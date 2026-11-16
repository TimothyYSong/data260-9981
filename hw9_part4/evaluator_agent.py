import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent
sys.path.insert(0, str(ROOT))

from src.model_client import ModelClient  # noqa: E402


class EvaluatorAgent:
    def __init__(self):
        reference = json.loads(
            (BASE / "reference_data.json").read_text(
                encoding="utf-8"
            )
        )
        self.records = {
            int(record["inspection_id"]): record
            for record in reference["inspections"]
        }
        self.model = ModelClient(
            model_name="qwen3:8b",
            temperature=0.0,
        )

    def evaluate(self, question, inspection_id, answer):
        inspection_id = int(inspection_id)

        if inspection_id not in self.records:
            raise ValueError(
                f"Inspection {inspection_id} not in reference dataset"
            )

        record = self.records[inspection_id]
        q = question.lower()
        a = answer.lower()
        required = {}

        if "violation" in q:
            required["violation_count"] = str(
                record["violation_count"]
            )
        if "restaurant name" in q:
            required["restaurant_name"] = record["restaurant_name"]
        if "address" in q:
            required["restaurant_address"] = record["restaurant_address"]
        if "inspection code" in q:
            required["inspection_code"] = record["inspection_code"]

        # Deterministic verification of required facts.
        issues = []

        for field, value in required.items():
            if field == "violation_count":
                found = re.search(
                    rf"(?<!\d){re.escape(value)}(?!\d)",
                    a,
                )
            else:
                found = value.lower() in a

            if not found:
                issues.append({
                    "field": field,
                    "expected": value,
                })

        mentioned_ids = {
            int(x)
            for x in re.findall(
                r"\b(?:inspection\s+|INSP-)(\d{5})\b",
                answer,
                flags=re.IGNORECASE,
            )
        }

        if mentioned_ids - {inspection_id}:
            issues.append({
                "field": "inspection_id",
                "expected": str(inspection_id),
            })

        # Independent LLM evaluation.
        prompt = f"""
You are an independent Evaluator Agent for
Local Restaurant Inspection questions.

Evaluate the ANSWER against the QUESTION and
GROUND TRUTH.

Reject answers that:
- Omit requested facts.
- Include incorrect values or identifiers.
- Contain contradictory statements.
- Add unsupported factual claims.
- Answer a different question.

GROUND TRUTH:
{json.dumps(record, indent=2)}

QUESTION:
{question}

ANSWER:
{answer}

Your response MUST begin with exactly one of:
PASS
REVISE

Then provide:
Reason: a concise explanation
Correction: what must change, or None

Only return PASS when the answer is fully supported
by the reference record and answers the question.
Do not invent facts.
"""
        response = self.model.complete(prompt)
        llm_assessment = response.content.strip()

        # Fail closed if the model's verdict is unparseable.
        match = re.match(
            r"^\s*(PASS|REVISE)\b",
            llm_assessment,
            flags=re.IGNORECASE,
        )

        llm_result = (
            match.group(1).upper()
            if match else "UNKNOWN"
        )

        deterministic_pass = len(issues) == 0

        # Both evaluations must approve.
        passed = (
            deterministic_pass
            and llm_result == "PASS"
        )

        if passed:
            return {
                "result": "PASS",
                "explanation": (
                    "Deterministic and LLM checks passed."
                ),
                "feedback": None,
                "missing_or_incorrect": [],
                "llm_result": llm_result,
                "llm_assessment": llm_assessment,
            }

        corrections = [
            f"{item['field']}={item['expected']}"
            for item in issues
        ]

        if corrections:
            feedback = (
                "Correct using these reference facts: "
                + "; ".join(corrections)
            )
        else:
            feedback = (
                "Revise the answer based on this evaluator "
                "assessment:\n" + llm_assessment
            )

        if llm_result == "REVISE":
            feedback += (
                "\nAlso address the evaluator's concerns:\n"
                + llm_assessment
            )

        return {
            "result": "REVISE",
            "explanation": (
                "One or both evaluation checks rejected "
                "the answer."
            ),
            "feedback": feedback,
            "missing_or_incorrect": issues,
            "llm_result": llm_result,
            "llm_assessment": llm_assessment,
        }


if __name__ == "__main__":
    evaluator = EvaluatorAgent()
    question = "What is the violation count for inspection 10016?"

    cases = [
        ("Correct", "Inspection 10016 has 0 violations."),
        ("Incorrect", "Inspection 10016 has 3 violations."),
        ("Incomplete", "Inspection 10016 was inspected."),
    ]

    for label, answer in cases:
        result = evaluator.evaluate(question, 10016, answer)
        print(f"\n=== {label} ===")
        print(json.dumps(result, indent=2))
