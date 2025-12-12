import type { ReviewResponse, ApiErrorShape } from "../types/review";

export async function submitReview(file: File): Promise<ReviewResponse> {
  const formData = new FormData();
  formData.append("file", file);

  // Prefer relative path to leverage Vite dev proxy.
  // If VITE_API_BASE_URL is set, use it; otherwise, fall back to proxy.
  const rawBase = import.meta.env.VITE_API_BASE_URL || "";
  const base = rawBase.replace(/\/$/, "");
  const url = base ? `${base}/api/review` : `/api/review`;

  let res: Response;
  try {
    res = await fetch(url, {
      method: "POST",
      body: formData,
    });
  } catch {
    throw new Error("Network request failed. Is backend running and CORS enabled?");
  }

  const data = await res.json().catch(() => null);

  if (!res.ok) {
    const apiError = (data ?? {}) as ApiErrorShape;
    const message =
      apiError?.error?.message ||
      res.statusText ||
      `Request failed with status ${res.status}`;
    throw new Error(message);
  }

  return data as ReviewResponse;
}