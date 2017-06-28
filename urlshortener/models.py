import datetime
from uuid import uuid4

from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy_utc import UtcDateTime

from urlshortener import db


class Token(db.Model):
    __tablename__ = 'tokens'

    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(UUID,
                     unique=True,
                     index=True,
                     default=lambda: str(uuid4()))
    name = db.Column(db.Text, nullable=False, unique=True)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    is_blocked = db.Column(db.Boolean, nullable=False, default=False)
    token_uses = db.Column(db.Integer, nullable=False, default=0)
    last_access = db.Column(UtcDateTime, nullable=False, default=datetime.utcnow)
    creator = db.Column(db.ForeignKey('tokens.id'))
    urls = db.relationship('URL', backref='token')


class URL(db.Model):
    __tablename__ = 'urls'

    shorturl = db.Column(db.String(5), primary_key=True)
    url = db.Column(db.Text, unique=False)
    token_id = db.Column(db.ForeignKey('tokens.id'))
    urldata = db.Column(JSONB)
