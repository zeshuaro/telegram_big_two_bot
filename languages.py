from sqlalchemy import Column, Integer, Text

from base import Base

class Language(Base):
    __tablename__ = "languages"

    tele_id = Column(Integer, primary_key=True)
    language = Column(Text)