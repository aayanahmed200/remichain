# RemiChain

**Live application:** [remichain.vercel.app](https://remichain.vercel.app)

[![Python](https://img.shields.io/badge/python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/) [![Flask](https://img.shields.io/badge/flask-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/) [![PostgreSQL](https://img.shields.io/badge/postgresql-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/) [![Vercel](https://img.shields.io/badge/vercel-000000?style=for-the-badge&logo=vercel&logoColor=white)](https://vercel.com/)

RemiChain matches surplus medical supplies with facility requests before the supplies expire in storage.

## Overview

A facility signs in, lists what it has spare and what it needs. The matching service scores donation-request pairs on urgency, distance, quantity fit and how soon the stock expires, then proposes the best pairs for either side to accept, decline or complete. Each facility sees only its own stock, requests and matches; the landing page shows the network totals.

A scheduled sweep runs once a day: it flags stock that has passed its expiry date and runs a matching pass, so new requests meet existing surplus without anyone pressing a button.

## How it was made

A Flask application with SQLAlchemy models for facilities, donations, requests, matches and rate limits, rendered through Jinja templates and hand-written CSS. Sign-in is a session cookie scoped to one facility, and the write paths are guarded with CSRF tokens, per-facility rate limits and length caps on free-text fields.

Matching lives in `app/services/matching.py`. It normalises free-text item names against a small catalogue, so "surgical gloves" and "gloves, surgical" resolve to the same item, then ranks candidate pairs on four weighted factors and records the score on each proposed match. Declining a match releases the reserved stock and reopens the request; partial fulfilment keeps the remainder available.

Vercel runs the app as a Python function loaded through `server.py`, with `public/` served from the CDN. The function filesystem is read-only apart from a per-instance `/tmp`, so the deployed app runs on hosted Postgres in its own `remichain` schema and connecting role, while locally it falls back to a SQLite file. The daily sweep is a Vercel cron job calling `/api/cron/maintenance`, which requires a bearer token matching `CRON_SECRET`.

## Highlights

- Register a hospital, clinic, pharmacy or NGO with coordinates, then sign in under that facility.
- List surplus donations and post supply requests; both are scoped to the signed-in facility.
- Rank donation-request pairs using four weighted factors, with a score shown on each proposed match.
- Accept, decline or complete a match. Declining releases the reserved stock and reopens the request; partial fulfilment keeps the remainder available.
- Match against a normalised item catalogue, so "surgical gloves" and "gloves, surgical" resolve to the same item.
- Expired stock is flagged by the daily sweep and listed on the donor's dashboard instead of silently disappearing.
- Browse a dashboard and read donations, requests and matches through a documented JSON API at `/api`.
- Guard the write paths with CSRF tokens, per-facility rate limits and length caps on free-text fields.

## Repository contents

- `server.py` — the WSGI entrypoint Vercel's Flask preset loads.
- `app/` — application factory, auth, CSRF and rate-limit helpers, models, routes and the matching service.
- `app/services/matching.py` — scoring, candidate selection and match creation.
- `app/models/catalog.py` — the normalised item catalogue used for matching.
- `templates/` and `public/` — Jinja templates, static assets, icons, manifest, robots and sitemap.
- `tests/` — pytest checks for the matching rules.
- `vercel.json` — the function bundle, included files and the daily cron schedule.

## Notes and limitations

Facilities self-register and are marked unverified; there is no email ownership check yet. Anyone who can sign in as a facility can act on that facility's matches, so per-person roles within an organisation are still missing. Matching is a scoring heuristic, not a validated allocation model, and the distance factor uses straight-line distance rather than a route. Without a database the app falls back to a throwaway SQLite file inside the function instance, which is fine locally and not something to rely on in production. Put email verification and per-user roles in front of it before using it with real stock across organisations.

## License

MIT — see `LICENSE`.
