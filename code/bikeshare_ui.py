"""DATA 260 HW7 Part 4: Bay Wheels Streamlit interface."""

import hashlib
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from bikeshare_runner import run_bikeshare_scenario


PRICING_URL = "https://lyftbikes.com/pricing"

st.set_page_config(
    page_title="Bay Wheels Membership Advisor",
    layout="wide",
)

st.title("Bay Wheels Membership Advisor")
st.caption("DATA 260 HW7 — Framework-Based ReAct/MRKL Agent")

st.info(
    "Upload a scenario CSV containing at least 500 real trip "
    "observations and a scenario_selected column identifying "
    "the hypothetical rider's monthly trips."
)

uploaded = st.file_uploader("Upload trip CSV", type=["csv"])

pricing_url = st.text_input(
    "Official pricing URL",
    value=PRICING_URL,
)

run_clicked = st.button(
    "Run Membership Analysis",
    type="primary",
)

if run_clicked:
    if uploaded is None:
        st.error("Upload a CSV before running the analysis.")

    elif pricing_url.strip() != PRICING_URL:
        st.error("Use the official Bay Wheels pricing URL.")

    else:
        raw_dir = Path("reports/hw07/raw")
        raw_dir.mkdir(parents=True, exist_ok=True)

        safe_name = Path(uploaded.name).name
        csv_path = raw_dir / safe_name
        csv_path.write_bytes(uploaded.getvalue())

        with st.spinner("Running framework agent and tools..."):
            try:
                result = run_bikeshare_scenario(
                    str(csv_path),
                    pricing_url,
                )
                st.session_state["bikeshare_result"] = result

            except Exception as exc:
                st.error(
                    f"Analysis failed: {type(exc).__name__}: {exc}"
                )

if "bikeshare_result" in st.session_state:
    result = st.session_state["bikeshare_result"]
    costs = result["costs"]

    st.divider()
    st.header("Membership Recommendation")
    st.subheader(result["decision"])
    st.write(result["verified_justification"])

    st.subheader("Cost Comparison")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Pay Per Ride/Minute",
        f"${costs['pay_per_use_total']:.2f}",
    )
    col2.metric(
        "Monthly Membership + Residual",
        f"${costs['membership_total']:.2f}",
    )
    col3.metric(
        "Savings with Recommended Option",
        f"${costs['savings']:.2f}",
    )

    st.write(
        f"**Membership base:** ${costs['membership_base']:.2f}"
    )
    st.write(
        f"**Residual charges:** ${costs['membership_residual']:.2f}"
    )
    st.write(
        f"**Break-even usage:** {costs['break_even_rides']} rides "
        f"versus {costs['selected_rides']} selected rides."
    )
    st.caption(costs["break_even_assumption"])

    st.subheader("Weekly Usage and Spending")

    weekly = pd.DataFrame(costs["weekly"])
    st.dataframe(
        weekly,
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Pricing Evidence and Citations")

    evidence = result.get("pricing_evidence")

    if evidence:
        st.write(f"**Source:** {evidence['source_url']}")
        st.write(f"**Captured:** {evidence['accessed_at']}")
        st.write(f"**SHA-256:** `{evidence['sha256']}`")

        snapshot_path = Path(evidence["snapshot_path"])

        if snapshot_path.exists():
            digest = hashlib.sha256(
                snapshot_path.read_bytes()
            ).hexdigest()

            st.write(
                "**SHA-256 verification:**",
                "PASS" if digest == evidence["sha256"] else "FAIL",
            )
    else:
        st.warning("No verified pricing snapshot was captured.")

    st.subheader("Execution Metrics")

    m1, m2, m3 = st.columns(3)
    m1.metric("Tool Steps", result["step_count"])
    m2.metric(
        "Total Time",
        f"{result['elapsed_seconds']:.2f} sec",
    )
    m3.metric("Stop Reason", result["stop_reason"])

    st.subheader("Tool-Call Timeline and Observations")

    for index, event in enumerate(result["timeline"], 1):
        if event["event"] == "tool_call":
            title = f"{index}. CALL — {event['tool']}"
            details = event["arguments"]
        else:
            title = f"{index}. OBSERVATION — {event['tool']}"
            details = event["result"]

        with st.expander(title):
            if (
                event["event"] == "observation"
                and event["tool"] == "policy_retriever"
                and isinstance(details, dict)
                and details.get("success")
            ):
                clean_details = dict(details)
                clean_data = dict(clean_details.get("data", {}))
                clean_data.pop("snapshot_text", None)
                clean_details["data"] = clean_data
                st.json(clean_details)
            else:
                st.json(details)

    st.subheader("Assumptions and Caveats")

    for assumption in costs["assumptions"]:
        st.write(f"- {assumption}")

    with st.expander("Raw Model Response — Unverified"):
        st.warning(
            "Model-generated prose may contain errors. "
            "The verified calculations above are authoritative."
        )
        st.write(result["agent_rationale"])
