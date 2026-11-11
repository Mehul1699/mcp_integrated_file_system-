# Resume Matching Agent

An AI-assisted resume screening and candidate matching system built with Python, LangGraph, ChromaDB, and the Model Context Protocol (MCP).

## 1. Project Overview

The Resume Matching Agent helps recruiters identify and evaluate candidates against job requirements.

It retrieves resume information, compares candidate skills with job requirements, performs deeper screening, and generates evidence-based recommendations. Recruiters can review the recommendations and provide feedback before the workflow is completed.

## 2. Key Features

- Resume ingestion through an MCP filesystem client.
- Resume text processing and chunking.
- Local vector generation using Python feature hashing.
- Persistent vector storage and retrieval with ChromaDB.
- Job requirement and candidate skill matching.
- Candidate ranking and eligibility assessment.
- AI-assisted deep screening using Groq.
- Final candidate recommendations with supporting reasoning.
- Recruiter feedback and approval through LangGraph.
- JSON export of final matching results.

## 3. Technologies Used

| Technology | Purpose |
|---|---|
| Python | Main programming language |
| LangGraph | Workflow orchestration |
| ChromaDB | Vector database |
| MCP | Filesystem integration |
| Groq API | AI-powered analysis |
| Requests | API communication |
| Python feature hashing | Local embedding generation |

## 4. Project Structure

```text
mcp_integrated_file_system-/
│
├── matching_agent.py
├── resume_rag.py
├── job_matcher.py
├── mcp_client.py
├── local_embeddings.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

Generated folders and files, such as the virtual environment, ChromaDB database, and matching results, are not included in version control.

## 5. Installation and Setup

### Prerequisites

- Python 3.12
- A Groq API key
- A configured MCP filesystem server
- Access to the resume files that will be indexed

### Step 1: Clone the repository

```bash
git clone YOUR_REPOSITORY_URL
cd YOUR_PROJECT_FOLDER
```

### Step 2: Create a virtual environment

```bash
python -m venv .venv
```

Activate it on Windows:

```bash
.venv\Scripts\activate
```

### Step 3: Install dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure environment variables

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key
CHAT_MODEL=openai/gpt-oss-120b
```

Never commit your actual `.env` file or API key.

### Step 5: Configure the MCP filesystem server

Configure the filesystem server and resume directory using the existing MCP client configuration in `mcp_client.py`.

Ensure the server can access the intended resume directory before indexing.

## 6. Running the Application

### Step 1: Index resumes

```bash
python resume_rag.py
```

This retrieves resumes through MCP, processes the documents, generates local feature-hashing vectors, and stores them in ChromaDB.

### Step 2: Start the matching agent

```bash
python matching_agent.py
```

Enter a job description when prompted.

Example:

```text
Find a Python developer with experience in Machine Learning.
```

### Step 3: Review candidate recommendations

The application retrieves and evaluates candidates, performs deep screening on a limited number of shortlisted candidates, and generates recommendations.

### Step 4: Provide recruiter feedback

Review the candidate recommendations and enter recruiter feedback when requested.

### Step 5: View saved results

After the workflow completes, the application saves its results to:

```text
job_match_results.json
```

## 7. Candidate Evaluation

The system uses candidate evidence and job requirements to support three recommendation categories:

- **Recommend for interview:** Essential requirements are supported by available evidence.
- **Further review required:** Essential skills or qualifications require additional verification.
- **Do not recommend at this stage:** Mandatory eligibility requirements are not satisfied.

Recommendations are intended to support recruiter decisions, not replace human judgment.

## 8. Important Implementation Notes and Limitations

### Local feature-hashing embeddings

This project uses a lightweight, local Python feature-hashing implementation for vector generation.

It avoids external embedding API costs and dependencies such as SentenceTransformers and SciPy.

However, feature hashing is not a transformer-based semantic embedding model. Its semantic retrieval quality may be lower than dedicated embedding models.

### Groq API rate limits

The Groq API may enforce token-per-minute limits. The application includes retry handling, and deep screening is currently limited to three candidates per run.

### Resume privacy

Resume documents and generated candidate information may contain personal information. Keep these files private and do not commit them to a public repository.

## 9. Future Improvements

- Improve semantic retrieval with a dedicated embedding model.
- Optimize token usage and API request handling.
- Support configurable deep-screening limits.
- Improve candidate skill normalization and evidence extraction.
- Add a recruiter-facing user interface.
- Expand evaluation and testing.

## 10. Disclaimer

This project is an AI-assisted recruitment decision-support tool. Its outputs may contain errors or incomplete interpretations of resume information. All hiring decisions should involve human review and independent verification of candidate qualifications.