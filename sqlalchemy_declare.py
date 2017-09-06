from sqlalchemy import create_engine, ForeignKey
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

engine = create_engine('sqlite:///vk.db', echo=True)
Base = declarative_base()


class Message_FWD(Base):
    __tablename__ = "message_fwdmessage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(Integer, ForeignKey('message.id'))
    fwd_message_id = Column(Integer, ForeignKey('message.id'))


class Message(Base):
    __tablename__ = "message"

    id = Column(Integer, primary_key=True, autoincrement=True)
    from_id = Column(Integer)
    text = Column(Text)
    time = Column(DateTime)
    attachments = relationship("Attachment")
    fwd_messages = relationship("Message_FWD", primaryjoin="Message.id==Message_FWD.message_id")
    wall_attachment = relationship("Wall", uselist=False)


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True)
    first_name = Column(String)
    second_name = Column(String)


class Attachment_type(Base):
    __tablename__ = "attachment_type"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)


class Attachment(Base):
    __tablename__ = "attachment"

    id = Column(Integer, primary_key=True, autoincrement=True)
    type_id = Column(Integer)
    name = Column(String)
    link = Column(String)
    message_id = Column(Integer, ForeignKey('message.id'))
    wall_id = Column(Integer, ForeignKey('wall.id'))


class Wall(Base):
    __tablename__ = "wall"

    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_name = Column(String)
    text = Column(String)
    message_id = Column(Integer, ForeignKey('message.id'))
    attachments = relationship("Attachment")


Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()

objects = [
    Attachment_type(name="audio"),
    Attachment_type(name="photo"),
    Attachment_type(name="video"),
    Attachment_type(name="doc"),
    Attachment_type(name="link")
]
session.bulk_save_objects(objects)
session.commit()
