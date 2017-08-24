#!/usr/bin/env python3

import pydealer

from sqlalchemy import Column, Integer, PickleType
from sqlalchemy.ext.hybrid import hybrid_property

from base import Base
from cards import suit_unicode, get_cards_type, are_cards_bigger
from player import Player


class Game(Base):
    __tablename__ = "games"

    group_tele_id = Column(Integer, primary_key=True)
    game_round = Column(Integer)
    curr_player = Column(Integer)
    biggest_player = Column(Integer)
    count_pass = Column(Integer)
    curr_cards = Column(PickleType)
    prev_cards = Column(PickleType)
