from datetime import datetime, timezone
from random import choices
from uuid import uuid4

from flask import current_app
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy_utc import UtcDateTime

from urlshortener import db


class Token(db.Model):
    __tablename__ = 'tokens'

    id = db.Column(db.Integer, primary_key=True)
    api_key = db.Column(UUID, unique=True, index=True, default=lambda: str(uuid4()))
    name = db.Column(db.String, nullable=False, unique=True)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    is_blocked = db.Column(db.Boolean, nullable=False, default=False)
    token_uses = db.Column(db.Integer, nullable=False, default=0)
    last_access = db.Column(UtcDateTime, nullable=False, default=lambda: datetime.now(tz=timezone.utc))
    callback_url = db.Column(db.String, nullable=True)

    urls = db.relationship('URL', back_populates='token')

    def __repr__(self):
        return f'<Token({self.id}, {self.api_key}): {self.name}>'


class URL(db.Model):
    __tablename__ = 'urls'

    id = db.Column(db.Integer, primary_key=True)
    shortcut = db.Column(db.String, unique=True, index=True, default=lambda: generate_shortcut())
    url = db.Column(db.String, nullable=False)
    token_id = db.Column(db.ForeignKey('tokens.id'), nullable=False)
    custom_data = db.Column(JSONB, default={}, nullable=False)

    token = db.relationship('Token', back_populates='urls')

    def __repr__(self):
        return f'<URL({self.id}, {self.shortcut}): {self.url}>'


def generate_shortcut():
    alphabet = '23456789bcdfghjkmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ'
    shortcut_length = current_app.config.get('URL_LENGTH')
    while True:
        candidate = ''.join(choices(alphabet, k=shortcut_length))
        if not URL.query.filter_by(shortcut=candidate).count():
            return candidate
