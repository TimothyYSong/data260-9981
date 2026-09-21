import json
from pathlib import Path

ROOT = Path(".")
HW3_DIR = ROOT / "reports" / "hw03"
RAW_DIR = HW3_DIR / "raw"
CORPUS_DIR = HW3_DIR / "corpus"
OUTPUT_PATH = HW3_DIR / "verification.json"

checks = {}

checks["questions_yaml_exists"] = (
    HW3_DIR / "questions.yaml"
).exists()

checks["question_count"] = 0

if checks["questions_yaml_exists"]:
    import yaml

    with open(
        HW3_DIR / "questions.yaml",
        "r",
        encoding="utf-8"
    ) as f:
        data = yaml.safe_load(f)

    checks["question_count"] = len(
        data.get("questions", [])
    )

checks["corpus_directory_exists"] = (
    CORPUS_DIR.exists()
)

checks["corpus_pdf_count"] = len(
    list(CORPUS_DIR.glob("*.pdf"))
)

checks["raw_directory_exists"] = (
    RAW_DIR.exists()
)

token_files = sorted(
    RAW_DIR.glob("token_q*.json")
)

semantic_files = sorted(
    RAW_DIR.glob("semantic_q*.json")
)

sentence_window_files = sorted(
    RAW_DIR.glob("sentence_window_q*.json")
)

retrieval_files = (
    token_files
    + semantic_files
    + sentence_window_files
)

checks["retrieval_json_count"] = len(
    retrieval_files
)

checks["token_result_count"] = len(
    token_files
)

checks["semantic_result_count"] = len(
    semantic_files
)

checks["sentence_window_result_count"] = len(
    sentence_window_files
)

checks["chunk_stats_exists"] = (
    RAW_DIR / "chunk_stats.json"
).exists()

checks["metrics_md_exists"] = (
    HW3_DIR / "METRICS.md"
).exists()

checks["run_log_exists"] = (
    HW3_DIR / "RUN_LOG.txt"
).exists()

checks["sources_md_exists"] = (
    HW3_DIR / "SOURCES.md"
).exists()

checks["corpus_manifest_exists"] = (
    HW3_DIR / "CORPUS_MANIFEST.json"
).exists()

checks["ai_use_exists"] = (
    HW3_DIR / "AI_USE.md"
).exists()

checks["run_instructions_exists"] = (
    HW3_DIR / "RUN_INSTRUCTIONS.md"
).exists()

checks["report_pdf_exists"] = (
    HW3_DIR / "report.pdf"
).exists()

embedding_dimensions = []

for file_path in retrieval_files:
    try:
        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as f:
            result = json.load(f)

        dimension = result.get(
            "query_embedding_dimension"
        )

        if dimension is not None:
            embedding_dimensions.append(
                dimension
            )

    except Exception:
        pass

checks["embedding_dimension"] = (
    embedding_dimensions[0]
    if embedding_dimensions
    else None
)

checks[
    "all_embedding_dimensions_384"
] = (
    bool(embedding_dimensions)
    and all(
        value == 384
        for value in embedding_dimensions
    )
)

checks[
    "all_required_retrieval_outputs_present"
] = (
    checks["token_result_count"] == 5
    and checks["semantic_result_count"] == 5
    and checks[
        "sentence_window_result_count"
    ] == 5
)

required_boolean_checks = [
    checks["questions_yaml_exists"],
    checks["corpus_directory_exists"],
    checks["raw_directory_exists"],
    checks["chunk_stats_exists"],
    checks["metrics_md_exists"],
    checks["run_log_exists"],
    checks["sources_md_exists"],
    checks["corpus_manifest_exists"],
    checks["ai_use_exists"],
    checks["run_instructions_exists"],
    checks["report_pdf_exists"],
    checks[
        "all_embedding_dimensions_384"
    ],
    checks[
        "all_required_retrieval_outputs_present"
    ],
]

required_value_checks = [
    checks["question_count"] == 5,
    checks["corpus_pdf_count"] >= 1,
    checks["retrieval_json_count"] == 15,
]

status = (
    "PASS"
    if all(
        required_boolean_checks
        + required_value_checks
    )
    else "FAIL"
)

verification = {
    "homework": "HW3",
    "student": "Timothy Song",
    "sid4": 9981,
    "domain_id": 5,
    "status": status,
    "checks": checks
}

with open(
    OUTPUT_PATH,
    "w",
    encoding="utf-8"
) as f:
    json.dump(
        verification,
        f,
        indent=2
    )

print(
    json.dumps(
        verification,
        indent=2
    )
)

print(
    f"\nSaved verification output to: "
    f"{OUTPUT_PATH}"
)