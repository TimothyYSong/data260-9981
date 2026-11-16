import argparse
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path

from deepeval.metrics import GEval
from deepeval.models import OllamaModel
from deepeval.test_case import LLMTestCase, SingleTurnParams

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/hw10"
CASES = OUT / "eval_cases.json"

MODEL_NAME = "qwen3:8b"

RUBRIC = [
    "Evaluate the output against the exact user request.",
    "Judge relevance, accuracy, completeness, and usefulness.",
    "Do not reward fabricated facts or unsupported claims.",
    "A correct not-found answer may be fully helpful.",
    "Generic or unsupported responses should receive low scores.",
    "Apply the same standard across all evaluation cases.",
]

MODEL = OllamaModel(
    model=MODEL_NAME,
    base_url="http://127.0.0.1:11434",
    temperature=0,
    generation_kwargs={"num_predict": 2048},
)


def evaluate_metric(name, question, answer, steps):
    metric = GEval(
        name=name,
        evaluation_steps=steps,
        evaluation_params=[
            SingleTurnParams.INPUT,
            SingleTurnParams.ACTUAL_OUTPUT,
        ],
        model=MODEL,
        async_mode=False,
    )

    test_case = LLMTestCase(
        input=question,
        actual_output=answer,
    )

    started = time.monotonic()
    metric.measure(test_case)

    raw_score = float(metric.score)

    if not math.isfinite(raw_score) or not 0 <= raw_score <= 1:
        raise ValueError(f"Invalid GEval score: {raw_score}")

    # Linear mapping from normalized 0–1 GEval to 1–5.
    score_1_to_5 = 1 + 4 * raw_score

    return {
        "raw_geval_score": raw_score,
        "score_1_to_5": round(score_1_to_5, 3),
        "reason": metric.reason,
        "latency_ms": round(
            (time.monotonic() - started) * 1000, 2
        ),
    }


def evaluate_case(case):
    question = case["question"]
    plan = case["plan"]
    draft = case["draft"]
    final = case["final_answer"]

    result = {
        "case_id": case["case_id"],
        "trace_id": case["correlation_id"],
        "correlation_id": case["correlation_id"],
        "question": question,
        "plan": plan,
        "draft": draft,
        "final_answer": final,
        "reviewer_status": case["reviewer_status"],
        "judge_model": MODEL_NAME,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "metrics": {},
    }

    evaluations = [
        (
            "plan_quality",
            json.dumps(plan, ensure_ascii=False),
            [
                "Assess whether the plan addresses the question.",
                "Assess whether the steps are logical and actionable.",
                "Penalize irrelevant, missing, or redundant steps.",
                *RUBRIC,
            ],
        ),
        (
            "writer_helpfulness",
            draft,
            RUBRIC,
        ),
        (
            "final_helpfulness",
            final,
            RUBRIC,
        ),
    ]

    for name, output, steps in evaluations:
        print(f"Evaluating {name}...", flush=True)
        try:
            result["metrics"][name] = evaluate_metric(
                name, question, output, steps
            )
        except Exception as exc:
            result["metrics"][name] = {
                "error": f"{type(exc).__name__}: {exc}"
            }
            print(f"ERROR in {name}: {exc}", flush=True)

    writer = result["metrics"]["writer_helpfulness"]
    reviewed = result["metrics"]["final_helpfulness"]

    if "score_1_to_5" in writer and "score_1_to_5" in reviewed:
        difference = round(
            reviewed["score_1_to_5"]
            - writer["score_1_to_5"],
            3,
        )

        if draft == final:
            interpretation = (
                "Reviewer left the draft unchanged; no actual "
                "textual improvement occurred. Score differences "
                "may reflect judge variability."
            )
        elif difference > 0:
            interpretation = "Final answer scored higher than draft."
        elif difference < 0:
            interpretation = "Final answer scored lower than draft."
        else:
            interpretation = "No measured helpfulness improvement."

        result["metrics"]["final_vs_draft"] = {
            "writer_score": writer["score_1_to_5"],
            "final_score": reviewed["score_1_to_5"],
            "score_difference": difference,
            "text_changed": draft != final,
            "interpretation": interpretation,
        }
    else:
        result["metrics"]["final_vs_draft"] = {
            "error": "Missing Writer or final-answer score"
        }

    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", default="case_03")
    args = parser.parse_args()

    cases = json.loads(CASES.read_text())
    case = next(
        (c for c in cases if c["case_id"] == args.case),
        None,
    )

    if case is None:
        raise SystemExit(f"Unknown case: {args.case}")

    print(f"Case: {args.case}", flush=True)
    print(f"Trace ID: {case['correlation_id']}", flush=True)

    result = evaluate_case(case)

    output = OUT / f"evaluation_{args.case}.json"
    output.write_text(
        json.dumps(result, indent=2, ensure_ascii=False)
    )

    print("\n=== EVALUATION RESULTS ===")
    for name, metric in result["metrics"].items():
        print(name, json.dumps(metric, indent=2))

    print(f"\nSaved: {output}")


if __name__ == "__main__":
    main()
