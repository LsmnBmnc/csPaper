import React from "react";

export function UploadPage() {
  return (
    <section className="upload-page">
      <div className="upload-hero">
        <h1 className="upload-title">
          AI Review: Upload once, get authentic feedback
        </h1>
        <p className="upload-subtitle">
          Upload a PDF paper and we’ll provide four scores and four review comments.
        </p>
      </div>

      <div className="upload-drop-wrapper">
        <div className="upload-drop-area">
          <div className="upload-icon" />
          <p className="upload-drop-text">
            Drag a PDF here, or click to select a file
          </p>
          <p className="upload-hint">
            Currently supports a single PDF file up to 20MB
          </p>
        </div>

        <button className="upload-button" type="button">
          Choose local file
        </button>
      </div>
    </section>
  );
}