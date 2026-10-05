import json

from database import SessionLocal
from domain_server import run_with_retry
from models import RestaurantInspection


def database_operation():
    db = SessionLocal()

    try:
        count = db.query(RestaurantInspection).count()

        return {
            "message": "database operation succeeded",
            "inspection_count": count,
        }

    finally:
        db.close()


def never_fail():
    return False


def fail_once():
    state = {"calls": 0}

    def injector():
        state["calls"] += 1
        return state["calls"] == 1

    return injector


def always_fail():
    return True


print("CASE 1: Success on first attempt")

case_1 = run_with_retry(
    database_operation,
    failure_injector=never_fail,
)

print(json.dumps(case_1, indent=2))


print("\nCASE 2: First attempt fails, retry succeeds")

case_2 = run_with_retry(
    database_operation,
    failure_injector=fail_once(),
)

print(json.dumps(case_2, indent=2))


print("\nCASE 3: All attempts fail")

case_3 = run_with_retry(
    database_operation,
    failure_injector=always_fail,
)

print(json.dumps(case_3, indent=2))