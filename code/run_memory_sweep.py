
import json
import os
import socket
import statistics
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen

import yaml

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "reports" / "hw06" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

URL = "http://127.0.0.1:8081"
STAMP = int(time.time())
WINDOW_SIZES = (4, 12, 30)

# The same 30 messages are used for every setting.
# Probe facts occur at the turns defined in memory_probes.yaml.
MESSAGES = [
    "I prioritize routine restaurant inspections.",
    "My inspection research is focused on Oakland.",
    "I want to examine inspection histories.",
    "I care about patterns over time.",
    "Please remember my inspection preferences.",
    "I also want to analyze food safety conditions.",
    "A key concern is cross-contamination.",
    "I want inspection records interpreted carefully.",
    "Another key concern is pest activity.",
    "Explain findings without inventing records.",
    "I want to track recurring violations.",
    "I prefer clear descriptions of violations.",
    "I want to know which problems persist.",
    "Use the last 12 months as my requested time range.",
    "I want meaningful comparisons of inspection results.",
    "Compare multiple restaurants, not just one.",
    "I want to spot improvements over time.",
    "Track whether problems were corrected.",
    "Pay attention to repeat failures.",
    "Keep the comparison practical.",
    "Format all final findings as concise bullet points.",
    "Emphasize actionable patterns.",
    "Highlight repeat violation counts.",
    "Avoid unsupported claims about individual restaurants.",
    "I want to narrow the geographic focus.",
    "Within Oakland, focus on Temescal.",
    "When inspecting results, prioritize recent information.",
    "Show the most recent routine inspection date first.",
    "Remember my comparison and reporting preferences.",
    "Acknowledge that you've recorded these preferences.",
]

assert len(MESSAGES) == 30

with (ROOT / "memory_probes.yaml").open(encoding="utf-8") as f:
    PROBES = yaml.safe_load(f)["probes"]

assert len(PROBES) == 5

# Deterministic answer-criteria checks. Each fact consists
# of groups of acceptable words or equivalent expressions.
CRITERIA = {
    "P1": [
        [("oakland",)],
        [("routine",), ("inspection", "inspections")],
    ],
    "P2": [
        [("cross contamination", "cross-contamination")],
        [("pest", "rodent", "vermin")],
    ],
    "P3": [
        [("12 months", "12-month", "past year", "last year")],
        [("multiple", "several", "different"),
         ("restaurants", "restaurant", "establishments")],
    ],
    "P4": [
        [("concise", "brief", "short"), ("bullet",)],
        [("repeat", "recurring"),
         ("violation",),
         ("count", "frequency", "number")],
    ],
    "P5": [
        [("temescal",)],
        [("recent", "latest", "last"),
         ("routine",),
         ("inspection",),
         ("date",)],
    ],
}


def score_probe(probe_id, answer):
    """Provisional 1-5 score using fixed answer criteria."""
    text = answer.lower()
    fact_scores = []

    for groups in CRITERIA[probe_id]:
        matched = sum(
            any(word in text for word in choices)
            for choices in groups
        )
        fact_scores.append(matched / len(groups))

    a, b = fact_scores

    if a == 1 and b == 1:
        return 5
    if min(a, b) >= 0.75:
        return 4
    if a > 0 and b > 0:
        return 3
    if max(a, b) > 0:
        return 2
    return 1


def api_chat(user_id, session_id, message):
    payload = json.dumps({
        "user_id": user_id,
        "session_id": session_id,
        "message": message,
    }).encode("utf-8")

    request = Request(
        f"{URL}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urlopen(request, timeout=300) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status}")
        return json.load(response)



def check_port_available():
    with socket.socket() as sock:
        sock.settimeout(1)

        # Check for an active listener rather than
        # binding a port that may be in TIME_WAIT.
        if sock.connect_ex(("127.0.0.1", 8081)) == 0:
            raise RuntimeError(
                "Port 8081 is occupied. Stop the existing "
                "FastAPI server with Control+C first."
            )



def start_server(n):
    env = os.environ.copy()
    env["SHORT_TERM_N"] = str(n)
    env["HW6_EXPERIMENT_NAME"] = f"short_term_n{n}"
    env["PYTHONPATH"] = os.pathsep.join([
        str(ROOT),
        str(ROOT / "code"),
        env.get("PYTHONPATH", ""),
    ])

    server_log_path = RAW / f"server_n{n}_{STAMP}.log"
    log_file = server_log_path.open("w", encoding="utf-8")

    process = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn",
            "main:app",
            "--app-dir", "code",
            "--host", "127.0.0.1",
            "--port", "8081",
        ],
        cwd=ROOT,
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
    )

    for _ in range(60):
        if process.poll() is not None:
            break

        try:
            with urlopen(f"{URL}/docs", timeout=2) as r:
                if r.status == 200:
                    return process, log_file
        except Exception:
            pass

        time.sleep(1)

    process.terminate()
    process.wait(timeout=10)
    log_file.close()

    raise RuntimeError(
        f"FastAPI failed to start. Check {server_log_path}"
    )


