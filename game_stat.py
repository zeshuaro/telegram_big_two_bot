from sqlalchemy import Column, Integer, Text, Float

from base import Base


class GroupStat(Base):
    __tablename__ = "group_stats"

    tele_id = Column(Integer, primary_key=True)
    num_games = Column(Integer)
    best_win_rate_player = Column(Text)
    best_win_rate = Column(Float)
    most_money_earned_player = Column(Text)
    most_money_earned = Column(Integer)


class PlayerStat(Base):
    __tablename__ = "player_stats"

    tele_id = Column(Integer, primary_key=True)
    player_name = Column(Text)
    num_games = Column(Integer)
    num_games_won = Column(Integer)
    num_cards = Column(Integer)
    win_rate = Column(Float)
    money = Column(Integer)
    money_earned = Column(Integer)
