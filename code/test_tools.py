import json

import tool_executor
from agent import run_agent


def fake_search_inspections(query, limit=10):
    if not isinstance(query, str) or not query.strip():
        return {
            "ok": False,
            "data": None,
            "error": "query must be a non-empty string",
        }

    if not isinstance(limit, int) or limit < 1 or limit > 25:
        return {
            "ok": False,
            "data": None,
            "error": "limit must be between 1 and 25",
        }

    return {
        "ok": True,
        "data": [
            {
                "id": 1,
                "restaurant_name": "Test Restaurant",
                "inspection_code": "INSP-1",
                "violation_count": 2,
                "restaurant_id": 1,
            }
        ],
        "error": None,
    }


def fake_inspection_detail(inspection_id):
    if not isinstance(inspection_id, int) or inspection_id <= 0:
        return {
            "ok": False,
            "data": None,
            "error": "inspection_id must be a positive integer",
        }

    return {
        "ok": True,
        "data": {
            "id": inspection_id,
            "restaurant_name": "Test Restaurant",
            "restaurant_address": "1 Test Street",
            "inspection_code": f"INSP-{inspection_id}",
            "violation_count": 2,
            "restaurant_id": 1,
        },
        "error": None,
    }


def fake_restaurant_inspection_summary(restaurant_id):
    if not isinstance(restaurant_id, int) or restaurant_id <= 0:
        return {
            "ok": False,
            "data": None,
            "error": "restaurant_id must be a positive integer",
        }

    return {
        "ok": True,
        "data": {
            "restaurant_id": restaurant_id,
            "inspection_count": 1,
            "total_violations": 2,
            "average_violations": 2.0,
            "maximum_violations": 2,
        },
        "error": None,
    }


tool_executor.search_inspections = fake_search_inspections
tool_executor.inspection_detail = fake_inspection_detail
tool_executor.restaurant_inspection_summary = (
    fake_restaurant_inspection_summary
)


class MockModel:
    def generate(self, messages):
        return {
            "action": "tool",
            "tool": "search_inspections",
            "inputs": {
                "query": "Restaurant",
                "limit": 5,
            },
        }


passed = 0
total = 0


def run_test(name, test_function):
    global passed
    global total

    total += 1

    try:
        test_function()
        passed += 1
        print(f"PASS: {name}")

    except AssertionError as error:
        print(f"FAIL: {name} - {error}")

    except Exception as error:
        print(f"FAIL: {name} - unexpected error: {error}")


def test_search_valid():
    result = json.loads(
        tool_executor.execute_tool(
            "search_inspections",
            {
                "query": "Restaurant",
                "limit": 5,
            },
        )
    )

    assert result["ok"] is True
    assert result["error"] is None
    assert isinstance(result["data"], list)


def test_search_invalid():
    result = json.loads(
        tool_executor.execute_tool(
            "search_inspections",
            {
                "query": "Restaurant",
                "limit": 0,
            },
        )
    )

    assert result["ok"] is False
    assert result["data"] is None
    assert result["error"] == "limit must be between 1 and 25"


def test_detail_valid():
    result = json.loads(
        tool_executor.execute_tool(
            "inspection_detail",
            {
                "inspection_id": 1,
            },
        )
    )

    assert result["ok"] is True
    assert result["error"] is None
    assert result["data"]["id"] == 1


def test_detail_invalid():
    result = json.loads(
        tool_executor.execute_tool(
            "inspection_detail",
            {
                "inspection_id": 0,
            },
        )
    )

    assert result["ok"] is False
    assert result["data"] is None
    assert (
        result["error"]
        == "inspection_id must be a positive integer"
    )


def test_summary_valid():
    result = json.loads(
        tool_executor.execute_tool(
            "restaurant_inspection_summary",
            {
                "restaurant_id": 1,
            },
        )
    )

    assert result["ok"] is True
    assert result["error"] is None
    assert result["data"]["restaurant_id"] == 1


def test_summary_invalid():
    result = json.loads(
        tool_executor.execute_tool(
            "restaurant_inspection_summary",
            {
                "restaurant_id": 0,
            },
        )
    )

    assert result["ok"] is False
    assert result["data"] is None
    assert (
        result["error"]
        == "restaurant_id must be a positive integer"
    )


def test_safety_rule_blocked():
    result = json.loads(
        tool_executor.execute_tool(
            "restaurant_inspection_summary",
            {
                "restaurant_id": 5001,
            },
        )
    )

    assert result["ok"] is False
    assert result["data"] is None
    assert (
        result["error"]
        == "safety rule blocked restaurant_id values greater than 5000"
    )


def test_agent_max_steps():
    mock_model = MockModel()

    result = run_agent(
        "Keep searching for restaurant inspections.",
        max_steps=3,
        model=mock_model,
    )

    assert result["answer"] is None
    assert result["steps"] == 3
    assert result["stop_reason"] == "max_steps"
    assert (
        result["error"]
        == "maximum number of agent steps reached"
    )


if __name__ == "__main__":
    print("Student: Timothy Song")
    print("Part 4 + Part 5 Offline Domain Tool Tests")
    print()

    run_test(
        "search_inspections valid input",
        test_search_valid,
    )

    run_test(
        "search_inspections invalid input",
        test_search_invalid,
    )

    run_test(
        "inspection_detail valid input",
        test_detail_valid,
    )

    run_test(
        "inspection_detail invalid input",
        test_detail_invalid,
    )

    run_test(
        "restaurant_inspection_summary valid input",
        test_summary_valid,
    )

    run_test(
        "restaurant_inspection_summary invalid input",
        test_summary_invalid,
    )

    run_test(
        "execute_tool safety rule blocked",
        test_safety_rule_blocked,
    )

    run_test(
        "run_agent MockModel max_steps",
        test_agent_max_steps,
    )

    print()
    print(f"FINAL SUMMARY: {passed}/{total} tests passed")