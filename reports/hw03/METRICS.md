# HW3 Retrieval Metrics

All metrics below were recomputed from the machine-readable JSON files in `reports/hw03/raw/`.

| Technique | Chunks | Avg chunk length (characters) | Top-1 cosine | Mean@k cosine | Recall@k | Mean retrieval latency (ms) |
|---|---:|---:|---:|---:|---:|---:|
| Token | 3220 | 852.20 | 0.7529 | 0.7201 | 1.00 | 27.53 |
| Semantic | 2253 | 1016.20 | 0.7469 | 0.7141 | 1.00 | 20.15 |
| Sentence Window | 17016 | 134.55 | 0.8224 | 0.7695 | 1.00 | 128.16 |

## Metric Definitions

- **Chunks:** Total number of chunks produced by the technique.
- **Avg chunk length:** Mean number of characters per chunk.
- **Top-1 cosine:** Mean across the five questions of the highest cosine similarity among each question's top-k retrieved chunks.
- **Mean@k cosine:** Mean cosine similarity across all retrieved top-k chunks for all five questions.
- **Recall@k:** Fraction of questions for which the expected source file appeared anywhere in the top-k retrieved results.
- **Mean retrieval latency:** Mean similarity-search latency across the five questions.
