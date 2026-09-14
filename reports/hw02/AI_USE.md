# AI Use

## 1. What did you use an AI assistant for, and what did you do yourself?

I used ChatGPT as an assistant for when I got stuck or needed clarification. I used it to explain assignment requirements and concepts that I was unclear about, help troubleshoot syntax and environment issues, suggest formatting and styling improvements, and review grammar and wording. I also used it to help organize documentation such as METRICS.md, RUN_LOG.txt, AI_USE.md, and the reproducible run instructions based on the results that I generated.

I completed and tested the assignment myself. I made the implementation decisions, ran the FastAPI and LangGraph programs locally, performed the experiments, collected the outputs, tested the validation and correction loop, created the adversarial input, and verified the reported results. The AI assistant was used for guidance and review rather than as a replacement for running or verifying the work.

## 2. What is one AI-produced output that was wrong or unsuitable, or one thing you independently verified?

One thing I independently verified was how to run the LangGraph program in my local Python environment. During development, one Python interpreter could not find the LangGraph package even though it was installed in the environment I intended to use.

## 3. How did you detect the problem or verify the result?

I detected the problem by running the program myself and observing the import error. I compared the Python environments and then ran the program using the environment where the required packages were installed. I verified the solution by running `PYTHONPATH=. python code/agents_demo.py` and confirming that the Supervisor, Planner, and Reviewer nodes executed and the graph terminated successfully.

I also independently verified the experimental results by running the schema-validation, ceiling-comparison, and adversarial experiment scripts locally and saving their outputs as machine-readable JSON files.

## 4. What did you change, and why does it work now?

I changed the way I invoked the program so that it used the correct Python environment and set `PYTHONPATH=.` so that the project modules could be imported correctly from the repository root. This works because Python can now locate both the installed dependencies and the local `src` package used by the LangGraph program.

After making the change, I reran the program and experiments and confirmed that they completed successfully. The resulting console outputs and JSON files were then used for the metrics and report rather than relying on unverified AI-generated results.