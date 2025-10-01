"""
Epoch management service for handling 4-hour zipcode assignment cycles
"""
import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from s3_storage_api.models.epoch import Epoch, EpochAssignment
from s3_storage_api.services.zipcode_service import ZipcodeService

logger = logging.getLogger(__name__)

class EpochManager:
    """
    Manages 4-hour epoch cycles and automatic zipcode assignment generation
    """
    
    def __init__(self, zipcode_service: ZipcodeService):
        self.zipcode_service = zipcode_service
        self.epoch_duration_hours = int(os.getenv("EPOCH_DURATION_HOURS", "4"))
        self.target_listings = int(os.getenv("TARGET_LISTINGS", "10000"))
        self.tolerance_percent = int(os.getenv("TOLERANCE_PERCENT", "10"))
        
        # Epoch start times (UTC): 00:00, 04:00, 08:00, 12:00, 16:00, 20:00
        self.epoch_start_hours = [0, 4, 8, 12, 16, 20]
        
        # Background task management
        self._background_task: Optional[asyncio.Task] = None
        self._running = False
    
    def generate_epoch_id(self, start_time: datetime) -> str:
        """Generate epoch ID in format YYYY-MM-DD-HH:MM"""
        return start_time.strftime("%Y-%m-%d-%H:%M")
    
    def get_next_epoch_start(self, from_time: Optional[datetime] = None) -> datetime:
        """
        Get the next epoch start time from the given time (or now)
        """
        if from_time is None:
            from_time = datetime.utcnow()
        
        # Find the next valid start hour
        current_hour = from_time.hour
        
        # Find next epoch start hour
        next_hour = None
        for start_hour in self.epoch_start_hours:
            if start_hour > current_hour:
                next_hour = start_hour
                break
        
        if next_hour is None:
            # Next epoch is tomorrow at 00:00
            next_start = from_time.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        else:
            # Next epoch is today at next_hour
            next_start = from_time.replace(hour=next_hour, minute=0, second=0, microsecond=0)
        
        return next_start
    
    def get_current_epoch_start(self, for_time: Optional[datetime] = None) -> datetime:
        """
        Get the current epoch start time for the given time (or now)
        """
        if for_time is None:
            for_time = datetime.utcnow()
        
        current_hour = for_time.hour
        
        # Find the most recent epoch start hour
        current_epoch_hour = None
        for start_hour in reversed(self.epoch_start_hours):
            if start_hour <= current_hour:
                current_epoch_hour = start_hour
                break
        
        if current_epoch_hour is None:
            # We're before the first epoch of the day, so current epoch is yesterday's last epoch
            yesterday = for_time - timedelta(days=1)
            current_epoch_hour = self.epoch_start_hours[-1]  # 20:00
            return yesterday.replace(hour=current_epoch_hour, minute=0, second=0, microsecond=0)
        else:
            return for_time.replace(hour=current_epoch_hour, minute=0, second=0, microsecond=0)
    
    async def get_current_epoch(self, db: AsyncSession) -> Optional[Epoch]:
        """
        Get the current active epoch
        """
        now = datetime.utcnow()
        current_start = self.get_current_epoch_start(now)
        current_end = current_start + timedelta(hours=self.epoch_duration_hours)
        
        # Check if we're within an epoch timeframe
        if current_start <= now <= current_end:
            epoch_id = self.generate_epoch_id(current_start)
            
            # Try to get existing epoch from database
            query = select(Epoch).where(Epoch.id == epoch_id)
            result = await db.execute(query)
            epoch = result.scalar_one_or_none()
            
            return epoch
        
        return None
    
    async def get_epoch_by_id(self, db: AsyncSession, epoch_id: str) -> Optional[Epoch]:
        """
        Get a specific epoch by ID
        """
        query = select(Epoch).where(Epoch.id == epoch_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_recent_epochs(self, db: AsyncSession, limit: int = 10) -> List[Epoch]:
        """
        Get recent epochs ordered by start time
        """
        query = select(Epoch).order_by(desc(Epoch.start_time)).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def create_epoch(
        self, 
        db: AsyncSession, 
        start_time: datetime,
        target_listings: Optional[int] = None
    ) -> Epoch:
        """
        Create a new epoch with zipcode assignments
        """
        if target_listings is None:
            target_listings = self.target_listings
        
        epoch_id = self.generate_epoch_id(start_time)
        end_time = start_time + timedelta(hours=self.epoch_duration_hours)
        
        # Check if epoch already exists
        existing_epoch = await self.get_epoch_by_id(db, epoch_id)
        if existing_epoch:
            logger.warning(f"Epoch {epoch_id} already exists")
            return existing_epoch
        
        # Generate zipcode selection
        selected_zipcodes, total_expected = await self.zipcode_service.select_zipcodes_for_epoch(
            db, epoch_id, target_listings
        )
        
        # Generate nonce for anti-gaming
        zipcode_list = [zc.zipcode for zc in selected_zipcodes]
        nonce = self.zipcode_service.generate_epoch_nonce(epoch_id, zipcode_list)
        
        # Create epoch record
        epoch = Epoch(
            id=epoch_id,
            start_time=start_time,
            end_time=end_time,
            nonce=nonce,
            target_listings=target_listings,
            tolerance_percent=self.tolerance_percent,
            status='pending',
            selection_seed=self.zipcode_service.generate_epoch_seed(epoch_id),
            algorithm_version='v1.0'
        )
        
        db.add(epoch)
        await db.flush()  # Get the epoch ID
        
        # Create epoch assignments
        await self.zipcode_service.create_epoch_assignments(db, epoch, selected_zipcodes)
        
        # Update epoch status
        now = datetime.utcnow()
        if start_time <= now <= end_time:
            epoch.status = 'active'
        
        await db.commit()
        
        logger.info(
            f"Created epoch {epoch_id}: {len(selected_zipcodes)} zipcodes, "
            f"{total_expected} expected listings"
        )
        
        return epoch
    
    async def activate_epoch(self, db: AsyncSession, epoch: Epoch) -> None:
        """
        Activate an epoch when its start time arrives
        """
        if epoch.status == 'pending':
            epoch.status = 'active'
            await db.commit()
            logger.info(f"Activated epoch {epoch.id}")
    
    async def complete_epoch(self, db: AsyncSession, epoch: Epoch) -> None:
        """
        Mark an epoch as completed when its end time passes
        """
        if epoch.status == 'active':
            epoch.status = 'completed'
            await db.commit()
            logger.info(f"Completed epoch {epoch.id}")
    
    async def ensure_current_epoch_exists(self, db: AsyncSession) -> Optional[Epoch]:
        """
        Ensure the current epoch exists, create if needed
        """
        current_epoch = await self.get_current_epoch(db)
        
        if current_epoch is None:
            # Create current epoch
            current_start = self.get_current_epoch_start()
            current_epoch = await self.create_epoch(db, current_start)
        
        return current_epoch
    
    async def prepare_next_epoch(self, db: AsyncSession) -> Optional[Epoch]:
        """
        Pre-generate the next epoch (called 5 minutes before start time)
        """
        next_start = self.get_next_epoch_start()
        next_epoch_id = self.generate_epoch_id(next_start)
        
        # Check if next epoch already exists
        existing_epoch = await self.get_epoch_by_id(db, next_epoch_id)
        if existing_epoch:
            return existing_epoch
        
        # Create next epoch
        next_epoch = await self.create_epoch(db, next_start)
        logger.info(f"Pre-generated next epoch {next_epoch_id}")
        
        return next_epoch
    
    async def cleanup_old_epochs(self, db: AsyncSession, retention_days: int = 7) -> int:
        """
        Archive old epochs beyond retention period
        """
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        query = select(Epoch).where(
            and_(
                Epoch.end_time < cutoff_date,
                Epoch.status != 'archived'
            )
        )
        
        result = await db.execute(query)
        old_epochs = result.scalars().all()
        
        archived_count = 0
        for epoch in old_epochs:
            epoch.status = 'archived'
            archived_count += 1
        
        if archived_count > 0:
            await db.commit()
            logger.info(f"Archived {archived_count} old epochs")
        
        return archived_count
    
    async def get_epoch_status_summary(self, db: AsyncSession) -> dict:
        """
        Get summary of epoch statuses for monitoring
        """
        now = datetime.utcnow()
        
        # Current epoch
        current_epoch = await self.get_current_epoch(db)
        
        # Next epoch start time
        next_start = self.get_next_epoch_start()
        time_to_next = (next_start - now).total_seconds()
        
        # Recent epochs
        recent_epochs = await self.get_recent_epochs(db, limit=5)
        
        return {
            'current_time': now.isoformat(),
            'current_epoch': {
                'id': current_epoch.id if current_epoch else None,
                'status': current_epoch.status if current_epoch else None,
                'start_time': current_epoch.start_time.isoformat() if current_epoch else None,
                'end_time': current_epoch.end_time.isoformat() if current_epoch else None,
                'assignments_count': len(current_epoch.assignments) if current_epoch else 0
            },
            'next_epoch': {
                'start_time': next_start.isoformat(),
                'seconds_until_start': int(time_to_next)
            },
            'recent_epochs': [
                {
                    'id': epoch.id,
                    'status': epoch.status,
                    'start_time': epoch.start_time.isoformat(),
                    'assignments_count': len(epoch.assignments)
                }
                for epoch in recent_epochs
            ]
        }
    
    async def start_background_management(self, db_session_factory):
        """
        Start background task for automatic epoch management
        """
        if self._running:
            logger.warning("Background epoch management already running")
            return
        
        self._running = True
        self._background_task = asyncio.create_task(
            self._background_epoch_loop(db_session_factory)
        )
        logger.info("Started background epoch management")
    
    async def stop_background_management(self):
        """
        Stop background epoch management
        """
        self._running = False
        if self._background_task:
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped background epoch management")
    
    async def _background_epoch_loop(self, db_session_factory):
        """
        Background loop for automatic epoch management
        """
        while self._running:
            try:
                async with db_session_factory() as db:
                    now = datetime.utcnow()
                    
                    # Ensure current epoch exists
                    current_epoch = await self.ensure_current_epoch_exists(db)
                    
                    # Activate pending epochs that should be active
                    if current_epoch and current_epoch.status == 'pending' and now >= current_epoch.start_time:
                        await self.activate_epoch(db, current_epoch)
                    
                    # Complete active epochs that have ended
                    if current_epoch and current_epoch.status == 'active' and now >= current_epoch.end_time:
                        await self.complete_epoch(db, current_epoch)
                    
                    # Pre-generate next epoch 5 minutes before start
                    next_start = self.get_next_epoch_start()
                    time_to_next = (next_start - now).total_seconds()
                    
                    if 0 < time_to_next <= 300:  # 5 minutes
                        await self.prepare_next_epoch(db)
                    
                    # Cleanup old epochs daily
                    if now.hour == 1 and now.minute < 5:  # Run at 1 AM
                        await self.cleanup_old_epochs(db)
                
            except Exception as e:
                logger.error(f"Error in background epoch management: {str(e)}")
            
            # Sleep for 1 minute before next check
            await asyncio.sleep(60)
