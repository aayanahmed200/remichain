# RemiChain

[![Python](https://img.shields.io/badge/python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/) [![Flask](https://img.shields.io/badge/flask-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/) [![SQLite](https://img.shields.io/badge/sqlite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://www.sqlite.org/)

RemiChain is a Flask prototype for matching surplus medical supplies with facility requests before supplies expire.

## Overview

Facilities can list surplus donations and submit requests. The matching service scores donation-request pairs using urgency, proximity, quantity fit, and expiry proximity, then creates proposed matches.

## Highlights

- Create and manage facility donations and supply requests.
- Rank potential matches using four scoring factors.
- Track proposed, reserved, partially fulfilled, and fulfilled states.
- View a dashboard and query donations, requests, and matches through a JSON API.
- Avoid duplicate proposals when no new data has been added.

## Technology

Python, Flask, Flask-SQLAlchemy, SQLite, and pytest.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export FLASK_APP=app
flask run --reload
```

Open `http://localhost:5000`.

Run the tests with:

```bash
pytest tests/
```

## Notes and limitations

This is a prototype. The current matching flow creates proposed matches; an accept/decline workflow is not implemented.

## License

MIT — see `LICENSE`.