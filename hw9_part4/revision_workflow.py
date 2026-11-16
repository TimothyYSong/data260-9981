import json
import time

from answering_agent import AnsweringAgent
from evaluator_agent import EvaluatorAgent


class RevisionWorkflow:
    MAX_ATTEMPTS = 2

    def __init__(self):
        self.answering_agent = AnsweringAgent()
        self.evaluator_agent = EvaluatorAgent()

    def run(
        self,
        question,
        inspection_id,
        controlled_failure=False,
        lessons=None,
    ):
        history = []
        feedback = None
        start = time.perf_counter()

        for attempt in range(1, self.MAX_ATTEMPTS + 1):

            # Controlled failure is ONLY for the training demo.
            if attempt == 1 and controlled_failure:
                answer = (
                    f"Inspection {inspection_id} has "
                    "3 violations."
                )
            else:
                response = self.answering_agent.answer(
                    question=question,
                    inspection_id=inspection_id,
                    feedback=feedback,
                    lessons=lessons,
                )
                answer = response["answer"]

            evaluation = self.evaluator_agent.evaluate(
                question=question,
                inspection_id=inspection_id,
                answer=answer,
            )

            history.append({
                "attempt": attempt,
                "answer": answer,
                "evaluation": evaluation,
            })

            print(f"\n=== ATTEMPT {attempt} ===")
            print("Question:", question)
            print("Answer:", answer)
            print("Evaluation:", evaluation["result"])
            print("Explanation:", evaluation["explanation"])

            if evaluation["feedback"]:
                print("Feedback:", evaluation["feedback"])

            if evaluation["result"] == "PASS":
                break

            feedback = evaluation["feedback"]

        latency_ms = (
            time.perf_counter() - start
        ) * 1000

        return {
            "question": question,
            "inspection_id": inspection_id,
            "final_answer": history[-1]["answer"],
            "final_evaluation": history[-1]["evaluation"]["result"],
            "attempts": len(history),
            "latency_ms": round(latency_ms, 2),
            "history": history,
        }


if __name__ == "__main__":
    workflow = RevisionWorkflow()

    print("\n" + "=" * 55)
    print("TEST 1: CONTROLLED FAILURE AND REPAIR")
    print("=" * 55)

    result1 = workflow.run(
        question="What is the violation count for inspection 10016?",
        inspection_id=10016,
        controlled_failure=True,
    )

    print("\n=== FINAL RESULT 1 ===")
    print(json.dumps(result1, indent=2))

    assert result1["attempts"] == 2
    assert result1["history"][0]["evaluation"]["result"] == "REVISE"
    assert result1["final_evaluation"] == "PASS"

    print("\n" + "=" * 55)
    print("TEST 2: NORMAL ANSWERING WORKFLOW")
    print("=" * 55)

    result2 = workflow.run(
        question="What is the violation count for inspection 10017?",
        inspection_id=10017,
    )

    print("\n=== FINAL RESULT 2 ===")
    print(json.dumps(result2, indent=2))

    assert result2["attempts"] <= 2
    assert result2["final_evaluation"] == "PASS"

    print("\nALL REVISION WORKFLOW TESTS PASSED")
