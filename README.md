# Content Dreamer.ai

Monorepo with Next.js frontend (`client/`) and Flask backend (`server/`).

## Quick start

1. Backend (in `server/`):
   - Ensure `.env` contains `DATABASE_URI`, `OPENAI_API_KEY`, and Redis is running.
   - Run Flask API
   - Run RQ worker using `./worker.sh`

2. Frontend (in `client/`):
   - Set `NEXT_PUBLIC_API_URL=http://localhost:5000`
   - Run next dev server

The landing page provides a Try It form that creates a guest report and redirects to the report page which polls status and shows partial suggestions until login/subscription.
