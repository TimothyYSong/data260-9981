"""DATA 260 HW7 Part 4: Bounded ReAct execution and trace collection."""

import json
import time
from datetime import datetime, timezone

from bikeshare_agent import create_bikeshare_agent
from bikeshare_costs import compare_costs


def run_bikeshare_scenario(csv_path, pricing_url):
    """Run the framework agent and collect structured results."""

    costs = compare_costs(csv_path)

    agent, tools = create_bikeshare_agent(csv_path)

    prompt = f"""
Analyze the uploaded Bay Wheels scenario.

Pricing URL: {pricing_url}

Dataset contains {costs['source_rows']} real source observations.
There are {costs['selected_rides']} hypothetical selected rider trips.

Required tool workflow:
1. Call csv_sql with:
   SELECT COUNT(*) AS total FROM trips;
2. Call csv_sql with:
   SELECT COUNT(*) AS total FROM trips
   WHERE scenario_selected = TRUE;
3. Call policy_retriever using the official pricing URL to
   retrieve the $29 monthly pass, $1 unlock fee, $0.19/min
   classic-bike rate, and 45-minute member allowance.
4. Call calculator to verify the difference between the
   pay-per-use total and membership total.

All four operations are required before the final response.

Execution rules:
- Complete the four required tool calls exactly once.
- After all four tools succeed, immediately produce the final answer.
- Do not repeat successful tool calls.
- Every policy_retriever call MUST include both:
  url = https://lyftbikes.com/pricing
  query = monthly pass unlock fee classic bike pricing
- Do not omit the URL argument under any circumstances.
- If a tool reports an error, correct it once if possible.
- The recommendation must match the lower verified total cost.
- If pay-per-use is cheaper, explicitly say pay-per-use saves
  money, NOT that membership saves money.
- Do not invent weekly costs. The application will display
  the exact deterministic weekly spending table.
- Do not claim that three monthly rides justify membership.
- Use a final decision of exactly:
  Buy Monthly Membership
  OR
  Pay Per Ride/Minute

Important:
- member_casual is the historical category in the source
  data, not the hypothetical rider's membership choice.
- Only scenario_selected = TRUE rows represent the
  hypothetical monthly riding profile.
- The $1 unlock fee applies to EACH pay-per-use ride.
- Savings are MONTHLY for this comparison, not annual.
- Do not substitute electric-bike records for classic bikes.
- Use the supplied verified costs rather than estimating
  costs from aggregate system-wide counts.
- Include the four-week summary from verified scenario data.
- Cite the official pricing page.
- Produce exactly one of the two required decisions.

Verified scenario calculations:
- Pay-per-use: ${costs['pay_per_use_total']:.2f}
- Monthly membership: ${costs['membership_total']:.2f}
- Membership residual: ${costs['membership_residual']:.2f}
- Break-even rides: {costs['break_even_rides']}
- Selected rides: {costs['selected_rides']}

Provide a concise rationale supported by the pricing policy.
Do not invent additional charges or change the verified calculations.
"""

    start = time.perf_counter()
    timeline = []
    stop_reason = "success"
    final_answer = ""

    try:
        result = agent.invoke(
            {"messages": [{"role": "user", "content": prompt}]},
            config={"recursion_limit": 16},
        )

        for message in result["messages"]:
            for call in getattr(message, "tool_calls", []) or []:
                timeline.append({
                    "event": "tool_call",
                    "tool": call["name"],
                    "arguments": call["args"],
                })

            if getattr(message, "type", "") == "tool":
                try:
                    observation = json.loads(message.content)
                except (ValueError, TypeError):
                    observation = {"raw": str(message.content)}

                timeline.append({
                    "event": "observation",
                    "tool": message.name,
                    "result": observation,
                })

        final_answer = str(result["messages"][-1].content)

    except Exception as exc:
        stop_reason = "error"
        final_answer = f"Agent execution failed: {type(exc).__name__}: {exc}"

    elapsed = round(time.perf_counter() - start, 2)

    step_count = sum(
        item["event"] == "tool_call" for item in timeline
    )

    called_tools = {
        event["tool"]
        for event in timeline
        if event["event"] == "tool_call"
    }

    observations = [
        event["result"]
        for event in timeline
        if event["event"] == "observation"
    ]

    required_tools = {
        "csv_sql", "policy_retriever", "calculator"
    }

    if stop_reason == "success":
        if not required_tools.issubset(called_tools):
            stop_reason = "incomplete_tool_workflow"
        elif not observations or any(
            item.get("success") is not True
            for item in observations
        ):
            stop_reason = "tool_error"

    savings = costs["savings"]
    rides = costs["selected_rides"]
    break_even = costs["break_even_rides"]

    if costs["decision"] == "Buy Monthly Membership":
        comparison = (
            f"The monthly membership saves ${savings:.2f} "
            "relative to pay-per-use."
        )
    else:
        comparison = (
            f"Pay-per-use saves ${savings:.2f} "
            "relative to the monthly membership."
        )

    verified_justification = (
        f"The modeled rider takes {rides} classic-bike rides "
        f"within the January 2026 scenario. "
        f"At the official Bay Wheels rates, pay-per-use costs "
        f"${costs['pay_per_use_total']:.2f}, compared with "
        f"${costs['membership_total']:.2f} for the monthly pass. "
        f"{comparison} "
        f"The estimated break-even point is {break_even} rides "
        f"when the observed ride-duration mix is repeated. "
        f"These estimates use Bay Wheels pricing published at "
        f"{pricing_url} and exclude taxes, discounts, and credits."
    )

    # Preserve the exact pricing text returned during this run.
    from pathlib import Path
    import hashlib

    pricing_evidence = None
    for event in timeline:
        if event["event"] != "observation":
            continue
        if event["tool"] != "policy_retriever":
            continue

        observation = event["result"]
        if observation.get("success") is not True:
            continue

        data = observation.get("data", {})
        snapshot = data.get("snapshot_text")
        if not snapshot:
            continue

        digest = hashlib.sha256(
            snapshot.encode("utf-8")
        ).hexdigest()

        if digest != data.get("snapshot_sha256"):
            stop_reason = "pricing_hash_mismatch"
            continue

        output_dir = Path(csv_path).resolve().parent
        stem = Path(csv_path).stem

        snapshot_path = output_dir / f"{stem}_pricing_snapshot.txt"
        metadata_path = output_dir / f"{stem}_pricing_metadata.json"

        snapshot_path.write_text(snapshot, encoding="utf-8")

        pricing_evidence = {
            "source_url": data["url"],
            "accessed_at": data["accessed_at"],
            "sha256": digest,
            "snapshot_path": str(snapshot_path),
        }

        metadata_path.write_text(
            json.dumps(pricing_evidence, indent=2),
            encoding="utf-8",
        )
        break

    if pricing_evidence is None and stop_reason == "success":
        stop_reason = "missing_pricing_evidence"

    # Independently validate the model's actual tool observations.
    observed_counts = []
    observed_calculations = []
    policy_snapshots = []

    for event in timeline:
        if event["event"] != "observation":
            continue

        observation = event["result"]
        if observation.get("success") is not True:
            continue

        data = observation.get("data", {})

        if event["tool"] == "csv_sql":
            for row in data.get("rows", []):
                if isinstance(row, dict) and "total" in row:
                    observed_counts.append(row["total"])

        elif event["tool"] == "calculator":
            value = data.get("value")
            if isinstance(value, (int, float)):
                observed_calculations.append(float(value))

        elif event["tool"] == "policy_retriever":
            policy_snapshots.append(data.get("snapshot_text", ""))

    expected_difference = round(
        abs(costs["pay_per_use_total"] - costs["membership_total"]),
        2,
    )

    validation = {
        "source_count_matches": (
            costs["source_rows"] in observed_counts
        ),
        "selected_count_matches": (
            costs["selected_rides"] in observed_counts
        ),
        "calculator_matches": any(
            abs(abs(value) - expected_difference) < 0.011
            for value in observed_calculations
        ),
        "official_pricing_present": any(
            all(
                rate in snapshot
                for rate in ("$29/month", "$0.19/min", "$1.00")
            )
            for snapshot in policy_snapshots
        ),
        "pricing_snapshot_verified": pricing_evidence is not None,
    }

    if stop_reason == "success" and not all(validation.values()):
        stop_reason = "verification_failed"

    return {
        "validation": validation,
        "pricing_evidence": pricing_evidence,
        "verified_justification": verified_justification,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "csv_path": str(csv_path),
        "pricing_url": pricing_url,
        "costs": costs,
        "decision": costs["decision"],
        "agent_rationale": final_answer,
        "timeline": timeline,
        "step_count": step_count,
        "elapsed_seconds": elapsed,
        "stop_reason": stop_reason,
    }
