from evaluator_agent import EvaluatorAgent

evaluator = EvaluatorAgent()

question = "What is the violation count for inspection 10016?"

cases = [
    (
        "Correct answer",
        "Inspection 10016 has 0 violations.",
        "PASS",
    ),
    (
        "Wrong violation count",
        "Inspection 10016 has 3 violations.",
        "REVISE",
    ),
    (
        "Contradictory answer",
        "Inspection 10016 has 0 violations and also 3 violations.",
        "REVISE",
    ),
    (
        "Unsupported additional fact",
        "Inspection 10016 has 0 violations and was permanently closed.",
        "REVISE",
    ),
    (
        "Missing answer",
        "Inspection 10016 was reviewed.",
        "REVISE",
    ),
    (
        "Wrong inspection ID",
        "Inspection 10017 has 0 violations.",
        "REVISE",
    ),
]

passed = 0

for label, answer, expected in cases:
    result = evaluator.evaluate(
        question=question,
        inspection_id=10016,
        answer=answer,
    )

    actual = result["result"]
    llm = result.get("llm_assessment", "")

    correct = actual == expected
    passed += int(correct)

    print(f"\n=== {label} ===")
    print(f"Expected: {expected}")
    print(f"Actual: {actual}")
    print(f"Result: {'PASS' if correct else 'FAIL'}")
    print(f"LLM assessment: {llm}")

print(f"\nROBUSTNESS RESULT: {passed}/{len(cases)}")
