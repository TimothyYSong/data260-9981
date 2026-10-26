import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "src"),
)

from model_client import ModelClient
from tool_executor import execute_tool


MODEL = "qwen3:8b"
MAX_STEPS = 8
MAX_REPAIRS = 1

ROOT = Path(__file__).resolve().parents[1]
LOG_FILE = ROOT / "reports/hw07/raw/agent_runs.jsonl"
RUN_LOG = ROOT / "reports/hw07/RUN_LOG.txt"

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_inspections",
            "description": (
                "Search restaurant inspections by restaurant name, "
                "address, or inspection code. Returns inspection IDs "
                "and restaurant IDs for follow-up tool calls."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 25,
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "inspection_detail",
            "description": (
                "Retrieve full inspection details using an inspection ID."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "inspection_id": {
                        "type": "integer",
                        "minimum": 1,
                    },
                },
                "required": ["inspection_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "restaurant_inspection_summary",
            "description": (
                "Calculate aggregate inspection statistics for one "
                "restaurant using its restaurant ID."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "restaurant_id": {
                        "type": "integer",
                        "minimum": 1,
                    },
                },
                "required": ["restaurant_id"],
            },
        },
    },
]

SCHEMAS_BY_NAME = {
    item["function"]["name"]: item["function"]
    for item in TOOL_SCHEMAS
}

SYSTEM_PROMPT = """
You are a tool-using assistant for local restaurant inspections.

Use the provided tools to answer inspection-data questions.
Never invent inspection IDs, restaurant IDs, statistics, or results.

For multi-step questions:
- Search first when you do not know the relevant IDs.
- Use the IDs returned by search for detail and summary calls.
- For aggregate questions, calculate the summary and retrieve
  at least one supporting inspection.
- For comparisons, retrieve details for both entities.
- Complete all necessary tool calls before answering.
- Do not request a follow-up prompt between tool calls.

Use at most one tool call at a time.
If a tool returns an ordinary "not found" result, explain that
result without inventing replacement data.
If you receive a validation error, correct the tool call.
Only use information supported by tool observations.
"""


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def write_log(record):
    entry = {
        "timestamp": timestamp(),
        **record,
    }

    LOG_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    RUN_LOG.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    line = json.dumps(
        entry,
        ensure_ascii=False,
        default=str,
    )

    with LOG_FILE.open("a", encoding="utf-8") as file:
        file.write(line + "\n")

    with RUN_LOG.open("a", encoding="utf-8") as file:
        file.write(line + "\n")


def validate_tool_call(name, inputs):
    if name not in SCHEMAS_BY_NAME:
        return f"unknown tool: {name}"

    if not isinstance(inputs, dict):
        return "tool inputs must be a JSON object"

    properties = SCHEMAS_BY_NAME[name]["parameters"]["properties"]
    required = SCHEMAS_BY_NAME[name]["parameters"]["required"]

    for field in required:
        if field not in inputs:
            return f"missing required argument: {field}"

    for field, value in inputs.items():
        if field not in properties:
            return f"unexpected argument: {field}"

        specification = properties[field]
        expected_type = specification["type"]

        if expected_type == "string":
            if not isinstance(value, str) or not value.strip():
                return f"{field} must be a non-empty string"

        if expected_type == "integer":
            if type(value) is not int:
                return f"{field} must be an integer"

            minimum = specification.get("minimum")
            maximum = specification.get("maximum")

            if minimum is not None and value < minimum:
                return f"{field} must be at least {minimum}"

            if maximum is not None and value > maximum:
                return f"{field} must be at most {maximum}"

    return None


