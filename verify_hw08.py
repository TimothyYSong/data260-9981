import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "code"))

from kafka_inspection_client import InspectionKafkaClient  # noqa: E402


SID4 = 9981
SEED = 9981
VERIFY_SEED = 269981
OUTPUT = ROOT / "reports" / "hw08" / "verification.json"


def git_commit():
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
    ).strip()


def main():
    checks = []
    client = None
    inspection_id = None

    def record(name, passed, detail):
        checks.append({
            "name": name,
            "passed": bool(passed),
            "result": "PASS" if passed else "FAIL",
            "detail": str(detail),
        })
        print(f"{'PASS' if passed else 'FAIL'}: {name} — {detail}")

    try:
        client = InspectionKafkaClient()

        create_cid = str(uuid4())
        create_response = client.request(
            operation="CREATE_INSPECTION",
            data={
                "restaurant_name": "HW8 Smoke Test",
                "inspection_type": "routine",
                "inspection_date": "2026-11-02T12:00:00",
                "description": "Verification round trip",
            },
            correlation_id=create_cid,
        )

        inspection_id = create_response.get("inspection_id")
        try:
            UUID(str(inspection_id))
            valid_uuid = True
        except (ValueError, TypeError):
            valid_uuid = False

        record(
            "CREATE_INSPECTION success and UUID",
            create_response.get("success") is True and valid_uuid,
            f"inspection_id={inspection_id}",
        )

        record(
            "CREATE correlation ID preserved",
            create_response.get("correlation_id") == create_cid,
            f"correlation_id={create_cid}",
        )

        if not valid_uuid:
            raise RuntimeError("Cannot GET without a valid inspection UUID")

        get_cid = str(uuid4())
        get_response = client.request(
            operation="GET_INSPECTION",
            data={"inspection_id": inspection_id},
            correlation_id=get_cid,
        )

        entity = get_response.get("entity")
        if not isinstance(entity, dict):
            entity = {}

        record(
            "GET_INSPECTION round trip",
            get_response.get("success") is True
            and entity.get("inspection_id") == inspection_id
            and entity.get("restaurant_name") == "HW8 Smoke Test"
            and entity.get("inspection_type") == "routine",
            f"retrieved_inspection_id={entity.get('inspection_id')}",
        )

        record(
            "GET correlation ID preserved",
            get_response.get("correlation_id") == get_cid,
            f"correlation_id={get_cid}",
        )

    except Exception as error:
        record("Kafka smoke-test execution", False, repr(error))

    finally:
        if client is not None:
            client.close()

        try:
            commit = git_commit()
        except Exception:
            commit = None

        output = {
            "homework": 8,
            "sid4": SID4,
            "commit_hash": commit,
            "model": "No LLM invoked by this Kafka smoke test",
            "configuration": {
                "prefix": "s9981",
                "port_base": 8081,
                "domain": "Local Restaurant Inspections",
                "kafka_bootstrap_servers": os.getenv(
                    "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"
                ),
            },
            "seed": SEED,
            "verify_seed": VERIFY_SEED,
            "tested_at_utc": datetime.now(timezone.utc).isoformat(),
            "checks": checks,
            "overall": "PASS" if checks and all(
                check["passed"] for check in checks
            ) else "FAIL",
        }

        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(json.dumps(output, indent=2) + "\n")

        print(f"\nVerification written to {OUTPUT}")
        print(f"OVERALL: {output['overall']}")

        if output["overall"] != "PASS":
            sys.exit(1)


if __name__ == "__main__":
    main()
