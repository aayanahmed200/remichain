from app import db


class RateLimit(db.Model):
    """Fixed-window request counter.

    Kept in the database rather than in process memory: serverless instances
    start and stop constantly, so an in-memory counter would reset itself and
    never actually slow an attacker down. Rows are disposable and pruned as
    new windows are created.
    """

    __tablename__ = "rate_limits"

    id = db.Column(db.Integer, primary_key=True)
    # "<scope>:<identity>", e.g. "login:203.0.113.9" or "donate:12".
    bucket = db.Column(db.String(160), nullable=False, index=True)
    # Window number, i.e. epoch seconds // window length.
    window_start = db.Column(db.Integer, nullable=False)
    hits = db.Column(db.Integer, nullable=False, default=0)

    __table_args__ = (
        db.UniqueConstraint("bucket", "window_start", name="uq_rate_limit_bucket_window"),
    )
