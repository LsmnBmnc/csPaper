import React, { useCallback, useRef, useState } from "react";
import { submitReview } from "../services/reviewApi";
import type { ReviewResponse } from "../types/review";

export function UploadPage() {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ReviewResponse | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const handleFileSelected = useCallback(
    async (file: File | null) => {
      if (!file) {
        return;
      }

      // 每次新上传清空旧状态
      setError(null);
      setResult(null);

      if (file.type !== "application/pdf") {
        setError("Only PDF files are supported. Please select a PDF.");
        return;
      }

      const maxSize = 20 * 1024 * 1024;
      if (file.size > maxSize) {
        setError("File exceeds the 20MB limit. Please compress and retry.");
        return;
      }

      setIsUploading(true);
      try {
        const res = await submitReview(file);
        setResult(res);
      } catch (e) {
        const msg =
          e instanceof Error ? e.message : "Upload or review failed. Please try again later.";
        setError(msg);
      } finally {
        setIsUploading(false);
      }
    },
    []
  );

  const onDrop = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      event.stopPropagation();
      setIsDragging(false);

      const files = event.dataTransfer.files;
      if (!files || files.length === 0) {
        return;
      }
      const file = files[0];
      void handleFileSelected(file);
    },
    [handleFileSelected]
  );

  const onDragOver = useCallback((event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    if (!isDragging) {
      setIsDragging(true);
    }
  }, [isDragging]);

  const onDragLeave = useCallback((event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    if (isDragging) {
      setIsDragging(false);
    }
  }, [isDragging]);

  const onClickSelect = useCallback(() => {
    if (isUploading) {
      return;
    }
    fileInputRef.current?.click();
  }, [isUploading]);

  const onFileInputChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const files = event.target.files;
      if (!files || files.length === 0) {
        return;
      }
      const file = files[0];
      void handleFileSelected(file);
      // 清空 input，避免选择同一个文件时 onChange 不触发
      event.target.value = "";
    },
    [handleFileSelected]
  );

  const dropAreaClass = [
    "upload-drop-area",
    isDragging ? "upload-drop-area--dragging" : "",
    isUploading ? "upload-drop-area--disabled" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <section className="upload-page">
      <div className="upload-hero">
        <h1 className="upload-title">
          AI Review: Upload once and get structured feedback fast
        </h1>
        <p className="upload-subtitle">
          Upload a PDF paper to get four scores and four review comments.
        </p>
      </div>

      <div className="upload-drop-wrapper">
        <div
          className={dropAreaClass}
          onDrop={onDrop}
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onClick={onClickSelect}
        >
          <div className="upload-icon" />
          <p className="upload-drop-text">
            {isUploading
              ? "Uploading and generating review…"
              : isDragging
              ? "Release to upload PDF"
              : "Drag a PDF here, or click to select file"}
          </p>
          <p className="upload-hint">
            Only a single PDF up to 20MB is supported
          </p>
        </div>

        <button
          className="upload-button"
          type="button"
          onClick={onClickSelect}
          disabled={isUploading}
        >
          {isUploading ? "Processing…" : "Choose local file"}
        </button>

        <input
          ref={fileInputRef}
          type="file"
          accept="application/pdf"
          style={{ display: "none" }}
          onChange={onFileInputChange}
        />

        {error && (
          <p className="upload-error">
            {error}
          </p>
        )}
      </div>

      {result && (
        <div className="review-result">
          <h2 className="review-result-title">Review Result</h2>

          <div className="review-scores">
            {result.review_result.scores.map((s) => (
              <div key={s.dimension} className="review-score-item">
                <span className="review-score-dim">
                  {s.dimension}
                </span>
                <span className="review-score-val">
                  {s.value.toFixed(1)} / 5.0
                </span>
              </div>
            ))}
          </div>

          <div className="review-reviews">
            {result.review_result.reviews.map((r) => (
              <div key={r.reviewer_id} className="review-review-item">
                <div className="review-review-header">
                  {r.reviewer_id}
                </div>
                <p className="review-review-text">
                  {r.text}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}