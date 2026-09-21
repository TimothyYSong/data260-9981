import json
from pathlib import Path
from statistics import mean


RAW_DIR = Path("reports/hw03/raw")
METRICS_PATH = Path("reports/hw03/METRICS.md")

TECHNIQUES = [
    "token",
    "semantic",
    "sentence_window"
]


with open(
    RAW_DIR / "chunk_stats.json",
    "r",
    encoding="utf-8"
) as f:
    chunk_stats = json.load(f)


all_runs = {
    "token": [],
    "semantic": [],
    "sentence_window": []
}


for technique in TECHNIQUES:
    for file_path in sorted(
        RAW_DIR.glob(f"{technique}_q*.json")
    ):
        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as f:
            data = json.load(f)

        all_runs[technique].append(data)


summary = {}


for technique in TECHNIQUES:
    runs = all_runs[technique]

    if not runs:
        raise ValueError(
            f"No retrieval files found for {technique}"
        )

    top1_cosines = []
    all_cosines = []
    latencies = []
    recall_hits = 0

    for run in runs:
        results = run["results"]

        if not results:
            continue

        query_cosines = [
            result["cosine_sim"]
            for result in results
        ]

        top1_cosines.append(
            max(query_cosines)
        )

        all_cosines.extend(
            query_cosines
        )

        latencies.append(
            run["latency_ms"]
        )

        expected_source = run[
            "expected_source"
        ]

        retrieved_sources = [
            result["source_file"]
            for result in results
        ]

        if expected_source in retrieved_sources:
            recall_hits += 1


    recall_at_k = (
        recall_hits / len(runs)
    )


    summary[technique] = {
        "chunks": (
            chunk_stats[
                technique
            ]["chunks"]
        ),
        "avg_chunk_len": (
            chunk_stats[
                technique
            ]["avg_chunk_len"]
        ),
        "top1_cosine": mean(
            top1_cosines
        ),
        "mean_at_k_cosine": mean(
            all_cosines
        ),
        "recall_at_k": recall_at_k,
        "mean_latency_ms": mean(
            latencies
        )
    }


print("\nHW3 Retrieval Quality Summary\n")

header = (
    f"{'Technique':<18}"
    f"{'Chunks':<10}"
    f"{'Avg Len':<12}"
    f"{'Top-1':<12}"
    f"{'Mean@k':<12}"
    f"{'Recall@k':<12}"
    f"{'Latency ms':<12}"
)

print(header)
print("-" * len(header))


display_names = {
    "token": "Token",
    "semantic": "Semantic",
    "sentence_window": "Sentence Window"
}


for technique in TECHNIQUES:
    values = summary[technique]

    print(
        f"{display_names[technique]:<18}"
        f"{values['chunks']:<10}"
        f"{values['avg_chunk_len']:<12.2f}"
        f"{values['top1_cosine']:<12.4f}"
        f"{values['mean_at_k_cosine']:<12.4f}"
        f"{values['recall_at_k']:<12.2f}"
        f"{values['mean_latency_ms']:<12.2f}"
    )


markdown_lines = [
    "# HW3 Retrieval Metrics",
    "",
    "All metrics below were recomputed from the machine-readable JSON files in `reports/hw03/raw/`.",
    "",
    "| Technique | Chunks | Avg chunk length (characters) | Top-1 cosine | Mean@k cosine | Recall@k | Mean retrieval latency (ms) |",
    "|---|---:|---:|---:|---:|---:|---:|"
]


for technique in TECHNIQUES:
    values = summary[technique]

    markdown_lines.append(
        "| "
        f"{display_names[technique]} | "
        f"{values['chunks']} | "
        f"{values['avg_chunk_len']:.2f} | "
        f"{values['top1_cosine']:.4f} | "
        f"{values['mean_at_k_cosine']:.4f} | "
        f"{values['recall_at_k']:.2f} | "
        f"{values['mean_latency_ms']:.2f} |"
    )


markdown_lines.extend(
    [
        "",
        "## Metric Definitions",
        "",
        "- **Chunks:** Total number of chunks produced by the technique.",
        "- **Avg chunk length:** Mean number of characters per chunk.",
        "- **Top-1 cosine:** Mean across the five questions of the highest cosine similarity among each question's top-k retrieved chunks.",
        "- **Mean@k cosine:** Mean cosine similarity across all retrieved top-k chunks for all five questions.",
        "- **Recall@k:** Fraction of questions for which the expected source file appeared anywhere in the top-k retrieved results.",
        "- **Mean retrieval latency:** Mean similarity-search latency across the five questions."
    ]
)


with open(
    METRICS_PATH,
    "w",
    encoding="utf-8"
) as f:
    f.write(
        "\n".join(markdown_lines)
        + "\n"
    )


print(
    f"\nSaved metrics to: "
    f"{METRICS_PATH}"
)