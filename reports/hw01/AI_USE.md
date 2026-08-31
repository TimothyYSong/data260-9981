(1) what you used an AI assistant for and what you did yourself
I used an AI assistant to help explain parts of the assignment requirements I did not understand, assist with coding, debugging, and troubleshooting, check syntax, styling, and formatting, help with Docker, Ollama, and AWS setup and configuration, and provide help when I got stuck. I also used an AI assistant for help with Git/GitHub and summarized the assignment process for AI to help me create the reproducible run instructions. I implemented and ran the code myself, tested and collected the results, took the screenshots, and created the report.

(2) one AI-produced output that was wrong/unsuitable, or one thing you independently verified
An AI assistant helped me with an import "from code.agents_demo import pipeline", but I had edited my repository and the AI assistant was not up to date. 

(3) how you detected the problem or verified the result
I received the error "ModuleNotFoundError: No module named 'code.agents_demo'; 'code' is not a package".

(4) what you changed and why it works now
I realized that I had relocated my agents_demo.py file earlier, so I changed the import to from agents_demo import pipeline to fix the error.