# DocuMind — Django Document Intelligence

A small document Q&A application that indexes uploaded PDF and TXT files with local sentence-transformer embeddings, retrieves the most relevant passages, and asks Gemini to answer using those passages only. Every answer includes its supporting source excerpts. If retrieved passages are not relevant enough, the application says it could not find the information instead of guessing.

## Requirements

- Python 3.10+
- A Gemini API key for generated answers ([Google AI Studio](https://aistudio.google.com/app/apikey))

## Setup (Windows PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `GEMINI_API_KEY` in `.env`. Django loads the `.env` file automatically:

```powershell
$env:GEMINI_API_KEY = ""
$env:DJANGO_SECRET_KEY = "replace-with-a-long-random-secret"
python manage.py migrate
python manage.py runserver
```

Open <http://127.0.0.1:8000/>. The embedding model is downloaded on first use and runs locally. Without a Gemini API key, retrieval still runs and the app reports that generated answers require configuration while showing the matching source passages.

By default, SQLite stores its database at `db.sqlite3` in the project folder. If that folder is read-only or cloud-synced, set `DJANGO_DATABASE_PATH` to a writable local file path before starting Django.

## Deploy to Render

1. Push this project to a GitHub repository you control.
2. In Render, choose **New → Blueprint**, connect that repository, and confirm the settings in `render.yaml`.
3. Enter your Gemini API key when Render asks for `GEMINI_API_KEY`. Keep it private; do not commit it to GitHub.
4. Deploy. Render will provide the public `https://...onrender.com` address when the build and startup finish.

The Blueprint uses a paid Starter web service and a persistent disk so uploaded document indexes survive restarts. Review Render's current pricing before confirming. Embedding model files and the SQLite database are stored on that disk. The first document upload downloads the embedding model, so allow extra time for initial indexing.

## How retrieval works

1. PDF pages are extracted with `pypdf`; TXT files are decoded as UTF-8.
2. Text is split into overlapping 1,000-character passages.
3. `sentence-transformers/all-MiniLM-L6-v2` creates normalized vector embeddings.
4. Each question is embedded and passages are ranked by cosine similarity.
5. The top five passages are sent to Gemini with instructions to use only that evidence.
6. Low-similarity matches are rejected; answers show the retrieved passages, filename, and PDF page when available.

Documents and passage embeddings are stored in a local SQLite database. The upload limit is 10 MB per file.
