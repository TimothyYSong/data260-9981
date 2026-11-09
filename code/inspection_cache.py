import logging
import os

import redis

from database import SessionLocal
from models import RestaurantInspection

logger = logging.getLogger(__name__)

PREFIX = "s9981"


class InspectionCache:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            decode_responses=True,
        )

    def increment_inspection_views(self, inspection_id):
        key = f"{PREFIX}:views:inspection:{inspection_id}"

        # Verify inspection exists.
        with SessionLocal() as session:
            inspection = session.get(
                RestaurantInspection, inspection_id
            )

            if inspection is None:
                raise ValueError(
                    f"Inspection {inspection_id} not found"
                )

            persisted_count = inspection.view_count

        # Initialize counter from database if missing.
        self.redis_client.setnx(key, persisted_count)

        # Increment Redis on each access.
        count = self.redis_client.incr(key)

        # Persist to SQL every 10 increments.
        if count % 10 == 0:
            with SessionLocal.begin() as session:
                inspection = session.get(
                    RestaurantInspection, inspection_id
                )
                inspection.view_count = count

            logger.info(
                "Synced views to database: "
                "inspection=%s, count=%s",
                inspection_id,
                count,
            )

        return count