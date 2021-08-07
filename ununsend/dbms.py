from sqlalchemy import create_engine, func, Integer, String, Column, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from traceback import format_exc
from hashlib import sha256
from threading import Lock
import random
import string
import json
import os

from . import utils
from . import __database_path as default_database_path

Base = declarative_base()
lock = Lock()

class User:
    def __init__(self, user_id, authenticated=False, name=''):
        self.__is_authenticated = authenticated
        self.__uid = user_id
        self.name = name
    
    def is_authenticated(self):
        return self.__is_authenticated
    
    def is_anonymous(self):
        return False
    
    def is_active(self):
        return True

    def get_id(self):
        return self.__uid

class WebsiteStuffs(Base):
    __tablename__ = 'website_stuffs'

    key = Column(String, primary_key=True)
    value = Column(String) 

class WebsiteUsers(Base):
    __tablename__ = 'website_users'
    user_id = Column(String, primary_key=True)
    user_name = Column(String)
    is_authenticated = Column(Boolean)

class Messages(Base):
    __tablename__ = 'messages'

    record_identifier = Column(String, primary_key=True)
    message_id = Column(String)
    timestamp = Column(Integer)
    sender = Column(String)
    message = Column(String)

class UnsentMessage(Base):
    __tablename__ = 'unsent_messages'

    message_index = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(String)
    timestamp = Column(Integer)
    timestamp_us = Column(Integer)
    sender = Column(String)
    sender_name = Column(String)
    message = Column(String)
    thread_id = Column(String)
    thread_name = Column(String)

    def __repr__(self):
        rep = {'index': self.message_index, 'mid': self.message_id}
        return f'UnsentMessage({json.dumps(rep)})'

class Contacts(Base):
    __tablename__ = 'contacts'

    user_id = Column(String, primary_key=True)
    name = Column(String)

class MessageThreads(Base):
    __tablename__ ='message_threads'
    thread_id = Column(String, primary_key=True)
    name = Column(String)

class AuthManager:
    def __init__(self, dbSession):
        self.__dbSession = dbSession
    
    def get_auth_tokens(self):
        tokens = self.__dbSession.query(WebsiteStuffs).filter_by(key='auth_tokens').first()
        tokens = None if not tokens else json.loads(tokens.value)
        return [] if not tokens else tokens
    
    def update_auth_tokens(self, tokens:list):
        assert isinstance(tokens, list)
        tokens_on_db = self.__dbSession.query(WebsiteStuffs).filter_by(key='auth_tokens').first()
        if tokens_on_db == None:
            self.__dbSession.add(WebsiteStuffs(key='auth_tokens', value=json.dumps(tokens)))
        else:
            tokens_on_db.value = json.dumps(tokens)
        DBMS.commit_session(self.__dbSession)

    def add_auth_token(self, token):
        tokens = self.get_auth_tokens()
        tokens.append(token)
        self.update_auth_tokens(tokens)
    
    def add_and_get_new_token(self):
        token = sha256(os.urandom(2048)).hexdigest()
        self.add_auth_token(token)
        return token

    def remove_auth_token(self, token):
        tokens = self.get_auth_tokens()
        if token not in tokens:
            return False
        tokens.remove(token)
        self.update_auth_tokens(tokens)
        return True

