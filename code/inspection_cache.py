import logging
import os

import redis

from database import SessionLocal
from models import RestaurantInspection

logger = logging.getLogger(__name__)

# Student-specific prefix required for all Redis keys.
PREFIX = "s9981"


class InspectionCache:
    def __init__(self):
        # STEP 1: Connect to Redis.
        # Redis stores the view counter in memory for fast updates.
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            decode_responses=True,
        )

    def increment_inspection_views(self, inspection_id):
        # STEP 2: Create a unique Redis key for this inspection.
        # Example: s9981:views:inspection:10016
        key = f"{PREFIX}:views:inspection:{inspection_id}"

        # STEP 3: Verify the inspection exists in the SQL database.
        # Also retrieve the previously saved view count.
        with SessionLocal() as session:
            inspection = session.get(
                RestaurantInspection, inspection_id
            )

            # Prevent counting views for nonexistent inspections.
            if inspection is None:
                raise ValueError(
                    f"Inspection {inspection_id} not found"
                )

            persisted_count = inspection.view_count

        # STEP 4: Initialize the Redis counter if it doesn't exist.
        # SETNX only sets the value when the key is missing.
        # This prevents resetting an existing counter.
        self.redis_client.setnx(key, persisted_count)

        # STEP 5: Increment the Redis counter by 1.
        # INCR is atomic and returns the updated count.
        count = self.redis_client.incr(key)

        # STEP 6: Synchronize the counter with SQL every 10 views.
        # Example: counts 10, 20, 30, etc.
        if count % 10 == 0:

            # Update the inspection's view_count in the SQL database.
            with SessionLocal.begin() as session:
                inspection = session.get(
                    RestaurantInspection, inspection_id
                )
                inspection.view_count = count

            # Log a message confirming database synchronization.
            logger.info(
                "Synced views to database: "
                "inspection=%s, count=%s",
                inspection_id,
                count,
            )

        # STEP 7: Return the current count from Redis.
        # Example: Access #25 -> Total = 25
        return count