import argparse
import csv
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/hw10"
RUNS = OUT / "judge_runs"
RUNS.mkdir(parents=True, exist_ok=True)

CASES = json.loads((OUT / "eval_cases.json").read_text())

STEPS = [
    "Evaluate whether the response answers the exact user question.",
    "Judge relevance, accuracy, completeness, and usefulness.",
    "Treat correct not-found responses as potentially helpful.",
    "Penalize generic answers that omit requested information.",
    "Penalize unsupported-task responses that do not answer.",
    "Use the same helpfulness standard for every evaluation.",
]


def worker(case_id, repeat):
    from hw10_evaluator import evaluate_metric

    case = next(c for c in CASES if c["case_id"] == case_id)

    result = evaluate_metric(
        "Writer Helpfulness",
        case["question"],
        case["draft"],
        STEPS,
    )

    result.update({
        "case_id": case_id,
        "repeat": repeat,
        "trace_id": case["correlation_id"],
        "model": "qwen3:8b",
        "temperature": 0,
        "num_predict": 2048,
    })

    path = RUNS / f"{case_id}_run_{repeat}.json"
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(result, indent=2))
    temp.replace(path)

    print(f"SAVED {path.name}", flush=True)


def run_batch():
    total = 60
    completed = 0
    failures = []

    for case in CASES:
        for repeat in range(1, 4):
            case_id = case["case_id"]
            path = RUNS / f"{case_id}_run_{repeat}.json"

            if path.exists():
                try:
                    data = json.loads(path.read_text())
                    assert 1 <= data["score_1_to_5"] <= 5
                    completed += 1
                    continue
                except Exception:
                    path.unlink()

            print(
                f"[{completed}/{total}] "
                f"{case_id}, repeat {repeat}",
                flush=True,
            )

            started = time.monotonic()

            try:
                subprocess.run(
                    [
                        sys.executable,
                        str(Path(__file__).resolve()),
                        "--worker",
                        "--case",
                        case_id,
                        "--repeat",
                        str(repeat),
                    ],
                    timeout=90,
                    check=True,
                )
                completed += 1

            except subprocess.TimeoutExpired:
                failures.append((case_id, repeat, "timeout"))
                print("TIMEOUT: 90 seconds", flush=True)

            except subprocess.CalledProcessError as exc:
                failures.append(
                    (case_id, repeat, f"exit code {exc.returncode}")
                )
                print("FAILED:", exc, flush=True)

            print(
                "Elapsed:",
                round(time.monotonic() - started, 2),
                "seconds",
                flush=True,
            )

    print(f"\nCompleted: {completed}/{total}")
    print("Failures:", failures)

    if failures:
        print("Rerun this script to retry missing evaluations.")

    if completed == total:
        analyze()


def analyze():
    with (OUT / "human_labels.csv").open(newline="") as file:
        labels = {
            row["case_id"]: int(row["human_score"])
            for row in csv.DictReader(file)
        }

    rows = []
    for case in CASES:
        case_id = case["case_id"]
        scores = []

        for repeat in range(1, 4):
            path = RUNS / f"{case_id}_run_{repeat}.json"
            data = json.loads(path.read_text())
            scores.append(float(data["score_1_to_5"]))

        rows.append({
            "case_id": case_id,
            "trace_id": case["correlation_id"],
            "human_score": labels[case_id],
            "judge_run_1": scores[0],
            "judge_run_2": scores[1],
            "judge_run_3": scores[2],
            "judge_mean": float(np.mean(scores)),
            "judge_range": max(scores) - min(scores),
            "score_changed": max(scores) != min(scores),
        })

    human = [row["human_score"] for row in rows]
    judged = [row["judge_mean"] for row in rows]

    correlation, p_value = spearmanr(human, judged)
    mad = float(np.mean(
        [abs(a - b) for a, b in zip(human, judged)]
    ))

    pairwise_changes = []
    for row in rows:
        scores = [
            row["judge_run_1"],
            row["judge_run_2"],
            row["judge_run_3"],
        ]
        pairwise_changes.extend([
            abs(scores[0] - scores[1]),
            abs(scores[0] - scores[2]),
            abs(scores[1] - scores[2]),
        ])

    summary = {
        "model": "qwen3:8b",
        "temperature": 0,
        "num_predict": 2048,
        "cases": len(rows),
        "judge_runs": len(rows) * 3,
        "spearman_rho": float(correlation),
        "spearman_p_value": float(p_value),
        "mean_absolute_difference": mad,
        "cases_with_score_changes": sum(
            row["score_changed"] for row in rows
        ),
        "score_change_rate": float(np.mean([
            row["score_changed"] for row in rows
        ])),
        "mean_pairwise_absolute_change": float(np.mean(
            pairwise_changes
        )),
        "max_pairwise_absolute_change": max(pairwise_changes),
        "score_scale": "1 + 4 * normalized GEval score",
        "reference_label_provenance":
            "Must be documented accurately in report",
    }

    with (OUT / "judge_validation_cases.csv").open(
        "w", newline=""
    ) as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    (OUT / "judge_validation_summary.json").write_text(
        json.dumps(summary, indent=2)
    )

    print("\n=== JUDGE VALIDATION ===")
    print(json.dumps(summary, indent=2))
    print("\nSaved raw case data and validation summary.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--analyze", action="store_true")
    parser.add_argument("--case")
    parser.add_argument("--repeat", type=int)
    args = parser.parse_args()

    if args.worker:
        worker(args.case, args.repeat)
    elif args.analyze:
        analyze()
    else:
        run_batch()
