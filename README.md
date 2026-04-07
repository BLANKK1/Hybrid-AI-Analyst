# Hybrid-AI-Analyst
## What It Does
1. Takes a **natural language business question**
2. Determines whether to use:
    - SQL (structured data)
    - RAG (unstructured data)
    - Or a combination of both
3. Generates and executes SQL queries when needed
4. Retrieves relevant documents when needed
5. Combines results into a **clear, accurate, and actionable insight**
6. Handles **follow-up questions with context**
7. Asks **clarifying questions when the input is ambiguous**
## Setup
1. Clone the repo
2. pip install -r requirements.txt
3. Set your Environment Vaiable for Gemini API key inside the folder
4. uvicorn server:app --port 8000(For Running)
