import json
import re
import time
from pathlib import Path

from answering_agent import AnsweringAgent
from evaluator_agent import EvaluatorAgent
from lesson_memory import LessonMemory

BASE = Path(__file__).resolve().parent


def load_json(filename):
    return json.loads(
        (BASE / filename).read_text(encoding="utf-8")
    )


def evaluate_answer(evaluator, item, answer):
    result = evaluator.evaluate(
        question=item["question"],
        inspection_id=item["inspection_id"],
        answer=answer,
    )

    # Require agreement between deterministic checks
    # and the independent LLM evaluator.
    assessment = result.get("llm_assessment", "")
    match = re.search(
        r"^\s*(?:1[.)]\s*)?(PASS|REVISE)\b",
        assessment,
        flags=re.IGNORECASE,
    )

    llm_result = (
        match.group(1).upper() if match else "UNKNOWN"
    )

    passed = (
        result["result"] == "PASS"
        and llm_result == "PASS"
    )

    return {
        "passed": passed,
        "deterministic_result": result["result"],
        "llm_result": llm_result,
        "explanation": result["explanation"],
        "llm_assessment": assessment,
    }


def main():
    validation = load_json("validation_data.json")
    memory = LessonMemory()
    lessons = memory.load()

    assert len(validation) == 8
    assert lessons, "No saved lesson found."

    # Validation must not increment use_count or create lessons.
    original_lessons = json.dumps(lessons, sort_keys=True)

    answering = AnsweringAgent()
    evaluator = EvaluatorAgent()

    results = []

    print("\n=== VALIDATION: WITHOUT VS WITH LESSON ===")

    for item in validation:
        relevant = [
            lesson for lesson in lessons
            if "violation" in item["question"].lower()
            and lesson["failure_pattern"]
            == "Missing or incorrect violation count"
        ]

        row = {
            "id": item["id"],
            "question": item["question"],
            "inspection_id": item["inspection_id"],
            "lesson_relevant": bool(relevant),
        }

        for variant, supplied_lessons in [
            ("before", []),
            ("after", relevant),
        ]:
            start = time.perf_counter()

            response = answering.answer(
                question=item["question"],
                inspection_id=item["inspection_id"],
                lessons=supplied_lessons,
            )

            evaluation = evaluate_answer(
                evaluator,
                item,
                response["answer"],
            )

            row[variant] = {
                "answer": response["answer"],
                **evaluation,
                "latency_ms": round(
                    (time.perf_counter() - start) * 1000,
                    2,
                ),
            }

        results.append(row)

        before = row["before"]["passed"]
        after = row["after"]["passed"]

        print(f"\n{item['id']}: {item['question']}")
        print("Lesson relevant:", row["lesson_relevant"])
        print("Before:", "PASS" if before else "FAIL")
        print("After: ", "PASS" if after else "FAIL")
        print(
            "Regression:",
            "YES" if before and not after else "NO",
        )

    before_correct = sum(
        row["before"]["passed"] for row in results
    )
    after_correct = sum(
        row["after"]["passed"] for row in results
    )

    regressions = [
        row["id"] for row in results
        if row["before"]["passed"]
        and not row["after"]["passed"]
    ]

    relevant_regressions = [
        row["id"] for row in results
        if row["lesson_relevant"]
        and row["before"]["passed"]
        and not row["after"]["passed"]
    ]

    unrelated_failures = [
        row["id"] for row in results
        if not row["lesson_relevant"]
        and not row["after"]["passed"]
    ]

    keep_lesson = (
        after_correct >= before_correct
        and not regressions
        and not relevant_regressions
        and not unrelated_failures
    )

    summary = {
        "validation_cases": len(results),
        "before_correct": before_correct,
        "after_correct": after_correct,
        "before_incorrect": len(results) - before_correct,
        "after_incorrect": len(results) - after_correct,
        "regressions": regressions,
        "relevant_regressions": relevant_regressions,
        "unrelated_failures": unrelated_failures,
        "decision": (
            "KEEP" if keep_lesson else "REJECT_PENDING_REVIEW"
        ),
    }

    output = {
        "summary": summary,
        "results": results,
    }

    output_path = BASE / "validation_results.json"
    output_path.write_text(
        json.dumps(output, indent=2) + "\n",
        encoding="utf-8",
    )

    assert json.dumps(
        memory.load(), sort_keys=True
    ) == original_lessons, (
        "Validation unexpectedly changed lessons.json"
    )

    print("\n=== VALIDATION SUMMARY ===")
    print(json.dumps(summary, indent=2))
    print(f"\nSaved results to {output_path}")

    if keep_lesson:
        print("\nLESSON VALIDATION PASSED")
    else:
        print("\nLESSON VALIDATION NEEDS REVIEW")
        print("Do not use this lesson in final testing yet.")


if __name__ == "__main__":
    main()
