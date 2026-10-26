"""Build reproducible Part 4 scenarios from real Bay Wheels trips."""

import hashlib
import json
from pathlib import Path

import duckdb

RAW = Path("reports/hw07/raw")
SOURCE = RAW / "202601-baywheels-tripdata.csv"
WEEKS = ["2026-01-05", "2026-01-12", "2026-01-19", "2026-01-26"]

con = duckdb.connect(":memory:")
con.execute(
    "CREATE TABLE trips AS SELECT * FROM read_csv_auto(?)",
    [str(SOURCE)],
)

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def build(name, min_seconds, max_seconds, rides_per_week):
    query = """
        WITH eligible AS (
            SELECT *,
                date_diff('second', started_at, ended_at)
                    AS duration_seconds,
                CAST(date_trunc('week', started_at) AS DATE)
                    AS week_start
            FROM trips
            WHERE rideable_type = 'classic_bike'
              AND date_diff('second', started_at, ended_at)
                  BETWEEN ? AND ?
              AND CAST(date_trunc('week', started_at) AS DATE)
                  IN ('2026-01-05', '2026-01-12',
                      '2026-01-19', '2026-01-26')
        ),
        ranked AS (
            SELECT *,
                ROW_NUMBER() OVER (
                    PARTITION BY week_start ORDER BY ride_id
                ) AS sample_rank
            FROM eligible
        )
        SELECT *
        FROM ranked
        WHERE sample_rank <= 125
        ORDER BY week_start, sample_rank
    """

    df = con.execute(
        query, [min_seconds, max_seconds]
    ).df()

    assert len(df) == 500, f"{name}: expected 500 rows"

    df["scenario_selected"] = False

    for week, selected_count in zip(WEEKS, rides_per_week):
        mask = (
            (df["week_start"].astype(str) == week)
            & (df["sample_rank"] <= selected_count)
        )
        df.loc[mask, "scenario_selected"] = True

    assert int(df["scenario_selected"].sum()) == sum(rides_per_week)

    output = RAW / f"part4_{name}_500.csv"
    df.to_csv(output, index=False)

    selected = df[df["scenario_selected"]]
    print(f"\n{name.upper()}")
    print("Source rows:", len(df))
    print("Selected rides:", len(selected))
    print(
        "Average selected duration:",
        round(selected["duration_seconds"].mean() / 60, 2),
        "minutes",
    )
    print(
        "Weekly selected rides:",
        selected.groupby("week_start").size().to_dict(),
    )
    print("Output:", output)
    print("SHA-256:", sha256(output))

    return {
        "scenario": name,
        "source_rows": len(df),
        "selected_rides": len(selected),
        "weekly_selected_rides": rides_per_week,
        "scenario_file": str(output),
        "scenario_sha256": sha256(output),
    }

high = build("membership", 1200, 2400, [6, 6, 6, 6])
low = build("pay_per_use", 60, 600, [1, 1, 1, 0])

metadata = {
    "source": str(SOURCE),
    "source_sha256": sha256(SOURCE),
    "method": (
        "500 authentic classic-bike observations per scenario. "
        "scenario_selected identifies a hypothetical monthly "
        "rider profile, not a recovered individual customer."
    ),
    "scenarios": [high, low],
}

metadata_path = RAW / "part4_scenario_metadata.json"
metadata_path.write_text(json.dumps(metadata, indent=2))

print("\nSTEP 3C: PASS")
