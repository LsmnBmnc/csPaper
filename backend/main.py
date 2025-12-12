from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.schemas import (
    Submission,
    Review,
    Score,
    ReviewResult,
    ReviewResponse,
)
from backend.app.db import engine
from backend.app.models import Base
from backend.app.db import init_db  # ← 这里补上 init_db 的导入

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


@app.on_event("startup")
def _startup():
    init_db()


@app.get("/ping")
def ping():
    return {"msg": "ok"}

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@app.post("/api/review", response_model=ReviewResponse)
async def post_review(
    file: UploadFile | None = File(None),
    model_version: str | None = Form(None),
    locale: str | None = Form(None),
):
    # Validation: missing file
    if file is None:
        return JSONResponse(
            status_code=400,
            content=ErrorEnvelope(
                error=ApiError(code="MISSING_FILE", message="file field is required", details=None)
            ).model_dump(),
        )

    # Validation: MIME type
    if file.content_type != "application/pdf":
        return JSONResponse(
            status_code=400,
            content=ErrorEnvelope(
                error=ApiError(
                    code="INVALID_FILE_TYPE",
                    message="only application/pdf is accepted",
                    details={"mime": file.content_type},
                )
            ).model_dump(),
        )

    # Read file to check size (simple MVP approach)
    data = await file.read()
    size = len(data)
    if size > MAX_FILE_SIZE:
        return JSONResponse(
            status_code=413,
            content=ErrorEnvelope(
                error=ApiError(
                    code="FILE_TOO_LARGE", message="file size exceeds 20MB limit", details={"limit_mb": 20}
                )
            ).model_dump(),
        )

    # Build submission
    submission_id = _make_id("sub")
    created_at = datetime.utcnow().isoformat() + "Z"

    submission = Submission(
        submission_id=submission_id,
        file_name=file.filename or "paper.pdf",
        file_size=size,
        created_at=created_at,
        text_preview="This is the first 200 characters of the formatted text...",
    )

    # Build review_result (static stub values for MVP)
    review_result = ReviewResult(
        review_result_id=_make_id("rev"),
        submission_id=submission_id,
        scores=[
            Score(dimension="novelty", value=4.5),
            Score(dimension="technical_quality", value=4.0),
            Score(dimension="clarity", value=3.5),
            Score(dimension="significance", value=4.0),
        ],
        reviews=[
            Review(
                reviewer_id="reviewer_1",
                text="The paper presents an interesting approach, but the experimental section is limited..."
            ),
            Review(
                reviewer_id="reviewer_2",
                text="Clarity of writing is good, yet related work section can be more complete..."
            ),
            Review(
                reviewer_id="reviewer_3",
                text="Method is technically sound, but evaluation lacks comparison with strong baselines..."
            ),
            Review(
                reviewer_id="reviewer_4",
                text="Overall recommendation: borderline accept. Suggestions for improvement include..."
            ),
        ],
        generated_at=datetime.utcnow().isoformat() + "Z",
    )

    return ReviewResponse(submission=submission, review_result=review_result)


@app.post("/api/review", response_model=ReviewResponse)
async def create_review(file: UploadFile = File(...)):
    """
    MVP 空壳接口：
    接受一个 PDF 文件，暂不做真实解析/模型调用，
    直接返回结构正确的假数据，方便前端联调。
    """
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

    submission_id = f"sub_{uuid4().hex[:12]}"
    review_result_id = f"rev_{uuid4().hex[:12]}"
    text_preview = "This is a placeholder text preview. Real formatted text will be added in step 6."

    return ReviewResponse(
        submission={
            "submission_id": submission_id,
            "file_name": file.filename or "paper.pdf",
            "file_size": 0,  # 第六步再填真实大小
            "created_at": _now_iso(),
            "text_preview": text_preview,
        },
        review_result={
            "review_result_id": review_result_id,
            "submission_id": submission_id,
            "scores": [
                {"dimension": "novelty", "value": 0.0},
                {"dimension": "technical_quality", "value": 0.0},
                {"dimension": "clarity", "value": 0.0},
                {"dimension": "significance", "value": 0.0},
            ],
            "reviews": [
                {
                    "reviewer_id": "reviewer_1",
                    "text": "Placeholder review text. Real model output will be added in step 6.",
                },
                {
                    "reviewer_id": "reviewer_2",
                    "text": "Placeholder review text. Real model output will be added in step 6.",
                },
                {
                    "reviewer_id": "reviewer_3",
                    "text": "Placeholder review text. Real model output will be added in step 6.",
                },
                {
                    "reviewer_id": "reviewer_4",
                    "text": "Placeholder review text. Real model output will be added in step 6.",
                },
            ],
            "generated_at": _now_iso(),
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)