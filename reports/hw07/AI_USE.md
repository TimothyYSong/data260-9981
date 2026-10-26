# DATA 260 — Homework 7: AI_USE

## 1. What did the AI assistant do, and what did I do myself?

I used ChatGPT as a development, debugging, testing, and writing assistant while extending my existing `data260-9981` repository for Homework 7. It helped me plan implementation steps, understand the assignment requirements, propose and revise Python/FastAPI code, troubleshoot errors, write and interpret test commands, and organize the required evidence files. This assistance covered JWT authentication and role-based access controls (Part 1), tool-call reliability and one-shot repair (Part 2), bounded Reflexion and its verifier (Part 3), bike-share scenario analysis and pricing comparisons (Part 4), prompt-injection tests and defenses (Part 5), and sandboxed file tools and the command safety gate (Part 6).

ChatGPT also helped draft and edit report wording, table descriptions, metric explanations, limitations, and documentation. I used it to improve Markdown/LaTeX formatting, syntax, clarity, grammar, and consistency across the PDF report, `RUN_LOG.txt`, `METRICS.md`, and other deliverables.

I was responsible for running the commands in my local environment, reviewing and integrating code in the existing repository, supplying actual outputs and errors, testing behavior, checking evidence against the assignment, and deciding what changes to keep. The locally executed `qwen3:8b` model was the agent being evaluated; ChatGPT was a separate assistant used during development and documentation.

## 2. What AI-generated output was wrong, incomplete, or unsuitable?

Not every AI suggestion worked as written. During final checks, a suggested Uvicorn startup command run from `code/` failed to locate `src.model_client` (`ModuleNotFoundError: No module named 'src'`). A subsequent command run from the repository root failed to locate `main`. Using `PYTHONPATH=.:code` resolved the import path, although that invocation then found port `8081` already occupied by another Python process.

The evaluation itself also exposed limitations that could not be described as successes simply because an AI-generated answer sounded plausible. In the Part 5 recommendation-override test, the saved prompt-only defense trial still followed the injected instruction; the combined application-level verification prevented that incorrect recommendation from becoming the final result. In Part 3, Reflexion did not improve the observed task-success rate over the original loop in the saved comparison runs, while consuming more tokens and time. Those results needed accurate reporting rather than an unsupported claim that the more elaborate method was better.

## 3. How did I detect and verify the problems?

I checked suggestions against actual terminal output, FastAPI responses, source code, and saved machine-readable experiment artifacts rather than accepting AI explanations on their own. For the startup issue, I used the Python traceback to identify the missing import path, confirmed the API's `/auth/login` and `/auth/me` routes through its OpenAPI endpoint, and checked which process was listening on port `8081`. The negative authentication checks returned HTTP `401` for a missing bearer token and invalid credentials.

For the experimental results, I compared the report and metrics against the corresponding CSV/JSON/JSONL files under `reports/hw07/raw/`. I inspected the before/after attack traces, distinguished model behavior from tool-boundary enforcement, and checked recorded safety-gate results rather than inferring outcomes. In particular, the Part 6 evidence recorded five expected-safe commands allowed, five expected-unsafe commands blocked, and zero false allows. I retained failure cases and limitations in the documentation instead of rewriting them as successes.

## 4. What did I change as a result, and why?

I corrected the startup invocation for the repository layout without changing application code solely to work around an environment-path error. I kept the actual test results and saved evidence, including cases in which the model or a proposed defense did not behave as intended. For the recommendation-override scenario, I distinguished the vulnerable raw model output from the final recommendation protected by deterministic application checks. For the SQL-injection scenario, I distinguished direct tool-boundary tests from model-generated attempts.

I revised report wording and metrics so that measured observations, derived estimates, and unverified claims were not conflated. For example, I described bike-share costs as estimates based on saved assumptions rather than current provider charges, disclosed that Part 1's appended tests covered only two negative cases, and reported that Reflexion used more resources without a measured success-rate gain. I also improved headings, table structure, formatting, syntax, and grammar to make the submission clearer. The final decisions were based on observed behavior, assignment requirements, and reproducible evidence—not solely on AI-generated text.
