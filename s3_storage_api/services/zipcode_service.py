"""
Zipcode selection service with weighted randomization and anti-gaming features
"""
import os
import random
import hashlib
import hmac
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from s3_storage_api.models.zipcode import Zipcode
from s3_storage_api.models.epoch import Epoch, EpochAssignment

logger = logging.getLogger(__name__)

class ZipcodeService:
    """
    Service for selecting zipcodes with weighted randomization and security features
    """
    
    def __init__(self):
        # Load configuration from environment
        self.target_listings = int(os.getenv("TARGET_LISTINGS", "10000"))
        self.tolerance_percent = int(os.getenv("TOLERANCE_PERCENT", "10"))
        self.min_zipcode_listings = int(os.getenv("MIN_ZIPCODE_LISTINGS", "200"))
        self.max_zipcode_listings = int(os.getenv("MAX_ZIPCODE_LISTINGS", "3000"))
        self.cooldown_hours = int(os.getenv("COOLDOWN_HOURS", "24"))
        
        # Algorithm parameters
        self.premium_weight = float(os.getenv("PREMIUM_WEIGHT", "1.5"))
        self.standard_weight = float(os.getenv("STANDARD_WEIGHT", "1.0"))
        self.emerging_weight = float(os.getenv("EMERGING_WEIGHT", "0.8"))
        self.selection_randomness = float(os.getenv("SELECTION_RANDOMNESS", "0.25"))
        self.geographic_spread_factor = float(os.getenv("GEOGRAPHIC_SPREAD_FACTOR", "0.15"))
        
        # Security parameters
        self.secret_key = os.getenv("ZIPCODE_SECRET_KEY", "default-secret-change-in-production")
        self.honeypot_probability = float(os.getenv("HONEYPOT_PROBABILITY", "0.3"))
        self.honeypot_threshold = int(os.getenv("HONEYPOT_THRESHOLD", "50"))
        
        # State priorities
        self.state_priorities = self._parse_state_priorities(
            os.getenv("STATE_PRIORITIES", "PA:1,NJ:2,NY:3,DE:4,MD:5")
        )
        
        # Market tier weights
        self.market_tier_weights = {
            "premium": self.premium_weight,
            "standard": self.standard_weight,
            "emerging": self.emerging_weight
        }
    
    def _parse_state_priorities(self, priority_string: str) -> Dict[str, int]:
        """Parse state priorities from environment variable"""
        priorities = {}
        for item in priority_string.split(","):
            if ":" in item:
                state, priority = item.strip().split(":")
                priorities[state.strip()] = int(priority.strip())
        return priorities
    
    def generate_epoch_seed(self, epoch_id: str) -> int:
        """Generate deterministic but unpredictable seed for zipcode selection"""
        seed_string = f"{epoch_id}:{self.secret_key}:{datetime.utcnow().strftime('%Y-%m-%d')}"
        return int(hashlib.sha256(seed_string.encode()).hexdigest()[:8], 16)
    
    def generate_epoch_nonce(self, epoch_id: str, selected_zipcodes: List[str]) -> str:
        """Generate epoch-specific nonce to prevent pre-scraping"""
        zipcode_hash = hashlib.sha256(''.join(sorted(selected_zipcodes)).encode()).hexdigest()
        nonce_input = f"{epoch_id}:{self.secret_key}:{zipcode_hash}"
        return hmac.new(
            self.secret_key.encode(),
            nonce_input.encode(),
            hashlib.sha256
        ).hexdigest()[:16]
    
    async def get_eligible_zipcodes(self, db: AsyncSession) -> List[Zipcode]:
        """
        Get zipcodes eligible for selection based on:
        - Active status
        - Expected listings within range
        - Not assigned within cooldown period
        - State priorities
        """
        cooldown_cutoff = datetime.utcnow() - timedelta(hours=self.cooldown_hours)
        
        query = select(Zipcode).where(
            and_(
                Zipcode.is_active == True,
                Zipcode.expected_listings >= self.min_zipcode_listings,
                Zipcode.expected_listings <= self.max_zipcode_listings,
                # Either never assigned or outside cooldown period
                (Zipcode.last_assigned.is_(None)) | (Zipcode.last_assigned < cooldown_cutoff),
                # Only include states in our priority list
                Zipcode.state.in_(list(self.state_priorities.keys()))
            )
        )
        
        result = await db.execute(query)
        eligible_zipcodes = result.scalars().all()
        
        logger.info(f"Found {len(eligible_zipcodes)} eligible zipcodes for selection")
        return list(eligible_zipcodes)
    
    def calculate_selection_weight(self, zipcode: Zipcode) -> float:
        """
        Calculate final selection weight for a zipcode incorporating all factors
        """
        # Base weight from expected listings
        base_weight = zipcode.expected_listings
        
        # Market tier weight
        tier_weight = self.market_tier_weights.get(zipcode.market_tier, 1.0)
        
        # State priority weight (lower priority number = higher weight)
        state_priority = self.state_priorities.get(zipcode.state, 10)
        state_weight = 1.0 / state_priority
        
        # Cooldown weight (recently assigned zipcodes get lower weight)
        cooldown_weight = zipcode.cooldown_weight
        
        # Base selection weight from zipcode record
        base_selection_weight = zipcode.base_selection_weight
        
        # Combine all weights
        final_weight = (
            base_weight * 
            tier_weight * 
            state_weight * 
            cooldown_weight * 
            base_selection_weight
        )
        
        return max(final_weight, 0.1)  # Minimum weight to avoid zero
    
    def add_honeypot_zipcodes(self, selected_zipcodes: List[Zipcode], all_eligible: List[Zipcode]) -> List[Zipcode]:
        """
        Add honeypot zipcodes for gaming detection
        """
        if random.random() < self.honeypot_probability:
            # Find low-activity zipcodes that weren't selected
            honeypot_candidates = [
                zc for zc in all_eligible 
                if zc not in selected_zipcodes and 
                zc.expected_listings < self.honeypot_threshold and
                not zc.is_honeypot  # Don't use existing honeypots
            ]
            
            if honeypot_candidates:
                honeypot = random.choice(honeypot_candidates)
                honeypot.is_honeypot = True  # Mark as honeypot for this epoch
                selected_zipcodes.append(honeypot)
                logger.info(f"Added honeypot zipcode {honeypot.zipcode} to selection")
        
        return selected_zipcodes
    
    def ensure_geographic_diversity(self, selected_zipcodes: List[Zipcode]) -> List[Zipcode]:
        """
        Ensure geographic diversity in selection by adjusting for state distribution
        """
        if len(selected_zipcodes) <= 3:
            return selected_zipcodes  # Too few to diversify
        
        # Count zipcodes per state
        state_counts = {}
        for zipcode in selected_zipcodes:
            state_counts[zipcode.state] = state_counts.get(zipcode.state, 0) + 1
        
        # If one state dominates (>70% of selection), try to balance
        total_selected = len(selected_zipcodes)
        max_state_count = max(state_counts.values())
        
        if max_state_count > (total_selected * 0.7):
            logger.info(f"Geographic diversity adjustment needed - one state has {max_state_count}/{total_selected} zipcodes")
            # This is a simple implementation - could be enhanced with more sophisticated balancing
        
        return selected_zipcodes
    
    async def select_zipcodes_for_epoch(
        self, 
        db: AsyncSession, 
        epoch_id: str,
        target_listings: Optional[int] = None
    ) -> Tuple[List[Zipcode], int]:
        """
        Select zipcodes for an epoch using weighted randomization
        
        Returns:
            Tuple of (selected_zipcodes, total_expected_listings)
        """
        if target_listings is None:
            target_listings = self.target_listings
        
        tolerance = target_listings * (self.tolerance_percent / 100)
        min_target = target_listings - tolerance
        max_target = target_listings + tolerance
        
        # Generate deterministic seed for this epoch
        seed = self.generate_epoch_seed(epoch_id)
        random.seed(seed)
        
        # Get eligible zipcodes
        eligible_zipcodes = await self.get_eligible_zipcodes(db)
        
        if not eligible_zipcodes:
            raise ValueError("No eligible zipcodes found for selection")
        
        # Calculate weights for all eligible zipcodes
        zipcode_weights = []
        for zipcode in eligible_zipcodes:
            weight = self.calculate_selection_weight(zipcode)
            zipcode_weights.append(weight)
        
        # Iteratively select zipcodes to hit target
        selected_zipcodes = []
        total_expected = 0
        attempts = 0
        max_attempts = 100
        
        while total_expected < min_target and attempts < max_attempts:
            attempts += 1
            
            # Select a zipcode using weighted random selection
            if eligible_zipcodes:
                selected_zipcode = random.choices(
                    eligible_zipcodes, 
                    weights=zipcode_weights, 
                    k=1
                )[0]
                
                # Add to selection
                selected_zipcodes.append(selected_zipcode)
                total_expected += selected_zipcode.expected_listings
                
                # Remove from eligible list to avoid duplicates
                index = eligible_zipcodes.index(selected_zipcode)
                eligible_zipcodes.pop(index)
                zipcode_weights.pop(index)
                
                # Stop if we've hit the max target or run out of zipcodes
                if total_expected >= max_target or not eligible_zipcodes:
                    break
        
        # Add honeypot zipcodes for gaming detection
        all_eligible = await self.get_eligible_zipcodes(db)  # Get fresh list including selected ones
        selected_zipcodes = self.add_honeypot_zipcodes(selected_zipcodes, all_eligible)
        
        # Ensure geographic diversity
        selected_zipcodes = self.ensure_geographic_diversity(selected_zipcodes)
        
        # Recalculate total expected listings
        total_expected = sum(zc.expected_listings for zc in selected_zipcodes)
        
        logger.info(
            f"Selected {len(selected_zipcodes)} zipcodes for epoch {epoch_id}: "
            f"{total_expected} expected listings (target: {target_listings}±{tolerance})"
        )
        
        return selected_zipcodes, total_expected
    
    async def create_epoch_assignments(
        self,
        db: AsyncSession,
        epoch: Epoch,
        selected_zipcodes: List[Zipcode]
    ) -> List[EpochAssignment]:
        """
        Create EpochAssignment records for selected zipcodes
        """
        assignments = []
        
        for zipcode in selected_zipcodes:
            assignment = EpochAssignment(
                epoch_id=epoch.id,
                zipcode=zipcode.zipcode,
                expected_listings=zipcode.expected_listings,
                state=zipcode.state,
                city=zipcode.city,
                county=zipcode.county,
                market_tier=zipcode.market_tier,
                selection_weight=self.calculate_selection_weight(zipcode),
                geographic_region=zipcode.geographic_region
            )
            assignments.append(assignment)
            
            # Update zipcode assignment history
            zipcode.update_assignment_history()
        
        # Bulk insert assignments
        db.add_all(assignments)
        await db.commit()
        
        logger.info(f"Created {len(assignments)} epoch assignments for epoch {epoch.id}")
        return assignments
    
    async def get_zipcode_statistics(self, db: AsyncSession) -> Dict:
        """
        Get statistics about zipcode availability and distribution
        """
        # Total zipcodes
        total_query = select(func.count(Zipcode.zipcode))
        total_result = await db.execute(total_query)
        total_zipcodes = total_result.scalar()
        
        # Active zipcodes
        active_query = select(func.count(Zipcode.zipcode)).where(Zipcode.is_active == True)
        active_result = await db.execute(active_query)
        active_zipcodes = active_result.scalar()
        
        # Eligible zipcodes (for current selection)
        eligible_zipcodes = await self.get_eligible_zipcodes(db)
        eligible_count = len(eligible_zipcodes)
        
        # Distribution by state
        state_query = select(
            Zipcode.state, 
            func.count(Zipcode.zipcode).label('count'),
            func.sum(Zipcode.expected_listings).label('total_listings')
        ).where(Zipcode.is_active == True).group_by(Zipcode.state)
        
        state_result = await db.execute(state_query)
        state_distribution = {
            row.state: {
                'zipcode_count': row.count,
                'total_expected_listings': row.total_listings or 0
            }
            for row in state_result
        }
        
        # Market tier distribution
        tier_query = select(
            Zipcode.market_tier,
            func.count(Zipcode.zipcode).label('count'),
            func.avg(Zipcode.expected_listings).label('avg_listings')
        ).where(Zipcode.is_active == True).group_by(Zipcode.market_tier)
        
        tier_result = await db.execute(tier_query)
        tier_distribution = {
            row.market_tier: {
                'zipcode_count': row.count,
                'avg_expected_listings': round(row.avg_listings or 0, 1)
            }
            for row in tier_result
        }
        
        return {
            'total_zipcodes': total_zipcodes,
            'active_zipcodes': active_zipcodes,
            'eligible_zipcodes': eligible_count,
            'state_distribution': state_distribution,
            'market_tier_distribution': tier_distribution,
            'configuration': {
                'target_listings': self.target_listings,
                'tolerance_percent': self.tolerance_percent,
                'cooldown_hours': self.cooldown_hours,
                'state_priorities': self.state_priorities,
                'market_tier_weights': self.market_tier_weights
            }
        }
