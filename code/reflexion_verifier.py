import re


def verify_task(case, result):
    case_id = case["case_id"]
    history = result.get("history", [])
    expected = case["expected_tools"]

    actual = [item.get("tool") for item in history]
    failures = []

    if actual != expected:
        failures.append(
            {
                "check": "tool_sequence",
                "expected": expected,
                "actual": actual,
                "message": "Required multi-step tool sequence was not completed.",
            }
        )

    for index, item in enumerate(history):
        observation = item.get("result", {})

        if observation.get("ok") is not True:
            failures.append(
                {
                    "check": "tool_success",
                    "step": index + 1,
                    "tool": item.get("tool"),
                    "observation": observation,
                    "message": "Tool did not complete successfully.",
                }
            )

    if len(history) == len(expected) and history:
        search_data = history[0].get("result", {}).get("data") or []

        if not search_data:
            failures.append(
                {
                    "check": "search_results",
                    "message": "Search returned no inspection records.",
                }
            )

        elif case_id == "A":
            actual_id = history[1].get("inputs", {}).get(
                "inspection_id"
            )
            expected_id = search_data[0]["id"]

            if actual_id != expected_id:
                failures.append(
                    {
                        "check": "first_result_lookup",
                        "expected": expected_id,
                        "actual": actual_id,
                        "message": "Detail lookup did not use the first result.",
                    }
                )

        elif case_id == "B":
            expected_restaurant = search_data[0]["restaurant_id"]
            actual_restaurant = history[1].get(
                "inputs", {}
            ).get("restaurant_id")

            expected_inspection = search_data[0]["id"]
            actual_inspection = history[2].get(
                "inputs", {}
            ).get("inspection_id")

            if actual_restaurant != expected_restaurant:
                failures.append(
                    {
                        "check": "summary_restaurant_id",
                        "expected": expected_restaurant,
                        "actual": actual_restaurant,
                        "message": "Summary used the wrong restaurant ID.",
                    }
                )

            if actual_inspection != expected_inspection:
                failures.append(
                    {
                        "check": "supporting_inspection",
                        "expected": expected_inspection,
                        "actual": actual_inspection,
                        "message": "Supporting inspection ID was incorrect.",
                    }
                )

        elif case_id == "C":
            if len(search_data) < 2:
                failures.append(
                    {
                        "check": "distinct_search_results",
                        "message": "Fewer than two inspections were returned.",
                    }
                )

            else:
                expected_ids = [
                    search_data[0]["id"],
                    search_data[1]["id"],
                ]
                actual_ids = [
                    history[1].get("inputs", {}).get("inspection_id"),
                    history[2].get("inputs", {}).get("inspection_id"),
                ]

                if actual_ids != expected_ids:
                    failures.append(
                        {
                            "check": "comparison_ids",
                            "expected": expected_ids,
                            "actual": actual_ids,
                            "message": "Comparison used incorrect inspection IDs.",
                        }
                    )

    answer = str(result.get("answer") or "")

    if not answer.strip():
        failures.append(
            {
                "check": "final_answer",
                "message": "Agent did not produce a final answer.",
            }
        )

    # Check that the answer references the required inspection IDs.
    # This is deliberately a limited deterministic check, not a
    # semantic evaluation of every claim.
    if answer.strip() and len(history) == len(expected):
        if case_id in ("A", "B"):
            inspection_id = history[-1].get(
                "inputs", {}
            ).get("inspection_id")

            if (
                inspection_id is not None
                and not re.search(
                    rf"\b{inspection_id}\b",
                    answer,
                )
            ):
                failures.append(
                    {
                        "check": "answer_inspection_id",
                        "expected": inspection_id,
                        "message": "Final answer omitted the inspection ID.",
                    }
                )

        elif case_id == "C":
            ids = [
                history[1].get("inputs", {}).get("inspection_id"),
                history[2].get("inputs", {}).get("inspection_id"),
            ]

            for inspection_id in ids:
                if (
                    inspection_id is not None
                    and not re.search(
                        rf"\b{inspection_id}\b",
                        answer,
                    )
                ):
                    failures.append(
                        {
                            "check": "answer_comparison_id",
                            "expected": inspection_id,
                            "message": "Final answer omitted a comparison ID.",
                        }
                    )

    if result.get("stop_reason") != "normal_completion":
        failures.append(
            {
                "check": "stop_reason",
                "actual": result.get("stop_reason"),
                "message": "Agent did not finish normally.",
            }
        )

    return {
        "case_id": case_id,
        "passed": len(failures) == 0,
        "failures": failures,
        "tool_calls": result.get("tool_calls", 0),
        "run_id": result.get("run_id"),
    }
