AI_USE

1. What did you use an AI assistant for, and what did you do yourself?
I used an AI assistant as a support tool throughout the assignment. It helped me interpret the homework requirements, debug and test parts of the retrieval pipeline, identify and fix implementation issues, and improve syntax, formatting, grammar, wording, and organization in my code and report. It also helped draft and format supporting Markdown and text files based on my implementation, outputs, and results. I remained responsible for the overall implementation and decisions: I set up the repository, selected and downloaded the corpus, ran and tested the code, verified the outputs and retrieval results, created the screenshots, and assembled the final report. 

2. Give one AI-produced output that was wrong or unsuitable, or one result you independently verified.
One initial approach for loading the PDF corpus was unsuitable because it resulted in PDF binary and internal file syntax being treated as document content instead of clean extracted text.

3. How did you detect the problem or verify the result?
I detected the issue because the output contained strings such as %PDF-1.6 and other unreadable PDF-internal content instead of normal English text from the FDA documents. The initial ingestion also produced only a few document objects, which was inconsistent with a corpus containing more than one thousand PDF pages.

4. What did you change, and why does it work now?
I changed the ingestion process to use pypdf.PdfReader and explicitly extract text from each page before creating LlamaIndex Document objects. After this change, the pipeline loaded 1,023 document/page objects and produced readable FDA text for chunking and retrieval. This works better because the retrieval system now embeds actual document text instead of PDF file structure or binary content.