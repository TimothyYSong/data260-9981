import json
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
LESSONS_PATH = BASE / "lessons.json"


class LessonMemory:
    def __init__(self, path=LESSONS_PATH):
        self.path = Path(path)
        if not self.path.exists() or not self.path.stat().st_size:
            self.path.write_text("[]\n", encoding="utf-8")

        self.failure_history = {}

    def load(self):
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save(self, lessons):
        self.path.write_text(
            json.dumps(lessons, indent=2) + "\n",
            encoding="utf-8",
        )

    def record_failure(self, case_id, evaluation):
        if evaluation["result"] != "REVISE":
            return None

        fields = {
            item["field"]
            for item in evaluation["missing_or_incorrect"]
        }

        if "violation_count" not in fields:
            return None

        pattern = "Missing or incorrect violation count"
        self.failure_history.setdefault(pattern, set()).add(case_id)

        # Require two distinct failed examples.
        if len(self.failure_history[pattern]) < 2:
            return None

        lessons = self.load()

        for lesson in lessons:
            if lesson["failure_pattern"] == pattern:
                return lesson

        lesson = {
            "lesson_id": f"lesson_{len(lessons) + 1:03d}",
            "failure_pattern": pattern,
            "correction": (
                "When a question asks about violations, "
                "explicitly state the violation count from "
                "the inspection record. Never guess or omit it."
            ),
            "created_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "use_count": 0,
        }

        lessons.append(lesson)
        self.save(lessons)
        return lesson

    def get_relevant(self, question):
        lessons = self.load()
        relevant = []

        for lesson in lessons:
            if (
                lesson["failure_pattern"]
                == "Missing or incorrect violation count"
                and "violation" in question.lower()
            ):
                relevant.append(lesson)

        if relevant:
            ids = {item["lesson_id"] for item in relevant}
            for lesson in lessons:
                if lesson["lesson_id"] in ids:
                    lesson["use_count"] += 1
            self.save(lessons)

        return relevant


if __name__ == "__main__":
    from evaluator_agent import EvaluatorAgent
    from answering_agent import AnsweringAgent

    memory = LessonMemory()
    evaluator = EvaluatorAgent()

    # Reset only the lesson file for this development demo.
    memory.save([])

    failures = [
        ("train_01", 10016),
        ("train_02", 10017),
    ]

    print("\n=== LEARNING FROM REPEATED FAILURES ===")

    for case_id, inspection_id in failures:
        question = (
            f"What is the violation count for "
            f"inspection {inspection_id}?"
        )

        # Intentionally incorrect development answer.
        incorrect_answer = (
            f"Inspection {inspection_id} has "
            "999 violations."
        )

        evaluation = evaluator.evaluate(
            question,
            inspection_id,
            incorrect_answer,
        )

        lesson = memory.record_failure(
            case_id,
            evaluation,
        )

        print(f"\nCase: {case_id}")
        print("Evaluation:", evaluation["result"])
        print("Lesson available:", lesson is not None)

    assert len(memory.load()) == 1

    print("\n=== REUSING THE LESSON ===")

    later_question = (
        "What is the violation count for inspection 10018?"
    )

    # Reload from disk to demonstrate persistence.
    memory = LessonMemory()
    relevant = memory.get_relevant(later_question)

    assert len(relevant) == 1
    assert relevant[0]["use_count"] == 1

    agent = AnsweringAgent()
    response = agent.answer(
        question=later_question,
        inspection_id=10018,
        lessons=relevant,
    )

    evaluation = evaluator.evaluate(
        later_question,
        10018,
        response["answer"],
    )

    print("Loaded lesson:", relevant[0]["lesson_id"])
    print("Correction:", relevant[0]["correction"])
    print("Later question:", later_question)
    print("Answer:", response["answer"])
    print("Evaluation:", evaluation["result"])
    print("Use count:", memory.load()[0]["use_count"])

    assert evaluation["result"] == "PASS"

    print("\nLESSON MEMORY TEST PASSED")
