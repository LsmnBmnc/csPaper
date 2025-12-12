import type { ReviewResponse, ApiErrorShape } from "../types/review";

const DEFAULT_API_BASE = "http://localhost:8000"; // 后端 uvicorn 默认地址

export async function submitReview(file: File): Promise<ReviewResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const baseUrl = import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE;

  const res = await fetch(`${baseUrl}/api/review`, {
    method: "POST",
    body: formData,
  });

  const data = await res.json().catch(() => null);

  if (!res.ok) {
    // 尝试按约定的错误结构解析
    const apiError = (data ?? {}) as ApiErrorShape;
    const message =
      apiError?.error?.message ||
      `Request failed with status ${res.status}`;
    throw new Error(message);
  }

  return data as ReviewResponse;
}