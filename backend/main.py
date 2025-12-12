# 顶部导入区域（改为绝对导入）
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from backend.app.schemas import ReviewResponse
from backend.app.db import engine, SessionLocal, init_db
from backend.app.models import Base, SubmissionORM, ReviewResultORM, ScoreORM, ReviewORM
from backend.app.pdf_utils import extract_text_from_pdf
from backend.app.llm import call_deepseek_for_review, LLMError
from uuid import uuid4
from datetime import datetime, timezone

app = FastAPI(title="csPaper AI Review MVP")

# 创建表（如果尚不存在）
Base.metadata.create_all(bind=engine)

# Dev CORS: allow localhost frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev only; tighten in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB


def _make_id(prefix: str) -> str:
    return f"{prefix}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:4]}"

# 依赖：数据库会话（确保在 Depends 使用前定义）
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.on_event("startup")
def _startup():
    init_db()


@app.get("/ping")
def ping():
    return {"msg": "ok"}

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@app.post("/api/review", response_model=ReviewResponse)
async def create_review(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    接受一个 PDF 文件，解析文本，调用 DeepSeek 获取评分与审稿意见，
    写入数据库四张表（submissions/review_results/scores/reviews），并返回结构化结果。
    """
    # 1. 基础校验：存在性 + 类型 + 大小
    if file is None:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "MISSING_FILE",
                    "message": "必须提供一个名为 file 的 PDF 文件。",
                    "details": None,
                }
            },
        )

    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "INVALID_FILE_TYPE",
                    "message": "仅支持上传 PDF 文件。",
                    "details": {"content_type": file.content_type},
                }
            },
        )

    raw_bytes = await file.read()
    if len(raw_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail={
                "error": {
                    "code": "FILE_TOO_LARGE",
                    "message": "文件大小超过 20MB 限制。",
                    "details": {"size": len(raw_bytes)},
                }
            },
        )

    # 2. PDF 转文本
    try:
        full_text, preview = extract_text_from_pdf(raw_bytes)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "FORMAT_FAILED",
                    "message": "PDF 解析失败，请检查文件是否损坏。",
                    "details": {"reason": str(e)},
                }
            },
        )

    if not full_text.strip():
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "EMPTY_TEXT",
                    "message": "无法从 PDF 中提取有效文本。",
                    "details": None,
                }
            },
        )

    # 3. 调用 DeepSeek 模型得到 scores + reviews
    try:
        llm_result = call_deepseek_for_review(full_text)
    except LLMError as e:
        raise HTTPException(
            status_code=502,
            detail={
                "error": {
                    "code": "MODEL_ERROR",
                    "message": "审稿模型调用失败，请稍后重试。",
                    "details": {"reason": str(e)},
                }
            },
        )

    scores_data = llm_result.get("scores", [])
    reviews_data = llm_result.get("reviews", [])

    # 4. 写入数据库：submission + review_result + scores + reviews
    submission_id = f"sub_{uuid4().hex[:12]}"
    review_result_id = f"rev_{uuid4().hex[:12]}"

    db_submission = SubmissionORM(
        submission_id=submission_id,
        file_name=file.filename,
        file_size=len(raw_bytes),
        text_preview=preview,
    )
    db.add(db_submission)
    db.flush()  # 获取 db_submission.id

    db_review_result = ReviewResultORM(
        review_result_id=review_result_id,
        submission_id=submission_id,
        submission_db_id=db_submission.id,
    )
    db.add(db_review_result)
    db.flush()

    # scores
    for item in scores_data:
        dimension = str(item.get("dimension", "")).strip()
        value_raw = item.get("value", 0.0)
        try:
            value = float(value_raw)
        except Exception:
            value = 0.0

        if not dimension:
            continue

        db_score = ScoreORM(
            review_result_id=db_review_result.id,
            dimension=dimension,
            value=value,
        )
        db.add(db_score)

    # reviews
    for item in reviews_data:
        reviewer_id = str(item.get("reviewer_id", "")).strip() or "reviewer"
        text = str(item.get("text", "")).strip()
        if not text:
            continue

        db_review = ReviewORM(
            review_result_id=db_review_result.id,
            reviewer_id=reviewer_id,
            text=text,
        )
        db.add(db_review)

    db.commit()
    db.refresh(db_submission)
    db.refresh(db_review_result)

    # 5. 组装成 Pydantic 的 ReviewResponse 返回
    # 注意：此处局部导入也改为绝对导入
    from backend.app.schemas import Submission as SubmissionSchema
    from backend.app.schemas import ReviewResult as ReviewResultSchema
    from backend.app.schemas import Score as ScoreSchema
    from backend.app.schemas import Review as ReviewSchema
    from backend.app.schemas import ReviewResponse as ReviewResponseSchema

    submission_schema = SubmissionSchema(
        submission_id=db_submission.submission_id,
        file_name=db_submission.file_name,
        file_size=db_submission.file_size,
        created_at=db_submission.created_at.isoformat(),
        text_preview=db_submission.text_preview,
    )

    score_schemas = [
        ScoreSchema(dimension=s.dimension, value=s.value)
        for s in db_review_result.scores
    ]

    review_schemas = [
        ReviewSchema(reviewer_id=r.reviewer_id, text=r.text)
        for r in db_review_result.reviews
    ]

    review_result_schema = ReviewResultSchema(
        review_result_id=db_review_result.review_result_id,
        submission_id=db_review_result.submission_id,
        scores=score_schemas,
        reviews=review_schemas,
        generated_at=db_review_result.generated_at.isoformat(),
    )

    response = ReviewResponseSchema(
        submission=submission_schema,
        review_result=review_result_schema,
    )

    return response


@app.post("/api/review", response_model=ReviewResponse)
async def create_review(file: UploadFile = File(...)):
    """
    接受一个 PDF 文件，解析文本，调用 DeepSeek 获取评分与审稿意见，
    写入数据库四张表（submissions/review_results/scores/reviews），并返回结构化结果。
    """
    # 基本校验
    if file is None:
        return JSONResponse(
            status_code=400,
            content=ErrorEnvelope(
                error=ApiError(code="MISSING_FILE", message="必须提供一个名为 file 的 PDF 文件。", details=None)
            ).model_dump(),
        )

    if file.content_type != "application/pdf":
        return JSONResponse(
            status_code=400,
            content=ErrorEnvelope(
                error=ApiError(
                    code="INVALID_FILE_TYPE",
                    message="仅支持上传 PDF 文件。",
                    details={"content_type": file.content_type},
                )
            ).model_dump(),
        )

    # 读入文件
    data = await file.read()
    size = len(data)
    if size > MAX_FILE_SIZE:
        return JSONResponse(
            status_code=413,
            content=ErrorEnvelope(
                error=ApiError(
                    code="FILE_TOO_LARGE", message="文件超过 20MB 限制", details={"limit_mb": 20}
                )
            ).model_dump(),
        )

    # 解析 PDF -> 文本
    try:
        full_text, preview = extract_text_from_pdf(data)
    except Exception as e:
        return JSONResponse(
            status_code=422,
            content=ErrorEnvelope(
                error=ApiError(code="PDF_PARSE_FAILED", message="PDF 解析失败", details=str(e))
            ).model_dump(),
        )

    if not full_text.strip():
        return JSONResponse(
            status_code=422,
            content=ErrorEnvelope(
                error=ApiError(code="PDF_PARSE_EMPTY_TEXT", message="PDF 文本为空", details=None)
            ).model_dump(),
        )

    # 调用 DeepSeek -> JSON
    try:
        llm_out = call_deepseek_for_review(full_text)
    except LLMError as e:
        return JSONResponse(
            status_code=502,
            content=ErrorEnvelope(
                error=ApiError(code="LLM_CALL_FAILED", message="DeepSeek 调用失败", details=str(e))
            ).model_dump(),
        )

    # 生成业务 ID
    submission_id = _make_id("sub")
    review_result_id = _make_id("rev")

    # 入库
    session = SessionLocal()
    try:
        sub_db = SubmissionORM(
            submission_id=submission_id,
            file_name=file.filename or "paper.pdf",
            file_size=size,
            text_preview=preview,
        )
        session.add(sub_db)
        session.commit()
        session.refresh(sub_db)

        rr_db = ReviewResultORM(
            review_result_id=review_result_id,
            submission_id=submission_id,
            submission_db_id=sub_db.id,
        )
        session.add(rr_db)
        session.commit()
        session.refresh(rr_db)

        # scores
        for s in llm_out["scores"]:
            session.add(
                ScoreORM(
                    review_result_id=rr_db.id,
                    dimension=str(s["dimension"]),
                    value=float(s["value"]),
                )
            )

        # reviews
        for r in llm_out["reviews"]:
            session.add(
                ReviewORM(
                    review_result_id=rr_db.id,
                    reviewer_id=str(r["reviewer_id"]),
                    text=str(r["text"]),
                )
            )

        session.commit()
    except Exception as e:
        session.rollback()
        return JSONResponse(
            status_code=500,
            content=ErrorEnvelope(
                error=ApiError(code="DB_WRITE_FAILED", message="写入数据库失败", details=str(e))
            ).model_dump(),
        )
    finally:
        session.close()

    # 构造响应（与前端契约一致）
    submission = Submission(
        submission_id=sub_db.submission_id,
        file_name=sub_db.file_name,
        file_size=sub_db.file_size,
        created_at=sub_db.created_at.isoformat(),
        text_preview=sub_db.text_preview,
    )

    scores = [Score(dimension=str(s["dimension"]), value=float(s["value"])) for s in llm_out["scores"]]
    reviews = [Review(reviewer_id=str(r["reviewer_id"]), text=str(r["text"])) for r in llm_out["reviews"]]

    review_result = ReviewResult(
        review_result_id=rr_db.review_result_id,
        submission_id=sub_db.submission_id,
        scores=scores,
        reviews=reviews,
        generated_at=rr_db.generated_at.isoformat(),
    )

    return ReviewResponse(submission=submission, review_result=review_result)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
from backend.app.db import engine, SessionLocal, init_db
from backend.app.models import Base, SubmissionORM, ReviewResultORM, ScoreORM, ReviewORM
from backend.app.pdf_utils import extract_text_from_pdf
from backend.app.llm import call_deepseek_for_review, LLMError


