from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from .db import Base


def now_utc():
  return datetime.now(timezone.utc)


class SubmissionORM(Base):
  __tablename__ = "submissions"

  id = Column(Integer, primary_key=True, index=True)
  submission_id = Column(String(64), unique=True, index=True, nullable=False)
  file_name = Column(String(512), nullable=False)
  file_size = Column(Integer, nullable=False)
  created_at = Column(DateTime(timezone=True), default=now_utc, nullable=False)
  text_preview = Column(Text, nullable=False)

  review_results = relationship("ReviewResultORM", back_populates="submission")


class ReviewResultORM(Base):
  __tablename__ = "review_results"

  id = Column(Integer, primary_key=True, index=True)
  review_result_id = Column(String(64), unique=True, index=True, nullable=False)

  # 业务上的 submission 标识，方便对齐接口
  submission_id = Column(String(64), nullable=False)

  # 数据库级外键，方便 join
  submission_db_id = Column(Integer, ForeignKey("submissions.id"), nullable=False)

  generated_at = Column(DateTime(timezone=True), default=now_utc, nullable=False)

  submission = relationship("SubmissionORM", back_populates="review_results")
  scores = relationship("ScoreORM", back_populates="review_result", cascade="all, delete-orphan")
  reviews = relationship("ReviewORM", back_populates="review_result", cascade="all, delete-orphan")


class ScoreORM(Base):
  __tablename__ = "scores"

  id = Column(Integer, primary_key=True, index=True)
  review_result_id = Column(Integer, ForeignKey("review_results.id"), nullable=False)
  dimension = Column(String(64), nullable=False)
  value = Column(Float, nullable=False)

  review_result = relationship("ReviewResultORM", back_populates="scores")


class ReviewORM(Base):
  __tablename__ = "reviews"

  id = Column(Integer, primary_key=True, index=True)
  review_result_id = Column(Integer, ForeignKey("review_results.id"), nullable=False)
  reviewer_id = Column(String(64), nullable=False)
  text = Column(Text, nullable=False)

  review_result = relationship("ReviewResultORM", back_populates="reviews")