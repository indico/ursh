from uuid import uuid4

from sqlalchemy.dialects.postgresql import JSONB, UUID

from urlshortener.core.db import db


class Token(db.Model):
    __tablename__ = 'tokens'

    id = db.Column(UUID(as_uuid=True),
                   primary_key=True,
                   default=lambda: str(uuid4()))
    name = db.Column(db.Text, nullable=False, unique=True)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    is_blocked = db.Column(db.Boolean, nullable=False, default=False)
    token_uses = db.Column(db.Integer, nullable=False)
    last_access = db.Column(db.DateTime, nullable=False)
    creator = db.Column(db.ForeignKey('tokens.id'))
    urls = db.relationship('URL', backref='token')


class URL(db.Model):
    __tablename__ = 'urls'

    shorturl = db.Column(db.String(5), primary_key=True)
    url = db.Column(db.Text, unique=False)
    token_id = db.Column(UUID(as_uuid=True),
                         db.ForeignKey('tokens.id'))
    urldata = db.Column(JSONB)
