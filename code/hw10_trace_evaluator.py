"""Run the existing HW10 evaluator for a real Kafka response."""

import json
import sys
from contextlib import redirect_stdout

from hw10_evaluator import evaluate_case


def main():
    case = json.load(sys.stdin)

    # Keep progress logs separate from machine-readable JSON.
    with redirect_stdout(sys.stderr):
        result = evaluate_case(case)

    errors = {
        name: metric["error"]
        for name, metric in result["metrics"].items()
        if "error" in metric
    }

    if errors:
        print(json.dumps(errors), file=sys.stderr)
        raise SystemExit(1)

    # stdout contains exactly one JSON evaluation result.
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
