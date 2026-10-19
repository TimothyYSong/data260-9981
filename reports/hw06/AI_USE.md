# AI_USE.md 

## 1. What did I use an AI assistant for, and what did I do myself?

I used ChatGPT as a development assistant while completing Homework 6. It helped me interpret the assignment requirements, break the work into implementation and verification steps, draft or revise Python code and test scripts, troubleshoot runtime errors, interpret recorded metrics, and prepare explanations for the report and required documentation. This included assistance with the MongoDB-backed REST API, short-term/long-term/episodic memory, token-usage experiments, file-based memory commands, and consolidation testing. I reviewed and applied the suggested changes in my existing repository rather than assuming that AI-generated material was correct.

I was responsible for running the application and experiments on my MacBook Pro, managing the local MongoDB Docker container and Ollama environment, executing API and terminal tests, inspecting the resulting code and outputs, reviewing memory-probe answers, capturing report evidence, and committing project changes to Git. I also checked the results against the assignment requirements and preserved the experimental JSON/JSONL records. ChatGPT helped prepare portions of the written report and documentation; I reviewed them against my recorded results.

The application separately uses a local Ollama **qwen3:8b** model for chat responses, memory summaries, and episodic fact extraction, plus **nomic-embed-text** for embeddings. These are runtime components of the system and are distinct from ChatGPT's role as a development assistant.

## 2. What AI-produced output was wrong or unsuitable, or what did I independently verify?

An AI-assisted memory-consolidation implementation used a **latest-entry-wins** rule when two structured memory facts had the same key but conflicting values. In the required 55-line consolidation experiment, the algorithm retained three deliberately incorrect values: `priority_city: Berkeley`, `inspection_type: complaint`, and `report_format: long paragraphs`. The correct facts from the benchmark conversation were Oakland, routine inspections, and concise bullet points. The automatic output was therefore unsuitable as final durable memory without verification.

## 3. How did I detect the problem or verify the result?

I created a controlled `MEMORY.md` containing at least three duplicated facts and three deliberate contradictions, preserved the original file in Git, and executed the `/compact` consolidation logic. The run reported **52 fact entries before**, **19 after**, **30 duplicate entries removed**, and **three contradictions documented**. I inspected the resulting resolution records and compared the retained values against the known benchmark facts. This revealed that the latest-entry rule had selected all three deliberately incorrect values even though it had recorded the conflicts for manual review.

## 4. What did I change, and why does it work now?

I corrected the three active memory facts to `priority_city: Oakland`, `inspection_type: routine`, and `report_format: concise bullet points`. I kept the original contradiction-resolution records and added explicit correction notes explaining why the previous values were wrong. I preserved the original **55-line** file, the **29-line** automatic consolidation result, and the final **32-line** corrected version as evidence. Git commits `f7c2363` and `0fc7dda` preserve the original and consolidated versions, respectively.

The verified final file contains fewer than 40 lines, has duplicate facts merged, retains an audit trail of the conflicting values, and restores the known correct facts. This works for the tested scenario because errors in automatic contradiction resolution are made visible and corrected rather than silently accepted. I do not assume that a latest-entry rule can resolve every real-world contradiction correctly without independent evidence or review.
