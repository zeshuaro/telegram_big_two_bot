from sqlalchemy import Column, Integer

from base import Base


class GroupSetting(Base):
    __tablename__ = "group_settings"

    group_tele_id = Column(Integer, primary_key=True)
    join_timer = Column(Integer)
    pass_timer = Column(Integer)
