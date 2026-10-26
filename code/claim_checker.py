import re


def check_unsupported_claims(result):
    """Check recognizable factual identifiers against tool observations."""
    answer = str(result.get("answer") or "")
    history = result.get("history", [])

    supported_ids = set()
    supported_codes = set()

    def collect(record):
        if not isinstance(record, dict):
            return

        if "id" in record and record["id"] is not None:
            supported_ids.add(str(record["id"]))

        if (
            "inspection_code" in record
            and record["inspection_code"] is not None
        ):
            supported_codes.add(str(record["inspection_code"]).upper())

    for item in history:
        observation = item.get("result") or {}

        if observation.get("ok") is not True:
            continue

        data = observation.get("data")

        if isinstance(data, dict):
            collect(data)

        elif isinstance(data, list):
            for record in data:
                collect(record)

    # Match explicit inspection IDs, avoiding unrelated numbers.
    claimed_ids = set(
        re.findall(
            r"\binspection\s*(?:id|#|number)\s*[:#=-]?\s*(\d+)",
            answer,
            flags=re.IGNORECASE,
        )
    )

    # Inspection codes follow the observed INSP-12345 format.
    claimed_codes = set(
        code.upper()
        for code in re.findall(
            r"\bINSP-\d+\b",
            answer,
            flags=re.IGNORECASE,
        )
    )

    supported_values = {}

    for item in history:
        observation = item.get("result") or {}
        if observation.get("ok") is not True:
            continue

        data = observation.get("data")
        records = data if isinstance(data, list) else [data]

        for record in records:
            if not isinstance(record, dict):
                continue

            for field in (
                "created_at",
                "updated_at",
                "inspection_count",
                "total_violations",
                "average_violations",
                "violation_count",
            ):
                if record.get(field) is not None:
                    supported_values.setdefault(field, set()).add(
                        str(record[field])
                    )

    unsupported = []

    field_patterns = {
        "created_at": (
            r"\\bcreated[_\\s-]*at\\s*[:=]\\s*"
            r"(\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2})"
        ),
        "updated_at": (
            r"\\bupdated[_\\s-]*at\\s*[:=]\\s*"
            r"(\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2})"
        ),
        "inspection_count": (
            r"\\b(?:total\\s+)?inspections?\\s*[:=]\\s*(\\d+)"
        ),
        "total_violations": (
            r"\\btotal\\s+violations?\\s*[:=]\\s*(\\d+)"
        ),
        "average_violations": (
            r"\\baverage\\s+violations?\\s*[:=]\\s*(\\d+(?:\\.\\d+)?)"
        ),
        "violation_count": (
            r"\\bviolation\\s+count\\s*[:=]\\s*(\\d+)"
        ),
    }

    for field, pattern in field_patterns.items():
        for match in re.findall(
            pattern.replace("\\\\", "\\"),
            answer,
            flags=re.IGNORECASE,
        ):
            supported = supported_values.get(field, set())

            if field == "average_violations":
                matches = any(
                    float(match) == float(value)
                    for value in supported
                )
            else:
                matches = match in supported

            if not matches:
                unsupported.append(
                    {
                        "type": field,
                        "value": match,
                        "reason": (
                            "Value not supported by successful "
                            "tool observations"
                        ),
                    }
                )

    for inspection_id in sorted(claimed_ids - supported_ids):
        unsupported.append(
            {
                "type": "inspection_id",
                "value": inspection_id,
                "reason": "ID not supported by successful tool observations",
            }
        )

    for code in sorted(claimed_codes - supported_codes):
        unsupported.append(
            {
                "type": "inspection_code",
                "value": code,
                "reason": "Code not supported by successful tool observations",
            }
        )

    return {
        "unsupported_claim_count": len(unsupported),
        "unsupported_claims": unsupported,
        "claimed_inspection_ids": sorted(claimed_ids),
        "claimed_inspection_codes": sorted(claimed_codes),
        "supported_inspection_ids": sorted(supported_ids),
        "supported_inspection_codes": sorted(supported_codes),
    }
