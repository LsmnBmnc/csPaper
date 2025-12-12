export interface Submission {
  submission_id: string;
  file_name: string;
  file_size: number;
  created_at: string;
  text_preview: string;
}

export interface Score {
  dimension: string; // e.g. "novelty" / "technical_quality" / ...
  value: number;     // 0–5
}

export interface Review {
  reviewer_id: string; // e.g. "reviewer_1"
  text: string;
}

export interface ReviewResult {
  review_result_id: string;
  submission_id: string;
  scores: Score[];
  reviews: Review[];
  generated_at: string;
}

export interface ReviewResponse {
  submission: Submission;
  review_result: ReviewResult;
}

export interface ApiError {
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
}