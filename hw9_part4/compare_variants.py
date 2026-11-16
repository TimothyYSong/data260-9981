import hashlib
import json
import statistics
import time
from pathlib import Path

from answering_agent import AnsweringAgent
from evaluator_agent import EvaluatorAgent
from lesson_memory import LessonMemory

BASE = Path(__file__).resolve().parent
TEST_PATH = BASE / "test_data.json"
LESSONS_PATH = BASE / "lessons.json"
OUTPUT_PATH = BASE / "variant_results.json"

VARIANTS = [
    "Baseline",
    "Evaluator Repair",
    "Lesson Memory",
    "Validated Improvement",
]


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relevant_lessons(question, lessons):
    return [
        lesson.copy()
        for lesson in lessons
        if (
            lesson["failure_pattern"]
            == "Missing or incorrect violation count"
            and "violation" in question.lower()
        )
    ]


def run_case(item, variant, answering, evaluator, lessons):
    question = item["question"]
    inspection_id = item["inspection_id"]

    use_repair = variant != "Baseline"

    use_lessons = variant in (
        "Lesson Memory",
        "Validated Improvement",
    )

    supplied_lessons = (
        relevant_lessons(question, lessons)
        if use_lessons else []
    )

    history = []
    feedback = None
    max_attempts = 2 if use_repair else 1

    start = time.perf_counter()

    for attempt in range(1, max_attempts + 1):
        response = answering.answer(
            question=question,
            inspection_id=inspection_id,
            feedback=feedback,
            lessons=supplied_lessons,
        )

        answer = response["answer"]

        # Evaluator is part of repair-system execution.
        if use_repair:
            evaluation = evaluator.evaluate(
                question, inspection_id, answer
            )
        else:
            evaluation = None

        history.append({
            "attempt": attempt,
            "answer": answer,
            "evaluation": evaluation,
        })

        if not use_repair:
            break

        if evaluation["result"] == "PASS":
            break

        feedback = evaluation["feedback"]

    # Measure time until the variant produces its final response.
    # Baseline does not run an evaluator in its execution path.
    latency_ms = (time.perf_counter() - start) * 1000

    final_answer = history[-1]["answer"]

    # Offline grading for Baseline only.
    # This grading is excluded from Baseline's latency.
    if history[-1]["evaluation"] is None:
        final_evaluation = evaluator.evaluate(
            question, inspection_id, final_answer
        )
    else:
        final_evaluation = history[-1]["evaluation"]

    correct = final_evaluation["result"] == "PASS"

    return {
        "id": item["id"],
        "question": question,
        "inspection_id": inspection_id,
        "correct": correct,
        "final_evaluation": final_evaluation["result"],
        "final_answer": final_answer,
        "attempts": len(history),
        "latency_ms": round(latency_ms, 2),
        "lessons_loaded": [
            lesson["lesson_id"]
            for lesson in supplied_lessons
        ],
        "history": history,
        "final_grading": final_evaluation,
    }


def main():
    test_hash_before = sha256(TEST_PATH)
    lessons_hash_before = sha256(LESSONS_PATH)

    test_cases = read_json(TEST_PATH)
    lessons = LessonMemory().load()
    validation = read_json(
        BASE / "validation_results.json"
    )

    assert len(test_cases) == 8
    assert len({x["id"] for x in test_cases}) == 8

    assert lessons, "Missing saved lessons."

    assert (
        validation["summary"]["decision"] == "KEEP"
    ), "Validated Improvement requires an accepted lesson."

    answering = AnsweringAgent()
    evaluator = EvaluatorAgent()

    results = {}
    summary = []

    for variant in VARIANTS:
        print(f"\n{'=' * 60}")
        print(f"VARIANT: {variant}")
        print("=" * 60, flush=True)

        # Independent run: do not carry feedback or
        # histories from one variant into another.
        variant_results = []

        for item in test_cases:
            case = run_case(
                item,
                variant,
                answering,
                evaluator,
                lessons,
            )

            variant_results.append(case)

            print(
                f"{item['id']} | "
                f"{case['final_evaluation']} | "
                f"attempts={case['attempts']} | "
                f"latency={case['latency_ms']:.2f} ms | "
                f"lessons={case['lessons_loaded']}",
                flush=True,
            )

        correct = sum(
            case["correct"]
            for case in variant_results
        )

        incorrect = len(variant_results) - correct

        avg_attempts = statistics.mean(
            case["attempts"]
            for case in variant_results
        )

        avg_latency = statistics.mean(
            case["latency_ms"]
            for case in variant_results
        )

        row = {
            "variant": variant,
            "correct_answers": correct,
            "incorrect_answers": incorrect,
            "average_attempts": round(avg_attempts, 3),
            "average_latency_ms": round(avg_latency, 2),
        }

        summary.append(row)
        results[variant] = variant_results

        print("\nSUMMARY:", json.dumps(row, indent=2))

    # Make sure final evaluation never changed either input.
    assert sha256(TEST_PATH) == test_hash_before
    assert sha256(LESSONS_PATH) == lessons_hash_before

    output = {
        "model": "qwen3:8b",
        "test_dataset_sha256": test_hash_before,
        "test_cases": len(test_cases),
        "validation_decision": "KEEP",
        "summary": summary,
        "results": results,
        "latency_definition": (
            "Elapsed time until the variant returns its final "
            "answer. Baseline grading is excluded; evaluator "
            "and revision latency are included for other variants."
        ),
    }

    OUTPUT_PATH.write_text(
        json.dumps(output, indent=2) + "\n",
        encoding="utf-8",
    )

    print("\n" + "=" * 60)
    print("FINAL FOUR-VARIANT COMPARISON")
    print("=" * 60)

    print(
        f"{'Variant':<24}"
        f"{'Correct':>9}"
        f"{'Incorrect':>11}"
        f"{'Avg attempts':>15}"
        f"{'Avg latency':>16}"
    )

    for row in summary:
        print(
            f"{row['variant']:<24}"
            f"{row['correct_answers']:>9}"
            f"{row['incorrect_answers']:>11}"
            f"{row['average_attempts']:>15.3f}"
            f"{row['average_latency_ms']:>16.2f}"
        )

    print(f"\nSaved results: {OUTPUT_PATH}")
    print("Test dataset unchanged: YES")
    print("Lessons file unchanged: YES")


if __name__ == "__main__":
    main()
