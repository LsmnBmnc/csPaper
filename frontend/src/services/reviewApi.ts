import type { ReviewResponse, ApiError } from "../types/review";

export async function submitReview(file: File): Promise<ReviewResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch("/api/review", {
    method: "POST",
    body: formData
  });

  const data = await res.json();

  if (!res.ok) {
    throw data as ApiError;
  }

  return data as ReviewResponse;
}