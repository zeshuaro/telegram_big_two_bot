from sqlalchemy import Column, Integer, Text, PickleType, ForeignKey

from base import Base


class Player(Base):
    __tablename__ = "players"

    group_tele_id = Column(Integer, ForeignKey("games.group_tele_id"))
    player_tele_id = Column(Integer, primary_key=True)
    player_name = Column(Text)
    player_id = Column(Integer)
    cards = Column(PickleType)
    num_cards = Column(Integer)
