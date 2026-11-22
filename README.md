# RemiChain

[![Python](https://img.shields.io/badge/python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/) [![Flask](https://img.shields.io/badge/flask-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/) [![Vercel](https://img.shields.io/badge/vercel-000000?style=for-the-badge&logo=vercel&logoColor=white)](https://vercel.com/)

RemiChain matches surplus medical supplies with facility requests before supplies expire.

## Overview

Facilities can list surplus donations and submit requests. The matching service scores donation-request pairs using urgency, proximity, quantity fit, and expiry proximity, then creates proposed matches.

## Highlights

- Create and manage facility donations and supply requests.
- Rank potential matches using four scoring factors.
- Track proposed, reserved, partially fulfilled, and fulfilled states.
- View a dashboard and query donations, requests, and matches through a JSON API.
- Avoid duplicate proposals when no new data has been added.

## Technology

Python, Flask, Flask-SQLAlchemy, SQLite (local) or Postgres (deployed), and pytest. Deployed as a Vercel Function using the Flask preset.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

Open `http://localhost:5000`. Locally the app stores data in `remichain.db`.

Run the tests with:

```bash
pytest tests/
```

## Deploy on Vercel

The repository is a Vercel project already: `server.py` exports the Flask `app`
that Vercel's Flask preset loads, `public/` holds the static assets served by
the CDN, and `vercel.json` bundles `templates/` with the function.

```bash
vercel link
vercel deploy --prod
```

Any push to `main` deploys as well, because the project is connected to GitHub.

### Database (Supabase)

Vercel's filesystem is read-only apart from a per-instance `/tmp`, so the app
runs on hosted Postgres. Connection details come from the environment — no code
changes are needed to point it at a different database:

| Variable | Used by |
| --- | --- |
| `DATABASE_URL` | Supabase, Neon, generic Postgres |
| `POSTGRES_URL` / `POSTGRES_PRISMA_URL` | Vercel storage integrations |

RemiChain keeps its tables in a dedicated `remichain` schema and connects as the
`remichain_app` role, so it never touches the other tables in that project. Both
were created with:

```sql
CREATE ROLE remichain_app LOGIN PASSWORD '...';
CREATE SCHEMA remichain;
GRANT USAGE, CREATE ON SCHEMA remichain TO remichain_app;
ALTER ROLE remichain_app SET search_path = remichain, public;
```

The pooler connection string (session mode, port 5432) is what serverless needs:

```
postgresql://remichain_app.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres?sslmode=require
```

Tables and demo facilities are created on first boot. `SECRET_KEY` (or
`FLASK_SECRET_KEY`) should also be set so session cookies stay valid across
function instances.

Without a database the app falls back to a throwaway SQLite file inside the
function instance: fine locally, not something to rely on in production.

## Notes and limitations

This is a prototype. The current matching flow creates proposed matches; an
accept/decline workflow is not implemented.

## License

MIT — see `LICENSE`.
