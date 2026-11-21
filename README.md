# RemiChain

A Flask prototype that ranks possible matches between surplus medical-supply donations and requests from healthcare facilities.

## Overview

Facilities can post available supplies and submit requests. The matching service compares open requests with available donations for the same item, then scores possible matches using request urgency, expiry timing, geographic distance and how much of the requested quantity a donation can cover.

The app includes facility pages, donation and request forms, a matching service, and JSON endpoints for viewing records and running a matching pass.

## Repository contents

- `app/models/` — facility, donation, request and match data models.
- `app/routes/` — page routes and JSON API endpoints.
- `app/services/matching.py` — distance calculation, scoring and match creation.
- `templates/` and `static/` — Flask templates and frontend assets.
- `config.py` and `run.py` — application configuration and entry point.
- `tests/` — matching-engine tests.

## Technology

Python, Flask, Flask-SQLAlchemy, SQLite and pytest. Flask-SQLAlchemy manages the application data; the database is created when the app starts.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

Open [http://localhost:5000](http://localhost:5000).

Run the tests with:

```bash
pytest tests/
```

On Windows, activate the environment with `.venv\\Scripts\\activate` instead of the `source` command.

## Scope and limitations

This is a prototype, not a live medical-supply exchange. Match scores are heuristic suggestions based on the fields available in the app; they do not verify stock quality, regulatory requirements, transport arrangements or clinical suitability. The current workflow creates and tracks proposed matches, but does not provide a complete accept/decline and fulfilment process between real facilities.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for the full text.
