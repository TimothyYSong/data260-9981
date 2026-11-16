# AI Use Disclosure — Homework 9

### 1. What did you use an AI assistant for, and what did you do yourself?

I used ChatGPT (OpenAI) to help interpret assignment requirements, develop implementation plans, generate and revise Python code, troubleshoot errors, design test cases, analyze experimental results, and prepare report documentation.

AI assistance supported the Redis view counter, semantic response cache, threshold evaluation, stale-cache invalidation, and two-agent system. For Part 4, ChatGPT helped develop the Answering Agent, Evaluator Agent, revision workflow, lesson memory, validation procedure, and four-variant comparison.

I executed the code in my local environment, configured and tested the required services, ran experiments, inspected the outputs, verified results against the assignment requirements, and assembled the report. The local `qwen3:8b` model was used for agent inference and evaluation.

### 2. Describe one AI-produced output that was wrong or unsuitable, or something you independently verified.

An initial AI-assisted implementation of the Part 4 Evaluator Agent was insufficient because it checked whether expected values appeared in an answer without adequately considering contradictory or unsupported statements.

For example, it incorrectly returned PASS for an answer claiming that inspection 10016 had both 0 and 3 violations. It also returned PASS when an answer included an unsupported claim that the restaurant was permanently closed.

### 3. How did you detect the problem or verify the result?

I ran a six-case evaluator robustness test covering correct answers, incorrect violation counts, contradictory statements, unsupported facts, incomplete answers, and incorrect inspection IDs.

The initial implementation passed only four of six cases. The independent Qwen3 evaluation correctly identified the two problematic answers as requiring revision, but the Python decision logic ignored those assessments and returned PASS.

Comparing the deterministic results with the LLM assessments revealed the inconsistency.

### 4. What did you change, and why does it work now?

I revised the Evaluator Agent to combine deterministic ground-truth verification with independent LLM evaluation. An answer now receives PASS only when both checks approve it. If either check rejects the answer, the system returns REVISE with corrective feedback.

After the modification, all six robustness tests passed. I also reran the answer-revision workflow, confirming that an incorrect initial answer was corrected through evaluator feedback in two attempts and that a correct answer passed on the first attempt.

This modification addressed the identified weaknesses while preserving the required revision and stopping behavior.