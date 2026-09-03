## Deploy on Render

1. Push this repository to GitHub.
2. In Render, choose **New > Blueprint** and select the repository. Render will use `render.yaml`.
3. Set `GEMINI_API_KEY` in the Render environment variables. Use a newly generated key rather than the key shared during development.
4. Set `DATABASE_URL` to a Render PostgreSQL connection string. Leave it unset only for a temporary demo using SQLite.
5. Deploy. Render will run `gunicorn --bind 0.0.0.0:$PORT run:app`.

SQLite, uploaded PDFs, and the local Chroma directory are stored on the web service filesystem. They can be lost when Render redeploys or restarts the service. For persistent production RAG data, use a Render persistent disk or move uploads and vector storage to managed storage.
