import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))

from database import SessionLocal  # noqa: E402
from models import RestaurantInspection  # noqa: E402

OUTPUT = Path(__file__).with_name("reference_data.json")

db = SessionLocal()

try:
    inspections = (
        db.query(RestaurantInspection)
        .order_by(RestaurantInspection.id)
        .limit(40)
        .all()
    )

    if not inspections:
        raise RuntimeError("No inspection records found.")

    records = [
        {
            "inspection_id": row.id,
            "inspection_code": row.inspection_code,
            "restaurant_id": row.restaurant_id,
            "restaurant_name": row.restaurant_name,
            "restaurant_address": row.restaurant_address,
            "violation_count": row.violation_count,
        }
        for row in inspections
    ]

    with OUTPUT.open("w", encoding="utf-8") as file:
        json.dump(
            {"domain": "Local Restaurant Inspection",
             "inspections": records},
            file,
            indent=2,
        )

    print(f"Exported {len(records)} inspections")
    print(f"Saved to: {OUTPUT}")
    print("First record:")
    print(json.dumps(records[0], indent=2))

finally:
    db.close()
