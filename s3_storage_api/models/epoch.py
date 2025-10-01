"""
Epoch and EpochAssignment models for managing 4-hour zipcode assignment cycles
"""
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import ENUM

from s3_storage_api.database import Base

# Enum for epoch status
EpochStatusEnum = ENUM(
    'pending', 'active', 'completed', 'archived',
    name='epoch_status_enum',
    create_type=False
)

class Epoch(Base):
    """
    Represents a 4-hour epoch with zipcode assignments
    """
    __tablename__ = "epochs"
    
    # Primary key: epoch ID in format "YYYY-MM-DD-HH:MM"
    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    
    # Timing
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # Security and configuration
    nonce: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    target_listings: Mapped[int] = mapped_column(Integer, nullable=False)
    tolerance_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    
    # Status tracking
    status: Mapped[str] = mapped_column(EpochStatusEnum, nullable=False, default='pending')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Selection algorithm metadata
    selection_seed: Mapped[Optional[int]] = mapped_column(Integer)
    algorithm_version: Mapped[str] = mapped_column(String(10), default='v1.0')
    
    # Relationships
    assignments: Mapped[List["EpochAssignment"]] = relationship(
        "EpochAssignment", 
        back_populates="epoch",
        cascade="all, delete-orphan"
    )
    
    # Indexes for performance
    __table_args__ = (
        Index('ix_epochs_start_time', 'start_time'),
        Index('ix_epochs_status', 'status'),
        Index('ix_epochs_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Epoch(id='{self.id}', status='{self.status}', target_listings={self.target_listings})>"
    
    @property
    def is_active(self) -> bool:
        """Check if epoch is currently active"""
        now = datetime.utcnow()
        return self.start_time <= now <= self.end_time
    
    @property
    def total_expected_listings(self) -> int:
        """Calculate total expected listings from all assignments"""
        return sum(assignment.expected_listings for assignment in self.assignments)


class EpochAssignment(Base):
    """
    Individual zipcode assignments within an epoch
    """
    __tablename__ = "epoch_assignments"
    
    # Composite primary key
    epoch_id: Mapped[str] = mapped_column(
        String(20), 
        ForeignKey("epochs.id", ondelete="CASCADE"),
        primary_key=True
    )
    zipcode: Mapped[str] = mapped_column(String(10), primary_key=True)
    
    # Zipcode details (denormalized for performance)
    expected_listings: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(2), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    county: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Market classification
    market_tier: Mapped[str] = mapped_column(
        ENUM('premium', 'standard', 'emerging', name='market_tier_enum', create_type=False),
        nullable=False
    )
    
    # Selection metadata
    selection_weight: Mapped[Optional[float]] = mapped_column()
    geographic_region: Mapped[Optional[str]] = mapped_column(String(50))
    
    # Relationships
    epoch: Mapped["Epoch"] = relationship("Epoch", back_populates="assignments")
    
    # Indexes for performance
    __table_args__ = (
        Index('ix_epoch_assignments_epoch_id', 'epoch_id'),
        Index('ix_epoch_assignments_zipcode', 'zipcode'),
        Index('ix_epoch_assignments_state', 'state'),
        Index('ix_epoch_assignments_market_tier', 'market_tier'),
    )
    
    def __repr__(self):
        return f"<EpochAssignment(epoch_id='{self.epoch_id}', zipcode='{self.zipcode}', expected_listings={self.expected_listings})>"
