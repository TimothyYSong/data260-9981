import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "code"))

from src.model_client import ModelClient  # noqa: E402
from tool_executor import execute_tool  # noqa: E402


class AnsweringAgent:
    def __init__(self):
        self.model = ModelClient(
            model_name="qwen3:8b",
            temperature=0.0,
        )

    def answer(
        self,
        question,
        inspection_id,
        feedback=None,
        lessons=None,
    ):
        # Retrieve verified facts from the existing domain tool.
        raw_result = execute_tool(
            "inspection_detail",
            {"inspection_id": int(inspection_id)},
        )
        tool_result = json.loads(raw_result)

        if not tool_result.get("ok"):
            raise RuntimeError(
                f"Inspection lookup failed: {tool_result.get('error')}"
            )

        facts = tool_result["data"]

        # Load relevant lesson instructions if supplied.
        lesson_text = ""
        if lessons:
            lesson_text = "\n".join(
                f"- {lesson['correction']}"
                for lesson in lessons
            )

        feedback_text = feedback or "None"

        prompt = f"""
You are an Answering Agent for Local Restaurant Inspections.

Answer the user's question using ONLY the supplied
inspection record.

Never invent facts or change numbers.
Include every field requested by the question.
Keep your response concise and factual.

USER QUESTION:
{question}

INSPECTION RECORD:
{json.dumps(facts, indent=2)}

REUSABLE LESSONS:
{lesson_text or "None"}

EVALUATOR FEEDBACK:
{feedback_text}

Provide only the final natural-language answer.
"""

        response = self.model.complete(prompt)
        answer = response.content

        if not isinstance(answer, str) or not answer.strip():
            raise RuntimeError("Model returned an empty answer.")

        return {
            "question": question,
            "inspection_id": int(inspection_id),
            "answer": answer.strip(),
        }


if __name__ == "__main__":
    agent = AnsweringAgent()

    result = agent.answer(
        question="What is the violation count for inspection 10016?",
        inspection_id=10016,
    )

    print("\n=== ANSWERING AGENT TEST ===")
    print(json.dumps(result, indent=2))
