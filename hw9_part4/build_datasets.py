import json
from pathlib import Path

BASE = Path(__file__).resolve().parent

reference = json.loads(
    (BASE / "reference_data.json").read_text(encoding="utf-8")
)
records = reference["inspections"]

assert len(records) >= 24, "At least 24 inspection records required."

def make_questions(selected, prefix):
    questions = []

    for i, record in enumerate(selected, 1):
        inspection_id = record["inspection_id"]

        if i % 4 == 1:
            question = (
                f"What is the violation count for inspection {inspection_id}?"
            )
        elif i % 4 == 2:
            question = (
                f"What is the restaurant name and address "
                f"for inspection {inspection_id}?"
            )
        elif i % 4 == 3:
            question = (
                f"What is the inspection code and violation count "
                f"for inspection {inspection_id}?"
            )
        else:
            question = (
                f"Provide the restaurant name, inspection code, "
                f"address, and violation count for inspection {inspection_id}."
            )

        questions.append({
            "id": f"{prefix}_{i:02d}",
            "inspection_id": inspection_id,
            "question": question
        })

    return questions

splits = {
    "training_data.json": make_questions(records[:8], "train"),
    "validation_data.json": make_questions(records[8:16], "val"),
    "test_data.json": make_questions(records[16:24], "test"),
}

for filename, questions in splits.items():
    path = BASE / filename
    path.write_text(
        json.dumps(questions, indent=2),
        encoding="utf-8"
    )
    print(f"{filename}: {len(questions)} questions")

(BASE / "lessons.json").write_text("[]\n", encoding="utf-8")

print("Initialized lessons.json")
print("Dataset generation completed.")
