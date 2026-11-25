# RemiChain

> A Flask application that helps healthcare facilities match surplus medical supplies with facility requests before stock expires.

**Live application:** [remichain.vercel.app](https://remichain.vercel.app/)

[![Python](https://img.shields.io/badge/python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/) [![Flask](https://img.shields.io/badge/flask-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/) [![SQLAlchemy](https://img.shields.io/badge/sqlalchemy-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/) [![PostgreSQL](https://img.shields.io/badge/postgresql-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/) [![Vercel](https://img.shields.io/badge/vercel-000000?style=for-the-badge&logo=vercel&logoColor=white)](https://vercel.com/)

## Overview

Facilities can register, list surplus donations, and post supply requests. RemiChain ranks potential donation-request pairs using urgency, expiry timing, proximity, and quantity fit. Facilities can review proposed matches and accept, decline, or complete them; declining a match releases reserved stock, while partial fulfilment leaves the remainder available.

The deployed application uses a Flask serverless function on Vercel with PostgreSQL storage. Local development can use SQLite.

## Highlights

- Facility registration and facility-scoped dashboards.
- Donation listings and supply requests.
- Weighted matching based on urgency, expiry, proximity, and quantity.
- Normalised item names so common naming variations can match.
- Match acceptance, decline, completion, and partial fulfilment.
- A daily maintenance endpoint that flags expired stock and runs a matching pass.
- JSON API routes for application data.

## Implementation

The application uses Flask, Flask-SQLAlchemy, and Jinja templates. The matching service is in `app/services/matching.py`; facility, donation, request, and match records are represented by SQLAlchemy models. Session cookies identify the signed-in facility, and write routes use CSRF protection, per-facility rate limits, and input length limits.

On Vercel, persistent data is stored in PostgreSQL. The daily maintenance task is configured through `vercel.json` and calls the cron endpoint using `CRON_SECRET`. A local SQLite database is used outside Vercel when no PostgreSQL connection is configured.

## Repository structure

- `server.py` — WSGI entry point used by Vercel and Flask's local development server.
- `app/` — application factory, authentication, models, routes, security helpers, and matching service.
- `config.py` — database selection, session settings, and matching weights.
- `templates/` — Jinja page templates.
- `public/` — static assets.
- `tests/` — automated tests.
- `requirements.txt` and `vercel.json` — Python dependencies and deployment/cron configuration.

## Status and limitations

Facilities self-register and are marked unverified; the current app does not yet verify email ownership or provide individual user roles within an organisation. Matching is a weighted heuristic, not a clinically validated or optimised allocation system, and proximity is based on straight-line distance rather than road routes. The database connection is read from the environment variables in `config.py`, falling back to SQLite, which suits local development but not persistent storage on Vercel; a production deployment needs a hosted PostgreSQL string to keep data durable.

## License

MIT. See [LICENSE](LICENSE).
