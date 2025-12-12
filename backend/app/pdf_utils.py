from io import BytesIO
from typing import Tuple
from pypdf import PdfReader


def extract_text_from_pdf(file_bytes: bytes) -> Tuple[str, str]:
    """
    输入整份 PDF 的二进制，返回：
    - full_text: 整篇文本（按页拼接）
    - preview: 截取前一小段，用于存库调试
    """
    reader = PdfReader(BytesIO(file_bytes))
    texts = []
    for page in reader.pages:
        try:
            page_text = page.extract_text() or ""
        except Exception:
            page_text = ""
        texts.append(page_text)

    full_text = "\n\n".join(texts).strip()

    # 预览截断长度，你可以根据需要调
    preview_len = 800
    preview = full_text[:preview_len]

    return full_text, preview