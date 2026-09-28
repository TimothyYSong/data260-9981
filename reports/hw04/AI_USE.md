# AI_USE.md

## 1. What I used an AI assistant for and what I did myself

I used an AI assistant to help interpret the homework requirements, review my implementation, suggest code structure, identify possible mistakes, improve grammar and formatting, and help organize the written report. I also used the AI assistant to review code snippets for syntax and structure, clarify assignment expectations, and help present tables, explanations, and experimental results more clearly.

For Part 4, I used the AI assistant to help design the six-question RAG test set, review the retrieval and context-engineering logic, suggest the k = 1, 3, and 5 context-size sweep, and help summarize the experimental results.

I personally implemented and ran the React frontend, FastAPI backend, MySQL database, authentication and session handling, CRUD endpoints, naive N+1 and fixed endpoints, benchmarking, indexing, RAG pipeline, Chroma vector store, Ollama models, retrieval experiments, and k-sweep. I also executed the commands locally, collected the actual outputs, inspected the results, verified that the system behaved as expected, and prepared the final report.

## 2. One AI-produced output that was wrong or unsuitable, or one thing I independently verified

One AI-assisted suggestion initially used a Q2 wording that was intended to require two retrieved chunks. However, after testing it, I found that the first version could actually be answered from a single retrieved chunk because that chunk contained both standard gradient-descent and momentum information.

## 3. How I detected the problem or verified the result

I detected the issue by running the retrieval pipeline and inspecting the printed top-k chunks before the LLM response. The output showed that the highest-ranked chunk already contained both pieces of information needed to answer the original Q2. Therefore, the question did not satisfy the assignment requirement that Q2 require information from two separate chunks.

## 4. What I changed and why it works now

I rewrote Q2 so that it asks how batch gradient descent computes its gradient using the training data and also asks for the velocity and parameter-update equations used by momentum gradient descent.

After rerunning the retrieval, one chunk contained the batch-gradient-descent information, while a separate chunk contained the momentum equations. The Context-Engineered RAG answer then combined the two pieces of evidence and cited both retrieved sources. Therefore, the revised Q2 now correctly tests multi-chunk retrieval and synthesis.