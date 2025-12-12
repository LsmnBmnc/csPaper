from pydantic import BaseModel
from typing import List, Optional, Any


class Score(BaseModel):
    dimension: str
    value: float


class Review(BaseModel):
    reviewer_id: str
    text: str


class Submission(BaseModel):
    submission_id: str
    file_name: str
    file_size: int
    created_at: str
    text_preview: str


class ReviewResult(BaseModel):
    review_result_id: str
    submission_id: str
    scores: List[Score]
    reviews: List[Review]
    generated_at: str


class ReviewResponse(BaseModel):
    submission: Submission
    review_result: ReviewResult


class ApiError(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None


class ErrorEnvelope(BaseModel):
    error: ApiError