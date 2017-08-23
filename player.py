import pydealer

from sqlalchemy import Column, Integer, Text, PickleType, ForeignKey
from sqlalchemy.orm import relationship

from base import Base

class Player(Base):
    __tablename__ = "players"

    group_tele_id = Column(Integer, ForeignKey("games.group_tele_id"))
    # player_tele_id = Column(Integer, primary_key=True)
    player_tele_id = Column(Integer)
    player_name = Column(Text)
    player_id = Column(Integer, primary_key=True)
    cards = Column(PickleType)

    # _game = relationship("Game", back_populates="players")
