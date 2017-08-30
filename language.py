from sqlalchemy import Column, Integer, Text, BigInteger

from base import Base


class Language(Base):
    __tablename__ = "languages"

    tele_id = Column(BigInteger, primary_key=True)
    language = Column(Text)
