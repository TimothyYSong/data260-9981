import logging
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

from mcp.server.fastmcp import FastMCP
from sqlalchemy import func, or_

from database import SessionLocal
from models import RestaurantInspection


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("s9981-domain")


def success_response(data):
    return {
        "ok": True,
        "data": data,
        "error": None,
    }


def error_response(message):
    return {
        "ok": False,
        "data": None,
        "error": message,
    }


class TransientStorageError(Exception):
    pass


def run_with_retry(
    operation,
    max_attempts=3,
    timeout_seconds=2.0,
    base_delay=0.1,
    max_delay=0.5,
    failure_injector=None,
):
    last_error = None

    for attempt in range(1, max_attempts + 1):
        try:
            if failure_injector is not None and failure_injector():
                raise TransientStorageError(
                    f"simulated transient failure on attempt {attempt}"
                )

            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(operation)
                result = future.result(timeout=timeout_seconds)

            return {
                "ok": True,
                "data": result,
                "error": None,
                "attempts": attempt,
            }

        except FutureTimeoutError:
            last_error = (
                f"operation timed out after {timeout_seconds} seconds"
            )

        except Exception as error:
            last_error = str(error)

        if attempt < max_attempts:
            delay = min(
                base_delay * (2 ** (attempt - 1)),
                max_delay,
            )

            logger.warning(
                "Attempt %s failed: %s. Retrying in %.2f seconds.",
                attempt,
                last_error,
                delay,
            )

            time.sleep(delay)

    return {
        "ok": False,
        "data": None,
        "error": last_error,
        "attempts": max_attempts,
    }


@mcp.tool()
def search_inspections(query: str, limit: int = 10):
    if not query.strip():
        return error_response("query must not be empty")

    if limit < 1 or limit > 25:
        return error_response("limit must be between 1 and 25")

    def operation():
        db = SessionLocal()

        try:
            inspections = (
                db.query(RestaurantInspection)
                .filter(
                    or_(
                        RestaurantInspection.restaurant_name.ilike(
                            f"%{query}%"
                        ),
                        RestaurantInspection.restaurant_address.ilike(
                            f"%{query}%"
                        ),
                        RestaurantInspection.inspection_code.ilike(
                            f"%{query}%"
                        ),
                    )
                )
                .limit(limit)
                .all()
            )

            return [
                {
                    "id": inspection.id,
                    "restaurant_name": inspection.restaurant_name,
                    "restaurant_address": inspection.restaurant_address,
                    "inspection_code": inspection.inspection_code,
                    "violation_count": inspection.violation_count,
                    "restaurant_id": inspection.restaurant_id,
                }
                for inspection in inspections
            ]

        finally:
            db.close()

    result = run_with_retry(operation)

    if result["ok"]:
        return success_response(result["data"])

    logger.error(
        "search_inspections failed after %s attempts: %s",
        result["attempts"],
        result["error"],
    )

    return error_response(
        f"failed to search inspections: {result['error']}"
    )


@mcp.tool()
def inspection_detail(inspection_id: int):
    if inspection_id < 1:
        return error_response(
            "inspection_id must be a positive integer"
        )

    def operation():
        db = SessionLocal()

        try:
            inspection = (
                db.query(RestaurantInspection)
                .filter(
                    RestaurantInspection.id == inspection_id
                )
                .first()
            )

            if inspection is None:
                raise ValueError(
                    f"inspection {inspection_id} was not found"
                )

            return {
                "id": inspection.id,
                "restaurant_name": inspection.restaurant_name,
                "restaurant_address": inspection.restaurant_address,
                "inspection_code": inspection.inspection_code,
                "violation_count": inspection.violation_count,
                "restaurant_id": inspection.restaurant_id,
                "created_at": (
                    inspection.created_at.isoformat()
                    if inspection.created_at
                    else None
                ),
                "updated_at": (
                    inspection.updated_at.isoformat()
                    if inspection.updated_at
                    else None
                ),
            }

        finally:
            db.close()

    result = run_with_retry(operation)

    if result["ok"]:
        return success_response(result["data"])

    logger.error(
        "inspection_detail failed after %s attempts: %s",
        result["attempts"],
        result["error"],
    )

    return error_response(
        f"failed to retrieve inspection details: {result['error']}"
    )


@mcp.tool()
def restaurant_inspection_summary(restaurant_id: int):
    if restaurant_id < 1:
        return error_response(
            "restaurant_id must be a positive integer"
        )

    def operation():
        db = SessionLocal()

        try:
            result = (
                db.query(
                    func.count(RestaurantInspection.id),
                    func.sum(
                        RestaurantInspection.violation_count
                    ),
                    func.avg(
                        RestaurantInspection.violation_count
                    ),
                    func.max(
                        RestaurantInspection.violation_count
                    ),
                )
                .filter(
                    RestaurantInspection.restaurant_id
                    == restaurant_id
                )
                .one()
            )

            inspection_count = result[0]

            if inspection_count == 0:
                raise ValueError(
                    f"no inspections found for restaurant "
                    f"{restaurant_id}"
                )

            return {
                "restaurant_id": restaurant_id,
                "inspection_count": inspection_count,
                "total_violations": int(result[1] or 0),
                "average_violations": float(result[2] or 0),
                "maximum_violations": int(result[3] or 0),
            }

        finally:
            db.close()

    result = run_with_retry(operation)

    if result["ok"]:
        return success_response(result["data"])

    logger.error(
        "restaurant_inspection_summary failed after %s attempts: %s",
        result["attempts"],
        result["error"],
    )

    return error_response(
        "failed to calculate restaurant inspection summary: "
        f"{result['error']}"
    )


if __name__ == "__main__":
    mcp.run()