class UnsentManager:
    def __init__(self, dbSession):
        self.__dbSession = dbSession
    
    def addMessage(self, message_id, timestamp, sender, message):
        record_identifier = sha256(os.urandom(1024)).hexdigest()
        dbObject = Messages(record_identifier=record_identifier, message_id=message_id, timestamp=timestamp, sender=sender, message=json.dumps(message))
        self.__dbSession.add(dbObject)
        DBMS.commit_session(self.__dbSession)
    
    def queryMessage(self, mid):
        return self.__dbSession.query(Messages).filter_by(message_id=mid).first()
    
    def queryUnsentMessage(self, mid):
        return self.__dbSession.query(UnsentMessage).filter_by(message_id=mid).first()

    def addContact(self, user_id, name):
        self.__dbSession.add(Contacts(user_id=user_id, name=name))
        DBMS.commit_session(self.__dbSession)

    def queryContact(self, user_id):
        return self.__dbSession.query(Contacts).filter_by(user_id=user_id).first()
    
    def queryMessageThread(self, thread_id):
        return self.__dbSession.query(MessageThreads).filter_by(thread_id=thread_id).first()

    def addMessageThread(self, thread_id, name):
        self.__dbSession.add(MessageThreads(thread_id=thread_id, name=name))
        DBMS.commit_session(self.__dbSession)

    def addUnsentMessage(self, message_id, timestamp, timestamp_us, sender, sender_name, message, thread_id, thread_name):
        if self.queryUnsentMessage(message_id):
            return # already processed unsent. sent twice by facebook
        dbObject = UnsentMessage(message_id=message_id, timestamp=timestamp, timestamp_us=timestamp_us, sender=sender, sender_name=sender_name, message=message, thread_id=thread_id, thread_name=thread_name)
        self.__dbSession.add(dbObject)
        DBMS.commit_session(self.__dbSession)
    
    def clearUp(self, clear_until):
        self.__dbSession.query(Messages).filter(Messages.timestamp < clear_until).delete()
        DBMS.commit_session(self.__dbSession)
    
    def getUnsentCount(self):
        return self.__dbSession.query(UnsentMessage).count() # https://stackoverflow.com/questions/10822635/get-the-number-of-rows-in-table-using-sqlalchemy
    
    def get_raws(self, start, size, desc=False):
        if desc:
            result = self.__dbSession.query(UnsentMessage).order_by(UnsentMessage.message_index.desc()).limit(size).offset(start).all()
        else:
            result = self.__dbSession.query(UnsentMessage).limit(size).offset(start).all()
        return result
    
    def get_last_index(self):
        return self.get_raws(0,1,True)[0].message_index

    def get_before_index(self, index, size, desc=False):
        result = self.__dbSession.query(UnsentMessage).filter(UnsentMessage.message_index < index).order_by(UnsentMessage.message_index.desc()).limit(size).all()
        if desc:
            return result
        else:
            return result[::-1]
    
    def get_all(self):
        return self.__dbSession.query(UnsentMessage).all()

class DBMS():
    def __init__(self, database_path=default_database_path):
        db_path = 'sqlite:///' + os.path.expanduser(database_path)
        engine = create_engine(db_path, connect_args={"check_same_thread": False})
        Base.metadata.create_all(engine)
        self.dbSession = sessionmaker(engine)()
        self.tokenManager = AuthManager(self.dbSession)
        self.unsentManager = UnsentManager(self.dbSession)
    
    def get_website_user(self, user_id):
        user = self.dbSession.query(WebsiteUsers).filter_by(user_id=user_id).first()
        if user != None:
            return User(user.user_id, user.is_authenticated, user.user_name)
    
    def add_and_get_user(self, authenticated=False, name='', uid=None):
        if not uid:
            uid = ''.join([random.choice(string.ascii_lowercase) for _ in range(16)])
        self.dbSession.add(WebsiteUsers(user_id=uid, is_authenticated=authenticated, user_name=name))
        DBMS.commit_session(self.dbSession)
        return self.get_website_user(uid)
    
    def update_website_stuff(self, key, value):
        stuff = self.dbSession.query(WebsiteStuffs).filter_by(key=key).first()
        if stuff == None:
            self.dbSession.add(WebsiteStuffs(key=key, value=json.dumps(value)))
        else:
            stuff.value = json.dumps(value)
        DBMS.commit_session(self.dbSession)

    def get_website_stuff(self, key):
        stuff = self.dbSession.query(WebsiteStuffs).filter_by(key=key).first()
        return stuff if stuff == None else json.loads(stuff.value)
    
    def get_last_message_contact_id(self):
        msg = self.dbSession.query(Messages).order_by(Messages.timestamp.desc()).first()
        return None if msg==None else msg.sender

    def get_flask_secret(self):
        secret = self.get_website_stuff('flask_secret')
        if secret:
            return secret
        secret = sha256(os.urandom(4096)).hexdigest()
        self.update_website_stuff('flask_secret', secret)
        return secret

    @staticmethod
    def commit_session(session):
        with lock:
            DBMS._commit_session_impl(session)
            
    
    @staticmethod
    def _commit_session_impl(session, retry=True):
        try:
            session.commit()
        except:
            if retry:
                session.rollback()
                DBMS._commit_session_impl(session, False)
            else:
                fmt_exec = format_exc()
                utils.debug_discord(f'DB commit failed. Reason:\n{fmt_exec}')
                print(fmt_exec)
