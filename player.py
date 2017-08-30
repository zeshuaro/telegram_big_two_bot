from sqlalchemy import Column, Integer, Text, PickleType, ForeignKey, BigInteger

from base import Base


class Player(Base):
    __tablename__ = "players"

    group_tele_id = Column(BigInteger, ForeignKey("games.group_tele_id"))
    player_tele_id = Column(BigInteger, primary_key=True)
    player_name = Column(Text)
    player_id = Column(Integer)
    cards = Column(PickleType)
    num_cards = Column(Integer)