def stop_server(process, log_file):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

    log_file.close()


def run_setting(n):
    check_port_available()

    user_id = f"hw6_sweep_n{n}_{STAMP}"
    session_id = f"session_n{n}_{STAMP}"

    print(f"\n========== SHORT_TERM_N={n} ==========", flush=True)

    process, server_log = start_server(n)

    try:
        turns = []
        probe_results = []

        # Run the fixed 30-message conversation.
        for i, message in enumerate(MESSAGES, 1):
            result = api_chat(user_id, session_id, message)

            turns.append({
                "turn": i,
                "user_message": message,
                "assistant_reply": result["reply"],
            })

            print(f"Turn {i:02d}/30: PASS", flush=True)

        # Ask the same five probes afterward.
        for probe in PROBES:
            result = api_chat(
                user_id,
                session_id,
                probe["question"],
            )

            score = score_probe(
                probe["id"],
                result["reply"],
            )

            probe_results.append({
                "id": probe["id"],
                "question": probe["question"],
                "expected_answer": probe["expected_answer"],
                "actual_answer": result["reply"],
                "score": score,
            })

            print(
                f"Probe {probe['id']}: score {score}/5",
                flush=True,
            )

        # Read exactly this user's logged usage.
        usage_path = RAW / "memory_usage.jsonl"

        with usage_path.open(encoding="utf-8") as f:
            records = [
                json.loads(line)
                for line in f
                if line.strip()
            ]

        usage = [
            r for r in records
            if r["user_id"] == user_id
            and r["session_id"] == session_id
        ]

        assert len(usage) == 35, (
            f"Expected 35 usage records, got {len(usage)}"
        )

        # Only the 30 conversation turns contribute
        # to mean prompt tokens and mean latency.
        conversation_usage = usage[:30]

        assert all(
            r["short_term_n"] == n
            for r in conversation_usage
        )

        assert all(
            isinstance(r["prompt_tokens"], int)
            and r["prompt_tokens"] > 0
            for r in conversation_usage
        )

        assert all(
            r["latency_ms"] > 0
            for r in conversation_usage
        )

        summary = {
            "setting": f"SHORT_TERM_N={n}",
            "short_term_n": n,
            "user_id": user_id,
            "session_id": session_id,
            "conversation_turns": 30,
            "probe_turns": 5,
            "mean_prompt_tokens_per_turn": round(
                statistics.mean(
                    r["prompt_tokens"]
                    for r in conversation_usage
                ), 2
            ),
            "mean_latency_ms": round(
                statistics.mean(
                    r["latency_ms"]
                    for r in conversation_usage
                ), 2
            ),
            "mean_probe_quality": round(
                statistics.mean(
                    p["score"] for p in probe_results
                ), 2
            ),
        }

        detail = {
            "summary": summary,
            "conversation": turns,
            "probes": probe_results,
            "usage_records": usage,
            "scoring_method": (
                "Deterministic preliminary scoring "
                "against fixed answer criteria; "
                "review actual probe replies."
            ),
        }

        output_path = RAW / f"sweep_n{n}_{STAMP}.json"

        output_path.write_text(
            json.dumps(detail, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        print("Mean prompt tokens:",
              summary["mean_prompt_tokens_per_turn"])
        print("Mean latency (ms):",
              summary["mean_latency_ms"])
        print("Mean probe quality:",
              summary["mean_probe_quality"])
        print("Raw output:", output_path)

        return summary

    finally:
        stop_server(process, server_log)


def main():
    print("Timothy Song | DATA 260 HW6 | Part 3.3")
    print("Three short-term memory configurations")
    print("30 conversation messages + 5 probes each")
    print()

    
    summary_path = RAW / "short_term_sweep_summary.json"

    results = (
        json.loads(summary_path.read_text(encoding="utf-8"))
        if summary_path.exists()
        else []
    )


    
    for n in WINDOW_SIZES:
        if any(r["short_term_n"] == n for r in results):
            print(
                f"SKIP SHORT_TERM_N={n}: previously completed",
                flush=True,
            )
            continue

        result = run_setting(n)

        results.append(result)

        # Save incremental results after each setting.
        summary_path = RAW / "short_term_sweep_summary.json"
        summary_path.write_text(
            json.dumps(results, indent=2),
            encoding="utf-8",
        )

    print("\n========== FINAL RESULTS ==========")

    for result in results:
        print(
            result["setting"],
            "| Prompt:",
            result["mean_prompt_tokens_per_turn"],
            "| Latency:",
            result["mean_latency_ms"],
            "| Quality:",
            result["mean_probe_quality"],
        )

    print("\nPASS: All three 30-message experiments completed.")
    print("PASS: All 15 memory probes completed.")
    print("PASS: Raw experiment results saved.")


if __name__ == "__main__":
    main()
