import json

from domain_server import (
    search_inspections,
    inspection_detail,
    restaurant_inspection_summary,
)


def execute_tool(name, inputs):
    try:
        if not isinstance(name, str) or not name.strip():
            result = {
                "ok": False,
                "data": None,
                "error": "tool name must be a non-empty string",
            }
            return json.dumps(result)

        if not isinstance(inputs, dict):
            result = {
                "ok": False,
                "data": None,
                "error": "inputs must be a JSON object",
            }
            return json.dumps(result)

    
        if name == "restaurant_inspection_summary":
            restaurant_id = inputs.get("restaurant_id")

            if (
                isinstance(restaurant_id, int)
                and restaurant_id > 5000
            ):
                result = {
                    "ok": False,
                    "data": None,
                    "error": (
                        "safety rule blocked restaurant_id values "
                        "greater than 5000"
                    ),
                }
                return json.dumps(result)

        tools = {
            "search_inspections": search_inspections,
            "inspection_detail": inspection_detail,
            "restaurant_inspection_summary":
                restaurant_inspection_summary,
        }

        tool = tools.get(name)

        if tool is None:
            result = {
                "ok": False,
                "data": None,
                "error": f"unknown tool: {name}",
            }
            return json.dumps(result)

        result = tool(**inputs)

        if not isinstance(result, dict):
            result = {
                "ok": False,
                "data": None,
                "error": "tool returned an invalid response",
            }

        return json.dumps(result)

    except TypeError as error:
        result = {
            "ok": False,
            "data": None,
            "error": f"invalid tool inputs: {error}",
        }

        return json.dumps(result)

    except Exception as error:
        result = {
            "ok": False,
            "data": None,
            "error": f"tool execution failed: {error}",
        }

        return json.dumps(result)