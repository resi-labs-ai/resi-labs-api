"""
Zipcode master data model for storing zipcode information and selection history
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, DateTime, Index, Float
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import ENUM

from s3_storage_api.database import Base

# Market tier enum
MarketTierEnum = ENUM(
    'premium', 'standard', 'emerging',
    name='market_tier_enum',
    create_type=False
)

class Zipcode(Base):
    """
    Master data for all zipcodes with market information and selection history
    """
    __tablename__ = "zipcodes"
    
    # Primary key
    zipcode: Mapped[str] = mapped_column(String(10), primary_key=True)
    
    # Geographic information
    state: Mapped[str] = mapped_column(String(2), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    county: Mapped[Optional[str]] = mapped_column(String(100))
    geographic_region: Mapped[Optional[str]] = mapped_column(String(50))
    
    # Market data
    population: Mapped[Optional[int]] = mapped_column(Integer)
    median_home_value: Mapped[Optional[int]] = mapped_column(Integer)
    expected_listings: Mapped[int] = mapped_column(Integer, nullable=False)
    market_tier: Mapped[str] = mapped_column(MarketTierEnum, nullable=False)
    
    # Selection history and weights
    last_assigned: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    assignment_count: Mapped[int] = mapped_column(Integer, default=0)
    base_selection_weight: Mapped[float] = mapped_column(Float, default=1.0)
    
    # Data quality tracking
    data_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    data_source: Mapped[Optional[str]] = mapped_column(String(50))  # e.g., "zillow", "census"
    data_quality_score: Mapped[Optional[float]] = mapped_column(Float)  # 0.0-1.0
    
    # Status flags
    is_active: Mapped[bool] = mapped_column(default=True)  # Can be assigned
    is_honeypot: Mapped[bool] = mapped_column(default=False)  # Used for gaming detection
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    
    # Indexes for performance
    __table_args__ = (
        Index('ix_zipcodes_state', 'state'),
        Index('ix_zipcodes_market_tier', 'market_tier'),
        Index('ix_zipcodes_expected_listings', 'expected_listings'),
        Index('ix_zipcodes_last_assigned', 'last_assigned'),
        Index('ix_zipcodes_is_active', 'is_active'),
        Index('ix_zipcodes_state_tier', 'state', 'market_tier'),  # Composite index
        Index('ix_zipcodes_selection_weight', 'base_selection_weight'),
    )
    
    def __repr__(self):
        return f"<Zipcode(zipcode='{self.zipcode}', state='{self.state}', city='{self.city}', expected_listings={self.expected_listings})>"
    
    @property
    def cooldown_weight(self) -> float:
        """
        Calculate cooldown weight based on last assignment time
        Returns lower weight for recently assigned zipcodes
        """
        if not self.last_assigned:
            return 1.0  # Never assigned = full weight
        
        hours_since_assignment = (datetime.utcnow() - self.last_assigned).total_seconds() / 3600
        cooldown_hours = 24  # From environment config
        
        if hours_since_assignment < cooldown_hours:
            # Linear decay from 0.1 to 1.0 over cooldown period
            return 0.1 + (0.9 * hours_since_assignment / cooldown_hours)
        else:
            return 1.0  # Full weight after cooldown
    
    @property
    def final_selection_weight(self) -> float:
        """
        Calculate final selection weight incorporating all factors
        """
        # Base factors
        listings_weight = self.expected_listings
        tier_weights = {'premium': 1.5, 'standard': 1.0, 'emerging': 0.8}
        tier_weight = tier_weights.get(self.market_tier, 1.0)
        
        # Combine all weights
        return (
            listings_weight * 
            tier_weight * 
            self.base_selection_weight * 
            self.cooldown_weight
        )
    
    def update_assignment_history(self):
        """
        Update assignment history when zipcode is selected
        """
        self.last_assigned = datetime.utcnow()
        self.assignment_count += 1
        self.updated_at = datetime.utcnow()
