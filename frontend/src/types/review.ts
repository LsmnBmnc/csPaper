export interface Submission {
  submission_id: string;
  file_name: string;
  file_size: number;
  created_at: string;
  text_preview: string;
}

export interface Score {
  dimension: string;
  value: number; // 0–5 的浮点
}

export interface Review {
  reviewer_id: string;
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

export interface ApiErrorShape {
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
}