"""WSGI entrypoint for Vercel's zero-configuration Flask preset.

Vercel loads the top-level `app` from server.py (one of its supported
entrypoint filenames). Local development can use this too:

    flask --app server run
"""

from app import create_app

app = create_app()
