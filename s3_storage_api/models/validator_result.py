"""
Validator result models for tracking validation outcomes and audit trails
"""
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey, Index, Boolean, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import ENUM, JSON

from s3_storage_api.database import Base

# Validation status enum
ValidationStatusEnum = ENUM(
    'in_progress', 'completed', 'failed',
    name='validation_status_enum',
    create_type=False
)

# Validation result enum
ValidationResultEnum = ENUM(
    'pass', 'fail', 'partial',
    name='validation_result_enum', 
    create_type=False
)

# Validation type enum
ValidationTypeEnum = ENUM(
    'basic', 'spot_check', 'full',
    name='validation_type_enum',
    create_type=False
)

class ValidatorResult(Base):
    """
    Results of validator evaluation for each epoch
    """
    __tablename__ = "validator_results"
    
    # Composite primary key
    epoch_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("epochs.id", ondelete="CASCADE"),
        primary_key=True
    )
    validator_hotkey: Mapped[str] = mapped_column(String(100), primary_key=True)
    
    # Validation timing
    validation_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    validation_duration_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Validation scope
    miners_evaluated: Mapped[int] = mapped_column(Integer, nullable=False)
    total_validated_listings: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Top 3 miners (JSON format for flexibility)
    top_3_miners: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    # Example: [{"hotkey": "5F...", "rank": 1, "score": 0.95, "listings": 9850}, ...]
    
    # S3 upload tracking
    s3_upload_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    s3_upload_path: Mapped[Optional[str]] = mapped_column(String(500))
    s3_upload_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Status and metadata
    validation_status: Mapped[str] = mapped_column(ValidationStatusEnum, nullable=False, default='in_progress')
    validation_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    # Example: {"spot_check_percentage": 5, "honeypots_used": 2, "algorithm_version": "v1.0"}
    
    # Error tracking
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    
    # Indexes for performance
    __table_args__ = (
        Index('ix_validator_results_epoch_id', 'epoch_id'),
        Index('ix_validator_results_validator_hotkey', 'validator_hotkey'),
        Index('ix_validator_results_validation_timestamp', 'validation_timestamp'),
        Index('ix_validator_results_validation_status', 'validation_status'),
        Index('ix_validator_results_s3_upload_complete', 's3_upload_complete'),
    )
    
    def __repr__(self):
        return f"<ValidatorResult(epoch_id='{self.epoch_id}', validator_hotkey='{self.validator_hotkey[:10]}...', status='{self.validation_status}')>"


class ValidationAudit(Base):
    """
    Detailed audit trail for individual validation checks
    """
    __tablename__ = "validation_audit"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign keys
    epoch_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("epochs.id", ondelete="CASCADE"),
        nullable=False
    )
    validator_hotkey: Mapped[str] = mapped_column(String(100), nullable=False)
    miner_hotkey: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Validation details
    zipcode: Mapped[Optional[str]] = mapped_column(String(10))  # Specific zipcode being validated
    validation_type: Mapped[str] = mapped_column(ValidationTypeEnum, nullable=False)
    validation_result: Mapped[str] = mapped_column(ValidationResultEnum, nullable=False)
    
    # Scoring
    score: Mapped[Optional[float]] = mapped_column(Float)  # 0.0-1.0
    listings_checked: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Issues found (JSON array)
    issues_found: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    # Example: [{"type": "fake_listing", "property_id": "123", "reason": "Non-existent address"}, ...]
    
    # Validation metadata
    validation_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    # Example: {"sample_size": 50, "honeypot_triggered": false, "scraping_duration_ms": 1250}
    
    # Timing
    validation_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Indexes for performance and analysis
    __table_args__ = (
        Index('ix_validation_audit_epoch_validator', 'epoch_id', 'validator_hotkey'),
        Index('ix_validation_audit_epoch_miner', 'epoch_id', 'miner_hotkey'),
        Index('ix_validation_audit_validation_result', 'validation_result'),
        Index('ix_validation_audit_validation_type', 'validation_type'),
        Index('ix_validation_audit_timestamp', 'validation_timestamp'),
        Index('ix_validation_audit_zipcode', 'zipcode'),
    )
    
    def __repr__(self):
        return f"<ValidationAudit(id={self.id}, epoch_id='{self.epoch_id}', miner='{self.miner_hotkey[:10]}...', result='{self.validation_result}')>"


class MinerSubmission(Base):
    """
    Track miner submission status and metadata (optional table for monitoring)
    """
    __tablename__ = "miner_submissions"
    
    # Composite primary key
    epoch_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("epochs.id", ondelete="CASCADE"),
        primary_key=True
    )
    miner_hotkey: Mapped[str] = mapped_column(String(100), primary_key=True)
    
    # Submission timing
    submission_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Submission details
    listings_scraped: Mapped[Optional[int]] = mapped_column(Integer)
    zipcodes_completed: Mapped[Optional[int]] = mapped_column(Integer)
    
    # S3 upload status
    s3_upload_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    s3_upload_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Status tracking
    status: Mapped[str] = mapped_column(
        ENUM('in_progress', 'completed', 'failed', name='submission_status_enum', create_type=False),
        default='in_progress'
    )
    
    # Performance metrics
    scraping_duration_minutes: Mapped[Optional[int]] = mapped_column(Integer)
    data_quality_score: Mapped[Optional[float]] = mapped_column(Float)
    
    # Error tracking
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    
    # Indexes
    __table_args__ = (
        Index('ix_miner_submissions_epoch_id', 'epoch_id'),
        Index('ix_miner_submissions_miner_hotkey', 'miner_hotkey'),
        Index('ix_miner_submissions_submission_timestamp', 'submission_timestamp'),
        Index('ix_miner_submissions_status', 'status'),
    )
    
    def __repr__(self):
        return f"<MinerSubmission(epoch_id='{self.epoch_id}', miner_hotkey='{self.miner_hotkey[:10]}...', status='{self.status}')>"
