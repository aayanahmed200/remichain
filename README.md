# RemiChain

[![Python](https://img.shields.io/badge/python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/flask-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![SQLite](https://img.shields.io/badge/sqlite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://www.sqlite.org/)

RemiChain matches surplus medical supplies with the facilities that need them, instead of letting usable equipment and medication expire in storage while other clinics run short.

## Why this exists

Hospitals and clinics regularly end up with supplies they can't use in time — equipment nobody needs right now, medication approaching its expiry date — while other facilities nearby are short on essential items. RemiChain connects donors with requesters and recommends efficient matches.

## How the matching works

Facilities list surplus supplies as donations and log what they need as requests. A matching engine (`app/services/matching.py`) scores every possible donation-to-request pair using four factors: urgency, proximity, quantity match, and expiration proximity. Matches are proposed to requesters and can be accepted or declined.

## Features

- List surplus supplies as donations, with quantity, category, and expiry date
- Log open requests from facilities, with an urgency score
- Automatic matching engine that proposes the best available match for each request
- Dashboard showing recent donations, requests, and matches
- A small JSON API (`/api/donations`, `/api/requests`, `/api/matches`, `/api/run-matching`) for querying and triggering matches

## Tech stack

- Python
- Flask
- Flask-SQLAlchemy (SQLite by default)
- pytest for the matching engine tests

## Project structure

- `app/models/` - Facility, SupplyDonation, SupplyRequest, Match
- `app/routes/` - main pages, donation/request forms, JSON API
- `app/services/matching.py` - the scoring and matching logic
- `app/services/seed.py` - sample facility data used on first run
- `tests/test_matching.py` - tests for the matching engine
- `LICENSE`

## Setup

```bash
git clone https://github.com/aayanahmed200/remichain.git
cd remichain
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export FLASK_APP=app
flask run --reload
```

Open http://localhost:5000 to view the dashboard.

## Tests

- `tests/test_matching.py` - covers the matching engine: urgency/expiry scoring, expired donations never matching, and ranked results for a request. Run with `pytest tests/`.

## License

MIT — see [LICENSE](LICENSE).
