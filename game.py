from sqlalchemy import Column, Integer, PickleType
from sqlalchemy.orm import relationship

from base import Base


class Game(Base):
    __tablename__ = "games"

    group_tele_id = Column(Integer, primary_key=True)
    game_round = Column(Integer)
    curr_player = Column(Integer)
    biggest_player = Column(Integer)
    count_pass = Column(Integer)
    curr_cards = Column(PickleType)
    prev_cards = Column(PickleType)
    players = relationship("Player", backref="Game", cascade="all, delete")
