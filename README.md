# RemiChain

**Live application:** [remichain.vercel.app](https://remichain.vercel.app)

[![Python](https://img.shields.io/badge/python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/) [![Flask](https://img.shields.io/badge/flask-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/) [![PostgreSQL](https://img.shields.io/badge/postgresql-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/) [![Vercel](https://img.shields.io/badge/vercel-000000?style=for-the-badge&logo=vercel&logoColor=white)](https://vercel.com/)

RemiChain matches surplus medical supplies with facility requests before the supplies expire in storage.

## Overview

A facility signs in, lists what it has spare and what it needs. The matching service scores donation-request pairs on urgency, distance, quantity fit and how soon the stock expires, then proposes the best pairs for either side to accept, decline or complete. Each facility sees only its own stock, requests and matches; the landing page shows the network totals.

A scheduled sweep runs once a day: it flags stock that has passed its expiry date and runs a matching pass, so new requests meet existing surplus without anyone pressing a button.

## Highlights

- Register a hospital, clinic, pharmacy or NGO with coordinates, then sign in under that facility.
- List surplus donations and post supply requests; both are scoped to the signed-in facility.
- Rank donation-request pairs using four weighted factors, with a score shown on each proposed match.
- Accept, decline or complete a match. Declining releases the reserved stock and reopens the request; partial fulfilment keeps the remainder available.
- Match against a normalised item catalogue, so "surgical gloves" and "gloves, surgical" resolve to the same item.
- Expired stock is flagged by the daily sweep and listed on the donor's dashboard instead of silently disappearing.
- Browse a dashboard and read donations, requests and matches through a documented JSON API at `/api`.
- Guard the write paths with CSRF tokens, per-facility rate limits and length caps on free-text fields.

## Technology

Python, Flask, Flask-SQLAlchemy, SQLite locally or PostgreSQL (Supabase) when deployed, pytest, and vanilla JavaScript and CSS. Hosted as a Vercel Function using the Flask preset, with the scheduled sweep registered as a Vercel cron job.

## Repository contents

- `server.py` — the WSGI entrypoint Vercel's Flask preset loads.
- `app/` — application factory, auth, CSRF and rate-limit helpers, models, routes and the matching service.
- `app/services/matching.py` — scoring, candidate selection and match creation.
- `app/models/catalog.py` — the normalised item catalogue used for matching.
- `templates/` and `public/` — Jinja templates, static assets, icons, manifest, robots and sitemap.
- `tests/` — pytest checks for the matching rules.
- `vercel.json` — the function bundle, included files and the daily cron schedule.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

Open `http://localhost:5000`. Without a database URL the app creates `remichain.db` in the repository root and seeds a demo facility.

Run the tests with:

```bash
pytest tests/
```

## Deploy on Vercel

The repository is a Vercel project already: `server.py` exports the Flask `app`, `public/` holds the assets the CDN serves, and `vercel.json` bundles `templates/` with the function.

```bash
vercel link
vercel deploy --prod
```

A push to `main` deploys as well, because the project is connected to GitHub.

### Database (Supabase)

Vercel's filesystem is read-only apart from a per-instance `/tmp`, so the deployed app runs on hosted Postgres. Connection details come from the environment, so no code changes are needed to point it at a different database:

| Variable | Used by |
| --- | --- |
| `DATABASE_URL` | Supabase, Neon, generic Postgres |
| `POSTGRES_URL` / `POSTGRES_PRISMA_URL` | Vercel storage integrations |

RemiChain keeps its tables in a dedicated `remichain` schema and connects as the `remichain_app` role, so it never touches other tables in that project. Both were created with:

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

Tables and a demo facility are created on first boot. Set `SECRET_KEY` (or `FLASK_SECRET_KEY`) too, so session cookies stay valid across function instances.

### Scheduled sweep

`vercel.json` registers `/api/cron/maintenance` for 04:00 UTC daily. The endpoint requires a bearer token matching `CRON_SECRET` and refuses every request without it, so it is not a public trigger. It expires stock whose date has passed and runs a matching pass across all facilities.

Without a database the app falls back to a throwaway SQLite file inside the function instance: fine locally, not something to rely on in production.

## Notes and limitations

Facilities self-register and are marked unverified; there is no email ownership check yet. Anyone who can sign in as a facility can act on that facility's matches, so per-person roles within an organisation are still missing. Matching is a scoring heuristic, not a validated allocation model, and the distance factor uses straight-line distance rather than a route. Put email verification and per-user roles in front of it before using it with real stock across organisations.

## License

MIT — see `LICENSE`.
