import sqlalchemy as sa
from sqlalchemy import event
from sqlalchemy.orm import relationship, Session
from datetime import datetime, timezone

from api.core.base.base_model import BaseTableModel


class User(BaseTableModel):
    __tablename__ = 'users'
    
    email = sa.Column(sa.String, nullable=False, unique=True, index=True)
    cid = sa.Column(sa.Text, nullable=True)
    hash = sa.Column(sa.Text, nullable=True)
    blockchain_tx = sa.Column(sa.Text, nullable=True)
    # full_name = sa.Column(sa.String, nullable=True, unique=True, index=True)
    # nin = sa.Column(sa.String, nullable=True, unique=True, index=True)
