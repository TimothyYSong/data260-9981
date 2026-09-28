import random

from database import SessionLocal
from models import InspectionNote, RestaurantInspection

SEED = 9981
PRIMARY_ROW_COUNT = 5000
RELATED_ROW_COUNT = 200


def main():
    rng = random.Random(SEED)
    db = SessionLocal()

    try:
        # Clear related rows first because of the foreign key.
        db.query(InspectionNote).delete()
        db.query(RestaurantInspection).delete()
        db.commit()

        # Seed exactly 5,000 primary domain rows.
        inspections = []

        for i in range(1, PRIMARY_ROW_COUNT + 1):
            inspection = RestaurantInspection(
                restaurant_name=f"Restaurant {i}",
                restaurant_address=f"{100 + i} Test Street",
            )
            inspections.append(inspection)

        db.add_all(inspections)
        db.commit()

        # Fetch generated IDs.
        inspection_ids = [
            row.id
            for row in db.query(RestaurantInspection.id).all()
        ]

        # Pick 200 associated primary rows deterministically.
        selected_ids = rng.sample(
            inspection_ids,
            RELATED_ROW_COUNT,
        )

        notes = []

        for i, inspection_id in enumerate(selected_ids, start=1):
            note = InspectionNote(
                restaurant_inspection_id=inspection_id,
                note=f"Inspection note {i}",
            )
            notes.append(note)

        db.add_all(notes)
        db.commit()

        primary_count = db.query(RestaurantInspection).count()
        related_count = db.query(InspectionNote).count()

        print(f"SEED = {SEED}")
        print(f"restaurant_inspections rows = {primary_count}")
        print(f"inspection_notes rows = {related_count}")

    finally:
        db.close()


if __name__ == "__main__":
    main()