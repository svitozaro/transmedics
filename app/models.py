from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    first_name = db.Column(db.String(100), nullable=False, default="")
    last_name = db.Column(db.String(100), nullable=False, default="")
    role = db.Column(db.String(10), nullable=False)  # ADMIN, PIC or SIC
    group = db.Column(db.String(1))  # A or B, pilots only
    hire_date = db.Column(db.Date)  # pilots only
    password_hash = db.Column(db.String(255))  # None until a password is set
    must_change_password = db.Column(db.Boolean, nullable=False, default=True)
    active = db.Column(db.Boolean, nullable=False, default=True)
    prefs_submitted_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, nullable=False, default=now)

    preferences = db.relationship("Preference", order_by="Preference.rank",
                                  cascade="all, delete-orphan", back_populates="user")

    @property
    def is_admin(self):
        return self.role == "ADMIN"

    @property
    def is_pilot(self):
        return self.role in ("PIC", "SIC")

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.email


class Preference(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    period = db.Column(db.String(10), nullable=False)  # start date, YYYY-MM-DD
    rank = db.Column(db.Integer, nullable=False)
    user = db.relationship("User", back_populates="preferences")


class Assignment(db.Model):
    """The working (draft) schedule: one row per pilot after a run."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, unique=True)
    period = db.Column(db.String(10))  # None = could not be assigned
    source = db.Column(db.String(20), nullable=False)  # preference, rule11, none, manual
    rank = db.Column(db.Integer)
    explanation = db.Column(db.Text, nullable=False, default="")
    updated_at = db.Column(db.DateTime, nullable=False, default=now, onupdate=now)
    user = db.relationship("User")


class PublishedAssignment(db.Model):
    """What pilots were last told, used to email only the changes."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, unique=True)
    period = db.Column(db.String(10))


class Setting(db.Model):
    key = db.Column(db.String(50), primary_key=True)
    value = db.Column(db.String(255), nullable=False)


class PasswordToken(db.Model):
    """One-time links for invitations and password resets. Only a hash is stored."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    token_hash = db.Column(db.String(64), unique=True, nullable=False)
    purpose = db.Column(db.String(10), nullable=False)  # invite or reset
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, nullable=False, default=False)
    user = db.relationship("User")


class EmailMessage(db.Model):
    """Every email the app sends, also used as the local 'outbox'."""
    id = db.Column(db.Integer, primary_key=True)
    to = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="outbox")
    created_at = db.Column(db.DateTime, nullable=False, default=now)


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    actor = db.Column(db.String(255))
    action = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=now)
