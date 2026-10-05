# AI USE

## 1. What I used an AI assistant for and what I did myself

I used an AI assistant mainly for implementation guidance, debugging support, test planning, and report organization/grammar. The assistant helped me break the homework into smaller steps, suggested code structure for the MCP servers, retry helper, `execute_tool`, agent loop, offline tests, metrics collection, repository artifacts, and other sections I was stuck on. It also helped me identify which relevant screenshots and outputs were needed for the report. In addition, it helped me generate repository files based on work I had already completed and verified.

I performed the actual implementation, ran the code locally, tested the FastAPI application, Redux client, MCP Inspector tools, failure-injection experiments, offline test suite, and Ollama agent scenarios, and verified the resulting outputs. I also created the final report, selected the screenshots, and organized the repository files.

## 2. One AI-produced output that was wrong or unsuitable, or one thing I independently verified

One thing I independently verified was the dependency setup for the MCP servers. The initial project requirements did not include all packages needed by the new MCP implementation. In particular, I verified that `httpx` and the MCP CLI dependency were required for the server code and development workflow.

## 3. How I detected the problem or verified the result

I detected the issue by running the MCP server and checking the installed package environment. I also verified the MCP version with `pip show mcp` and confirmed that the FastMCP implementation worked with MCP 1.30.0. I then ran the server through MCP Inspector and successfully executed the meal and domain tools, which confirmed that the dependency configuration was correct.

## 4. What I changed and why it works now

I updated `requirements.txt` to include:

- `httpx`
- `mcp[cli]<2`

This matches the implementation because the MCP servers use `httpx` for HTTP requests and FastMCP from MCP 1.x. After making the change, the servers started correctly in MCP Inspector and the required tools executed successfully. This resolved the missing dependency issue and made the environment reproducible for the submitted repository.