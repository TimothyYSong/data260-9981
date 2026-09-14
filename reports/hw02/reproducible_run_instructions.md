# Homework 2 Reproducible Run Instructions

## Configuration

- SID4: 9981
- PORT_BASE: 8081
- PREFIX: s9981
- SEED: 9981
- VERIFY_SEED: 269981
- DOMAIN_ID: 5
- Domain: Local restaurant inspections
- Local model: qwen3:8b

## Setup

Clone the repository and enter the repository root:

```bash
git clone https://github.com/TimothyYSong/data260-9981.git
cd data260-9981
```

Install the required Python packages:

```bash
pip install fastapi==0.109.0 "uvicorn[standard]==0.27.0" pydantic==2.12.5 langgraph langchain-ollama
```

Make sure Ollama is installed and the required local model is available:

```bash
ollama pull qwen3:8b
```

## Run the FastAPI Application

From the repository root:

```bash
cd code
python main.py
```

The application should start on:

```text
http://127.0.0.1:8081
```

Open this address in a web browser to use the web application.

Return to the repository root before running the LangGraph scripts:

```bash
cd ..
```

## Run the LangGraph Demo

From the repository root:

```bash
PYTHONPATH=. python code/agents_demo.py
```

Enter a title and content when prompted.

Example:

```text
Title: O2 Valley Inspection
Content: O2 Valley passed the routine inspection with flying colors.
```

The Supervisor, Planner, and Reviewer nodes should execute. The graph should terminate when the review is complete or the turn ceiling is reached.

## Run the Schema Validation Experiment

From the repository root:

```bash
PYTHONPATH=. python code/schema_experiment.py
```

This performs 30 runs using the frozen input in:

```text
reports/hw02/cases/schema_input.json
```

The machine-readable results are written to:

```text
reports/hw02/raw/schema_30_runs.json
```

## Run the Turn Ceiling Comparison Experiment

From the repository root:

```bash
PYTHONPATH=. python code/ceiling_experiment.py
```

This performs 20 runs with a turn ceiling of 2 and 20 runs with a turn ceiling of 10 using the same frozen input.

The machine-readable results are written to:

```text
reports/hw02/raw/ceiling_comparison.json
```

## Run the Adversarial Experiment

From the repository root:

```bash
PYTHONPATH=. python code/adversarial_experiment.py
```

This performs five runs using the adversarial input in:

```text
reports/hw02/cases/adversarial_input.json
```

The machine-readable results are written to:

```text
reports/hw02/raw/adversarial_5_runs.json
```

## Experiment Outputs

The filled-in results tables are available in:

```text
reports/hw02/METRICS.md
```

The run log is available in:

```text
reports/hw02/RUN_LOG.txt
```

The machine-readable experiment results are available in:

```text
reports/hw02/raw/
```

## Verification

The Homework 2 self-check is implemented in:

```text
code/verify.py
```

The self-check verifies objective system behavior, including the FastAPI application and LangGraph workflow, and writes its results to:

```text
reports/hw02/verification.json
```

Run the Homework 2 smoke test from the repository root:

```bash
PYTHONPATH=. python code/verify.py
```

The script starts the FastAPI application, verifies that the backend responds on PORT_BASE, runs the LangGraph workflow, checks objective output constraints, and writes the results to:

```text
reports/hw02/verification.json
```