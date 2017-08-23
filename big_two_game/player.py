#!/usr/bin/env python3

import pydealer

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, Text, PickleType


Base = declarative_base()

class Player(Base):
    __tablename__ = "players"

    group_tele_id = Column(Integer, primary_key=True)
    player_tele_id = Column(Integer, primary_key=True)
    player_name = Column(Text)
    player_id = Column(Integer)
    cards = Column(PickleType)

    def __init__(self, player_id):
        self.player_ID = player_id
        self.cards = pydealer.Stack()
