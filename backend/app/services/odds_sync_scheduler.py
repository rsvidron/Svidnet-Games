"""
Background Odds Sync Scheduler
Automatically syncs odds from The Odds API at 6 AM ET and 3 PM ET daily
"""
import threading
import time
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from app.core.config import settings

logger = logging.getLogger(__name__)


SETTLEMENT_INTERVAL_SECONDS = 30 * 60  # 30 minutes


class OddsSyncScheduler:
    """Background thread that syncs odds at scheduled times and settles bets every 30 minutes"""

    def __init__(self):
        self.sync_times = [(6, 0), (15, 0)]  # 6 AM and 3 PM
        self.timezone = ZoneInfo(settings.SYNC_TIMEZONE)
        self.running = False
        self.thread = None
        self.last_sync_day = None
        self.synced_hours = set()
        self.last_settlement_time = 0  # epoch seconds

    def start(self):
        """Start the background sync scheduler"""
        if not settings.AUTO_SYNC_ENABLED:
            logger.info("Auto-sync is disabled (AUTO_SYNC_ENABLED=false)")
            return

        if self.running:
            logger.warning("Sync scheduler already running")
            return

        self.running = True
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        logger.info("🕐 Odds sync scheduler started - syncing at 6 AM and 3 PM ET, settling bets every 30 min")

    def stop(self):
        """Stop the background sync scheduler"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Odds sync scheduler stopped")

    def _run_scheduler(self):
        """Main scheduler loop - runs in background thread"""
        logger.info("Sync scheduler thread started")

        while self.running:
            try:
                now = datetime.now(self.timezone)
                current_hour = now.hour
                current_minute = now.minute
                current_day = now.date()

                # Reset synced hours at midnight
                if current_day != self.last_sync_day:
                    self.synced_hours = set()
                    self.last_sync_day = current_day
                    logger.info(f"New day detected: {current_day}, resetting sync tracker")

                # Check if we should sync odds now (6 AM / 3 PM ET)
                for sync_hour, sync_minute in self.sync_times:
                    if current_hour == sync_hour and current_minute == sync_minute:
                        if sync_hour not in self.synced_hours:
                            logger.info(f"⏰ Sync time reached: {sync_hour}:00 ET")
                            self._trigger_sync()
                            self.synced_hours.add(sync_hour)
                        break

                # Settle bets every 30 minutes
                now_epoch = time.time()
                if now_epoch - self.last_settlement_time >= SETTLEMENT_INTERVAL_SECONDS:
                    self._trigger_settlement()
                    self.last_settlement_time = now_epoch

                # Sleep for 60 seconds before next check
                time.sleep(60)

            except Exception as e:
                logger.error(f"Error in sync scheduler loop: {str(e)}", exc_info=True)
                time.sleep(60)  # Continue even if error

        logger.info("Sync scheduler thread ended")

    def _trigger_sync(self):
        """Trigger the sync operation"""
        try:
            logger.info("🔄 Triggering automatic odds sync...")

            # Import here to avoid circular imports
            from database import SessionLocal
            from app.services.odds_service import odds_service
            from models.sports import SportsMatch, MatchStatus
            from models.sync_metadata import SyncMetadata
            from datetime import datetime, timezone, timedelta

            db = SessionLocal()

            try:
                # Get or create sync metadata
                sync_meta = db.query(SyncMetadata).first()
                if not sync_meta:
                    sync_meta = SyncMetadata()
                    db.add(sync_meta)
                    db.flush()

                # Mark sync as running
                sync_meta.sync_status = "running"
                db.commit()

                # Fetch all sports odds
                import asyncio
                all_games = asyncio.run(odds_service.get_all_todays_games())

                synced_count = 0
                updated_count = 0

                # Sync all sports
                for category, sports_dict in all_games.items():
                    for sport_key, events in sports_dict.items():
                        for event in events:
                            external_id = event.get("id")

                            existing = db.query(SportsMatch).filter(
                                SportsMatch.external_id == external_id
                            ).first()

                            if existing:
                                # Update odds data
                                existing.odds_data = event.get("bookmakers", [])
                                existing.updated_at = datetime.now(timezone.utc)
                                updated_count += 1
                            else:
                                # Create new match
                                match = SportsMatch(
                                    external_id=external_id,
                                    sport_key=sport_key,
                                    sport_title=event.get("sport_title", sport_key.upper()),
                                    home_team=event.get("home_team"),
                                    away_team=event.get("away_team"),
                                    commence_time=datetime.fromisoformat(
                                        event.get("commence_time").replace('Z', '+00:00')
                                    ),
                                    status=MatchStatus.UPCOMING,
                                    odds_data=event.get("bookmakers", [])
                                )
                                db.add(match)
                                synced_count += 1

                db.commit()

                # Clean up old matches (>7 days with no bets)
                cleanup_cutoff = datetime.now(timezone.utc) - timedelta(days=7)
                old_matches = db.query(SportsMatch).filter(
                    SportsMatch.created_at < cleanup_cutoff
                ).all()

                cleaned_count = 0
                for match in old_matches:
                    # Check if match has any bets
                    from models.sports import BetPick
                    has_bets = db.query(BetPick).filter(
                        BetPick.match_id == match.id
                    ).first() is not None

                    if not has_bets:
                        db.delete(match)
                        cleaned_count += 1

                db.commit()

                # Update sync metadata
                sync_meta.last_sync_time = datetime.now(timezone.utc)
                sync_meta.sync_status = "success"
                sync_meta.games_synced = synced_count + updated_count
                sync_meta.error_message = None
                db.commit()

                logger.info(
                    f"✅ Sync completed: {synced_count} new, {updated_count} updated, "
                    f"{cleaned_count} cleaned"
                )

            except Exception as sync_error:
                logger.error(f"❌ Sync failed: {str(sync_error)}", exc_info=True)

                # Mark sync as failed
                if sync_meta:
                    sync_meta.sync_status = "failed"
                    sync_meta.error_message = str(sync_error)[:500]
                    db.commit()

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error triggering sync: {str(e)}", exc_info=True)


    def _trigger_settlement(self):
        """Fetch scores from The Odds API and settle completed bets"""
        try:
            logger.info("💰 Triggering automatic bet settlement...")

            from database import SessionLocal
            from routers.sports import settle_completed_matches

            db = SessionLocal()
            try:
                result = settle_completed_matches(db)
                logger.info(
                    f"✅ Settlement complete: {result.get('matches_settled', 0)} matches, "
                    f"{result.get('bets_settled', 0)} bets settled"
                )
            finally:
                db.close()

        except Exception as e:
            logger.error(f"❌ Settlement failed: {str(e)}", exc_info=True)


# Global scheduler instance
sync_scheduler = OddsSyncScheduler()
