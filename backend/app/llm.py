import os
import json
from typing import Dict, Any
from openai import OpenAI
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import re

logger = logging.getLogger("cspaper.llm")
logger.setLevel(logging.INFO)
if not logger.handlers:
    log_path = Path(__file__).resolve().parent.parent / "instance" / "llm.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        log_path, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def sanitize_llm_json(content: str) -> str:
    """
    Normalize LLM output to a clean JSON string:
    - Strip whitespace
    - Remove Markdown code fences ```...``` (including ```json)
    - Remove common textual prefixes (e.g., 'JSON:', 'Response:', 'Output:')
    - Fallback: clip to first '{' and last '}' segment
    """
    s = content.strip()

    # Prefer fenced block content if present
    fence_re = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)
    m = fence_re.search(s)
    if m:
        logger.info("Sanitize: removed Markdown code fence from LLM content.")
        s = m.group(1).strip()

    # Remove common label prefixes
    s = re.sub(r"^\s*(json\s*:|response\s*:|output\s*:)\s*", "", s, flags=re.IGNORECASE)

    # Fallback: clip to braces
    if not s.lstrip().startswith("{") or not s.rstrip().endswith("}"):
        start = s.find("{")
        end = s.rfind("}")
        if start != -1 and end != -1 and end > start:
            logger.info("Sanitize: clipped to JSON braces segment.")
            s = s[start : end + 1]

    return s

class LLMError(Exception):
    pass


def build_review_prompt(paper_text: str) -> str:
    """
    Build an English prompt that instructs the model to return STRICT JSON
    with scores and reviews. The output must be ONLY valid JSON.
    """
    prompt = """
You are an experienced reviewer for top-tier computer science conferences.

Given the full paper text below, produce a structured review with STRICT JSON output.
Requirements:
1. Provide four scores (0.0 to 5.0, floating point) for dimensions:
   - novelty
   - technical_quality
   - clarity
   - significance
2. Provide four review comments, labeled reviewer_1 to reviewer_4, each focusing on different aspects.
3. Return ONLY valid JSON. No extra text, no comments, no Markdown.

Paper content (may be long):
"""
    prompt += "\n" + paper_text + "\n\n"
    prompt += """
Return JSON with EXACT keys:

{
  "scores": [
    { "dimension": "novelty", "value": 4.0 },
    { "dimension": "technical_quality", "value": 3.5 },
    { "dimension": "clarity", "value": 4.0 },
    { "dimension": "significance", "value": 3.5 }
  ],
  "reviews": [
    { "reviewer_id": "reviewer_1", "text": "..." },
    { "reviewer_id": "reviewer_2", "text": "..." },
    { "reviewer_id": "reviewer_3", "text": "..." },
    { "reviewer_id": "reviewer_4", "text": "..." }
  ]
}
"""
    return prompt


def call_deepseek_for_review(paper_text: str) -> Dict[str, Any]:
    """
    Call DeepSeek via the official OpenAI-compatible client.
    Expects the model to return a JSON string containing:
    {
      "scores": [...],
      "reviews": [...]
    }
    """
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        logger.error("DEEPSEEK_API_KEY not set")
        raise LLMError("DEEPSEEK_API_KEY not set")

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    messages = [
        {
            "role": "system",
            "content": "You are an expert CS conference reviewer. Respond ONLY with valid JSON."
        },
        {
            "role": "user",
            "content": build_review_prompt(paper_text)
        },
    ]

    # 调用前记录基本信息（模型与提示长度）
    logger.info(f"Calling DeepSeek model=deepseek-chat, prompt_chars={len(paper_text)}")

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=0.1,
            stream=False,
        )
    except Exception as e:
        logger.exception(f"DeepSeek API request failed: {type(e).__name__}: {e}")
        raise LLMError(f"DeepSeek API request failed: {e}")

    try:
        content = response.choices[0].message.content
    except Exception as e:
        logger.exception(f"Unexpected response format: {type(e).__name__}: {e}; raw_response={response}")
        raise LLMError(f"Unexpected DeepSeek response format: {e}; raw={response}")

    # 清洗内容后再解析 JSON
    sanitized = sanitize_llm_json(content)

    try:
        parsed = json.loads(sanitized)
    except json.JSONDecodeError as e:
        logger.exception(f"JSON parse failed after sanitize: {e}; content_head={sanitized[:500]}")
        raise LLMError(f"Failed to parse LLM JSON content: {e}; content={sanitized[:200]}")

    if "scores" not in parsed or "reviews" not in parsed:
        logger.error(f"LLM JSON missing keys: keys={list(parsed.keys())}")
        raise LLMError(f"LLM JSON missing keys: {parsed.keys()}")

    return parsed