def run_agent(
    user_input,
    max_steps=MAX_STEPS,
    model=None,
    max_repairs=MAX_REPAIRS,
    max_tool_calls=None,
    max_total_tokens=None,
):
    run_id = uuid.uuid4().hex[:12]

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_input),
    ]

    tool_call_count = 0
    repair_count = 0
    total_tokens = 0
    input_tokens = 0
    output_tokens = 0
    history = []

    def log(event, **fields):
        write_log(
            {
                "run_id": run_id,
                "user_input": user_input,
                "event": event,
                **fields,
            }
        )

    def finish(answer, steps, stop_reason, error=None):
        result = {
            "run_id": run_id,
            "answer": answer,
            "steps": steps,
            "tool_calls": tool_call_count,
            "repairs": repair_count,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "stop_reason": stop_reason,
            "history": history,
        }

        if error is not None:
            result["error"] = error

        log(
            "agent_finished",
            steps=steps,
            tool_call_count=tool_call_count,
            repair_count=repair_count,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            stop_reason=stop_reason,
            answer=answer,
            error=error,
        )

        return result

    try:
        client = model if model is not None else ModelClient(
            model_name=MODEL,
            temperature=0.0,
        )
    except Exception as error:
        return finish(
            None,
            0,
            "model_error",
            str(error),
        )

    log(
        "agent_started",
        model=MODEL,
        max_steps=max_steps,
        max_repairs=max_repairs,
    )

    for step in range(1, max_steps + 1):
        try:
            remaining_tokens = (
                None
                if max_total_tokens is None
                else max_total_tokens - total_tokens
            )

            if (
                remaining_tokens is not None
                and remaining_tokens <= 0
            ):
                return finish(
                    None,
                    step,
                    "budget_exhausted",
                    "token budget reached",
                )

            if remaining_tokens is not None:
                input_reserve = 4000

                if remaining_tokens <= input_reserve:
                    return finish(
                        None,
                        step,
                        "budget_exhausted",
                        "insufficient remaining token budget",
                    )

                output_limit = min(
                    2000,
                    remaining_tokens - input_reserve,
                )

            response = client.complete(
                messages,
                tools=TOOL_SCHEMAS,
                **(
                    {}
                    if remaining_tokens is None
                    else {
                        "max_output_tokens": output_limit,
                    }
                ),
            )

            if not isinstance(response, AIMessage):
                raise TypeError(
                    "model adapter did not return an AIMessage"
                )

        except Exception as error:
            return finish(
                None,
                step,
                "model_error",
                str(error),
            )

        usage = response.usage_metadata or {}
        input_tokens += usage.get("input_tokens", 0)
        output_tokens += usage.get("output_tokens", 0)
        total_tokens += usage.get("total_tokens", 0)

        if (
            max_total_tokens is not None
            and total_tokens >= max_total_tokens
        ):
            return finish(
                None,
                step,
                "budget_exhausted",
                "token budget reached",
            )

        invalid_calls = response.invalid_tool_calls or []
        tool_calls = response.tool_calls or []

        if invalid_calls:
            problem = (
                "Malformed tool-call arguments: "
                + str(invalid_calls[0].get("error", "invalid JSON"))
            )

            log(
                "invalid_tool_call",
                step=step,
                problem=problem,
            )

            if repair_count >= max_repairs:
                return finish(
                    None,
                    step,
                    "repair_exhausted",
                    problem,
                )

            repair_count += 1
            messages.append(
                HumanMessage(
                    content=(
                        f"Your previous tool call failed: {problem}. "
                        "Correct the tool name and arguments, "
                        "then try again once."
                    )
                )
            )
            continue

        if not tool_calls:
            answer = response.content
            if isinstance(answer, list):
                answer = json.dumps(answer, ensure_ascii=False)

            answer = str(answer).strip()

            if tool_call_count == 0:
                problem = (
                    "You must use the inspection tools before "
                    "answering a question about inspection data."
                )

                log(
                    "text_without_tool",
                    step=step,
                    problem=problem,
                    answer=answer,
                )

                if repair_count >= max_repairs:
                    return finish(
                        None,
                        step,
                        "repair_exhausted",
                        problem,
                    )

                repair_count += 1
                messages.append(
                    HumanMessage(
                        content=(
                            problem
                            + " Make the appropriate tool call now."
                        )
                    )
                )
                continue

            return finish(
                answer,
                step,
                "normal_completion",
            )

        # Keep the model's tool-call message in conversation history.
        messages.append(response)

        for call in tool_calls:
            name = call.get("name")
            inputs = call.get("args")
            call_id = call.get("id")

            problem = validate_tool_call(name, inputs)

            if problem is not None:
                result = {
                    "ok": False,
                    "data": None,
                    "error": problem,
                }

                history.append(
                    {
                        "step": step,
                        "tool": name,
                        "inputs": inputs,
                        "result": result,
                        "validation_error": True,
                    }
                )

                log(
                    "tool_validation_failed",
                    step=step,
                    tool_call=name,
                    tool_input=inputs,
                    tool_result=result,
                    problem=problem,
                )

                messages.append(
                    ToolMessage(
                        content=json.dumps(result),
                        tool_call_id=call_id,
                        name=str(name),
                    )
                )

                if repair_count >= max_repairs:
                    return finish(
                        None,
                        step,
                        "repair_exhausted",
                        problem,
                    )

                repair_count += 1
                messages.append(
                    HumanMessage(
                        content=(
                            f"The tool call failed validation: {problem}. "
                            "Correct it and retry once."
                        )
                    )
                )
                break

            if (
                max_tool_calls is not None
                and tool_call_count >= max_tool_calls
            ):
                return finish(
                    None,
                    step,
                    "budget_exhausted",
                    "tool-call budget reached",
                )

            tool_call_count += 1

            raw_result = execute_tool(name, inputs)

            try:
                result = json.loads(raw_result)
            except (TypeError, ValueError):
                result = {
                    "ok": False,
                    "data": None,
                    "error": "tool returned invalid JSON",
                }

            history.append(
                {
                    "step": step,
                    "tool": name,
                    "inputs": inputs,
                    "result": result,
                    "validation_error": False,
                }
            )

            log(
                "tool_invocation",
                step=step,
                tool_call=name,
                tool_input=inputs,
                tool_result=result,
                tool_call_count=tool_call_count,
            )

            messages.append(
                ToolMessage(
                    content=json.dumps(result),
                    tool_call_id=call_id,
                    name=name,
                )
            )

            if (
                result.get("ok") is False
                and str(result.get("error", "")).startswith(
                    "safety rule blocked"
                )
            ):
                return finish(
                    result["error"],
                    step,
                    "safety_rule_block",
                )

    return finish(
        None,
        max_steps,
        "max_steps",
        "maximum number of agent steps reached",
    )


if __name__ == "__main__":
    question = input(
        "Enter a restaurant-inspection question: "
    )

    print(
        json.dumps(
            run_agent(question),
            indent=2,
            ensure_ascii=False,
        )
    )
