import json
import time
from pathlib import Path

from deepeval.metrics import GEval
from deepeval.models import OllamaModel
from deepeval.test_case import LLMTestCase, SingleTurnParams

ROOT = Path(__file__).resolve().parents[1]
cases = json.loads(
    (ROOT / "reports/hw10/eval_cases.json").read_text()
)

case = next(c for c in cases if c["case_id"] == "case_13")

model = OllamaModel(
    model="qwen3:8b",
    base_url="http://127.0.0.1:11434",
    temperature=0,
    generation_kwargs={"num_predict": 2048},
)

metric = GEval(
    name="Writer Helpfulness",
    evaluation_steps=[
        "Assess whether the actual output answers the user's question.",
        "Assess relevance, completeness, specificity, and usefulness.",
        "Treat an accurate not-found response as potentially helpful.",
        "Penalize generic answers that omit requested details.",
        "Penalize unsupported-task responses that do not answer.",
        "Use a five-level helpfulness judgment: 1 unhelpful, 2 mostly "
        "unhelpful, 3 partially helpful, 4 helpful, 5 fully helpful.",
    ],
    evaluation_params=[
        SingleTurnParams.INPUT,
        SingleTurnParams.ACTUAL_OUTPUT,
    ],
    model=model,
    async_mode=False,
)

test_case = LLMTestCase(
    input=case["question"],
    actual_output=case["draft"],
)

print("Evaluating:", case["case_id"], flush=True)
print("Question:", case["question"], flush=True)

started = time.monotonic()
metric.measure(test_case)

print("Raw GEval score:", metric.score)
print("Reason:", metric.reason)
print("Elapsed seconds:", round(time.monotonic() - started, 2))
