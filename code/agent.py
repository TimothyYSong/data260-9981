import json
import os
from datetime import datetime, timezone

import requests

from tool_executor import execute_tool


MODEL = "qwen3:8b"
OLLAMA_URL = "http://localhost:11434/api/chat"
LOG_FILE = "reports/hw05/raw/agent_runs.jsonl"

TOOLS = [
    "search_inspections",
    "inspection_detail",
    "restaurant_inspection_summary",
]

SYSTEM_PROMPT = """
You are an agent for a Local Restaurant Inspections system.

You have exactly three tools:

1. search_inspections
   Inputs:
   {
     "query": string,
     "limit": integer from 1 to 25
   }

2. inspection_detail
   Inputs:
   {
     "inspection_id": positive integer
   }

3. restaurant_inspection_summary
   Inputs:
   {
     "restaurant_id": positive integer
   }

When you need a tool, respond ONLY with JSON in this form:

{
  "action": "tool",
  "tool": "tool_name",
  "inputs": {
    ...
  }
}

When you have enough information to answer the user, respond ONLY with:

{
  "action": "final",
  "answer": "your answer"
}

Do not invent tool results.
Use tool results before giving factual answers about inspection data.
"""


def write_log(record):
    os.makedirs(
        os.path.dirname(LOG_FILE),
        exist_ok=True,
    )

    record["timestamp"] = datetime.now(
        timezone.utc
    ).isoformat()

    with open(
        LOG_FILE,
        "a",
        encoding="utf-8",
    ) as file:
        file.write(
            json.dumps(record) + "\n"
        )


def call_ollama(messages):
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "messages": messages,
            "stream": False,
            "format": "json",
            "think": False,
        },
        timeout=60,
    )

    response.raise_for_status()

    data = response.json()
    content = data["message"]["content"]

    return json.loads(content)


def run_agent(user_input, max_steps=5, model=None):
    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": user_input,
        },
    ]

    tool_call_count = 0

    for step in range(1, max_steps + 1):
        try:
            if model is None:
                model_output = call_ollama(messages)
            else:
                model_output = model.generate(messages)

        except Exception as error:
            stop_reason = "model_error"

            write_log(
                {
                    "step": step,
                    "user_input": user_input,
                    "tool_call": None,
                    "tool_input": None,
                    "tool_result": None,
                    "tool_call_count": tool_call_count,
                    "stop_reason": stop_reason,
                    "error": str(error),
                }
            )

            return {
                "answer": None,
                "steps": step,
                "tool_calls": tool_call_count,
                "stop_reason": stop_reason,
                "error": str(error),
            }

        action = model_output.get("action")

        if action == "final":
            answer = model_output.get(
                "answer",
                "",
            )

            stop_reason = "normal_completion"

            write_log(
                {
                    "step": step,
                    "user_input": user_input,
                    "model_output": model_output,
                    "tool_call": None,
                    "tool_input": None,
                    "tool_result": None,
                    "tool_call_count": tool_call_count,
                    "final_answer": answer,
                    "stop_reason": stop_reason,
                }
            )

            return {
                "answer": answer,
                "steps": step,
                "tool_calls": tool_call_count,
                "stop_reason": stop_reason,
            }

        if action != "tool":
            stop_reason = "invalid_model_output"

            write_log(
                {
                    "step": step,
                    "user_input": user_input,
                    "model_output": model_output,
                    "tool_call": None,
                    "tool_input": None,
                    "tool_result": None,
                    "tool_call_count": tool_call_count,
                    "stop_reason": stop_reason,
                }
            )

            return {
                "answer": None,
                "steps": step,
                "tool_calls": tool_call_count,
                "stop_reason": stop_reason,
                "error": "model returned an invalid action",
            }

        tool_name = model_output.get("tool")
        tool_inputs = model_output.get(
            "inputs",
            {},
        )

        tool_call_count += 1

        if tool_name not in TOOLS:
            result = json.dumps(
                {
                    "ok": False,
                    "data": None,
                    "error": (
                        f"unknown tool requested by model: "
                        f"{tool_name}"
                    ),
                }
            )
        else:
            result = execute_tool(
                tool_name,
                tool_inputs,
            )

        result_object = json.loads(result)

        write_log(
            {
                "step": step,
                "user_input": user_input,
                "model_output": model_output,
                "tool_call": tool_name,
                "tool_input": tool_inputs,
                "tool_result": result_object,
                "tool_call_count": tool_call_count,
                "stop_reason": None,
            }
        )

        if (
            result_object.get("ok") is False
            and result_object.get("error", "").startswith(
                "safety rule blocked"
            )
        ):
            stop_reason = "safety_rule_block"

            write_log(
                {
                    "step": step,
                    "user_input": user_input,
                    "tool_call": tool_name,
                    "tool_input": tool_inputs,
                    "tool_result": result_object,
                    "tool_call_count": tool_call_count,
                    "stop_reason": stop_reason,
                }
            )

            return {
                "answer": result_object["error"],
                "steps": step,
                "tool_calls": tool_call_count,
                "stop_reason": stop_reason,
            }

        messages.append(
            {
                "role": "assistant",
                "content": json.dumps(
                    model_output
                ),
            }
        )

        messages.append(
            {
                "role": "user",
                "content": (
                    "Tool result:\n"
                    + result
                    + "\nUse this result to decide "
                    "whether another tool is needed "
                    "or return the final answer."
                ),
            }
        )

    stop_reason = "max_steps"

    write_log(
        {
            "step": max_steps,
            "user_input": user_input,
            "tool_call": None,
            "tool_input": None,
            "tool_result": None,
            "tool_call_count": tool_call_count,
            "stop_reason": stop_reason,
        }
    )

    return {
        "answer": None,
        "steps": max_steps,
        "tool_calls": tool_call_count,
        "stop_reason": stop_reason,
        "error": "maximum number of agent steps reached",
    }


if __name__ == "__main__":
    user_input = input(
        "Enter a restaurant-inspection question: "
    )

    result = run_agent(user_input)

    print(
        json.dumps(
            result,
            indent=2,
        )
    )