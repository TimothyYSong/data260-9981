"""Deterministic Bay Wheels monthly cost comparisons."""

from math import ceil
from pathlib import Path

import pandas as pd

MONTHLY_PRICE = 29.0
SINGLE_UNLOCK = 1.0
SINGLE_CLASSIC_PER_MIN = 0.19
MEMBER_INCLUDED_MINUTES = 45
MEMBER_OVERAGE_PER_MIN = 0.17


def compare_costs(csv_path):
    """Compare monthly versus single-ride costs for a scenario CSV."""
    df = pd.read_csv(csv_path)

    required = {
        "ride_id", "rideable_type", "duration_seconds",
        "week_start", "scenario_selected",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    if len(df) < 500:
        raise ValueError("Scenario must contain at least 500 source rows.")

    selected = df.loc[
        df["scenario_selected"].astype(str).str.lower() == "true"
    ].copy()

    if selected.empty:
        raise ValueError("No scenario rides selected.")

    if not (selected["rideable_type"] == "classic_bike").all():
        raise ValueError("This pricing model supports classic bikes only.")

    if not (
        pd.to_numeric(selected["duration_seconds"], errors="coerce") > 0
    ).all():
        raise ValueError("All selected rides need positive durations.")

    selected["billable_minutes"] = selected["duration_seconds"].apply(
        lambda seconds: ceil(float(seconds) / 60)
    )
    selected["pay_cost"] = (
        SINGLE_UNLOCK
        + selected["billable_minutes"] * SINGLE_CLASSIC_PER_MIN
    )
    selected["member_residual"] = (
        (selected["billable_minutes"] - MEMBER_INCLUDED_MINUTES)
        .clip(lower=0) * MEMBER_OVERAGE_PER_MIN
    )

    pay_total = round(float(selected["pay_cost"].sum()), 2)
    residual = round(float(selected["member_residual"].sum()), 2)
    membership_total = round(MONTHLY_PRICE + residual, 2)

    decision = (
        "Buy Monthly Membership"
        if membership_total < pay_total
        else "Pay Per Ride/Minute"
    )

    savings = round(abs(pay_total - membership_total), 2)

    # Break-even assumes repeating the observed selected-ride mix.
    average_pay = float(selected["pay_cost"].mean())
    average_residual = float(selected["member_residual"].mean())
    net_savings_per_ride = average_pay - average_residual

    break_even_rides = (
        ceil(MONTHLY_PRICE / net_savings_per_ride)
        if net_savings_per_ride > 0
        else None
    )

    weekly = (
        selected.groupby("week_start", sort=True)
        .agg(
            ride_count=("ride_id", "count"),
            average_duration_minutes=(
                "duration_seconds",
                lambda s: round(float(s.mean()) / 60, 2),
            ),
            pay_per_use_spend=("pay_cost", "sum"),
            member_residual_spend=("member_residual", "sum"),
        )
        .reset_index()
    )

    for column in ("pay_per_use_spend", "member_residual_spend"):
        weekly[column] = weekly[column].round(2)

    return {
        "source_rows": int(len(df)),
        "selected_rides": int(len(selected)),
        "decision": decision,
        "pay_per_use_total": pay_total,
        "membership_base": MONTHLY_PRICE,
        "membership_residual": residual,
        "membership_total": membership_total,
        "savings": savings,
        "average_ride_minutes": round(
            float(selected["duration_seconds"].mean()) / 60, 2
        ),
        "break_even_rides": break_even_rides,
        "break_even_assumption": (
            "Repeats the observed selected-ride duration and fee mix."
        ),
        "weekly": weekly.to_dict(orient="records"),
        "assumptions": [
            "The source data does not identify individual customers.",
            "Selected real trips model a hypothetical monthly rider.",
            "Only classic-bike rides are priced.",
            "Per-ride durations are rounded up to whole minutes.",
            "Costs exclude taxes, discounts, and promotional credits.",
            "January observations are compared under the captured "
            "current pricing policy, not historical January rates.",
        ],
    }


if __name__ == "__main__":
    for name in ("membership", "pay_per_use"):
        path = Path(
            f"reports/hw07/raw/part4_{name}_500.csv"
        )
        result = compare_costs(path)

        print(f"\n=== {name.upper()} ===")
        for key in (
            "source_rows",
            "selected_rides",
            "decision",
            "pay_per_use_total",
            "membership_total",
            "membership_residual",
            "savings",
            "break_even_rides",
        ):
            print(f"{key}: {result[key]}")

        print("Weekly rows:", len(result["weekly"]))

        assert result["source_rows"] == 500
        assert result["membership_residual"] == 0
        assert (
            result["decision"] == "Buy Monthly Membership"
            if name == "membership"
            else result["decision"] == "Pay Per Ride/Minute"
        )

    print("\nSTEP 3E: PASS")
