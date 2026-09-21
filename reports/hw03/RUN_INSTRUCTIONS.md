HW3 Reproducible Run Instructions

These instructions reproduce the HW3 authentication application and retrieval experiment from the repository root.

1. Install Dependencies

Create or activate a Python environment, then install the required packages:

pip install -r requirements.txt

The retrieval portion uses the following packages:

llama-index

llama-index-embeddings-huggingface

sentence-transformers

faiss-cpu

numpy

pandas

pyyaml

pypdf

fonttools

2. Run the FastAPI Application

From the repository root, run:

python3 code/main.py

The application runs at:

http://127.0.0.1:8081

Available routes are:

/
/login
/dashboard
/logout

The default test credentials used for HW3 are:

Username: admin
Password: password

3. Run the HW3 Retrieval Experiment

The graded corpus must already be located in:

reports/hw03/corpus/

The five retrieval questions are stored in:

reports/hw03/questions.yaml

Run the complete retrieval experiment with timestamps using:

echo "RUN START: $(date -Iseconds)" | tee reports/hw03/RUN_LOG.txt
python3 code/hw3_retrieval.py 2>&1 | tee -a reports/hw03/RUN_LOG.txt
echo "RUN END: $(date -Iseconds)" | tee -a reports/hw03/RUN_LOG.txt

The retrieval script performs the following steps:

extracts text from the PDF corpus using pypdf

creates Token, Semantic, and Sentence-window chunks

builds a separate in-memory VectorStoreIndex for each chunking technique

runs all five questions against all three techniques

computes the vector-store similarity score

explicitly embeds each returned chunk

computes cosine similarity between the query and returned chunk embeddings

records chunk length and text preview

records query and document vector shapes

measures retrieval latency

preserves sentence-window context metadata

saves the per-query, per-technique results as JSON

The machine-readable outputs are saved in:

reports/hw03/raw/

The experiment produces 15 retrieval JSON files plus:

reports/hw03/raw/chunk_stats.json

4. Recompute the Summary Metrics

After the retrieval experiment completes, run:

python3 code/recompute_hw3_metrics.py

This script reads the machine-readable files in:

reports/hw03/raw/

and recomputes the retrieval comparison metrics.

The results are written to:

reports/hw03/METRICS.md

The summary includes:

total number of chunks

average chunk length

mean top-1 cosine similarity

mean@5 cosine similarity

Recall@5

mean retrieval latency

5. Verify Generated Outputs

To list the generated raw files:

ls reports/hw03/raw

To count them:

ls reports/hw03/raw | wc -l

The expected count is:

16

This consists of:

15 per-query, per-technique retrieval JSON files

1 chunk_stats.json file

The full timestamped console output from the graded run is stored in:

reports/hw03/RUN_LOG.txt

The recomputed summary metrics are stored in:

reports/hw03/METRICS.md

6. Supporting HW3 Files

The HW3 report directory should contain:

reports/hw03/RUN_LOG.txt
reports/hw03/raw/
reports/hw03/METRICS.md
reports/hw03/AI_USE.md
reports/hw03/report.pdf
reports/hw03/RUN_INSTRUCTIONS.md
reports/hw03/verification.json
reports/hw03/SOURCES.md
reports/hw03/CORPUS_MANIFEST.json
reports/hw03/questions.yaml

7. Corpus Documentation

The graded corpus is stored in:

reports/hw03/corpus/

Source URLs and access dates are documented in:

reports/hw03/SOURCES.md

Local filenames, byte sizes, and SHA-256 hashes are documented in:

reports/hw03/CORPUS_MANIFEST.json

8. Embedding Model

The retrieval experiment uses the public Hugging Face sentence embedding model:

sentence-transformers/all-MiniLM-L6-v2

The expected embedding dimension is:

384

9. Reproducibility Notes

All commands above should be run from the repository root.

The first run may download the Hugging Face embedding model if it is not already cached locally.

The retrieval results reported in the HW3 report were generated from the local FDA corpus in reports/hw03/corpus/ using the five questions stored in reports/hw03/questions.yaml.