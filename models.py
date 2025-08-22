from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, LargeBinary, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import json

Base = declarative_base()

class Student(Base):
    __tablename__ = 'students'
    
    id = Column(Integer, primary_key=True)
    matricula = Column(String(50), unique=True, nullable=False, index=True)
    lastname = Column(String(100), nullable=False)
    firstname = Column(String(100), nullable=False)
    lotin = Column(String(100))  # Latin name
    short = Column(String(50))   # Short name
    group_name = Column(String(50))
    identifier = Column(String(100), unique=True, index=True)  # Идентификатор
    date_of_birth = Column(String(20))
    passport_number = Column(String(50))
    file_path = Column(String(500))  # Original photo file path
    face_encoding = Column(LargeBinary)  # Stored as binary numpy array
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'matricula': self.matricula,
            'lastname': self.lastname,
            'firstname': self.firstname,
            'lotin': self.lotin,
            'short': self.short,
            'group_name': self.group_name,
            'identifier': self.identifier,
            'date_of_birth': self.date_of_birth,
            'passport_number': self.passport_number,
            'file_path': self.file_path,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Pass(Base):
    __tablename__ = 'passes'
    
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, nullable=False, index=True)  # Foreign key to Student
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    source = Column(String(20), default='camera')  # camera, web, etc.
    confidence = Column(String(20))  # Distance/confidence of recognition
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'source': self.source,
            'confidence': self.confidence,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class LoadSession(Base):
    __tablename__ = 'load_sessions'
    
    id = Column(Integer, primary_key=True)
    filename = Column(String(500), nullable=False)
    records_processed = Column(Integer, default=0)
    records_added = Column(Integer, default=0)
    records_skipped = Column(Integer, default=0)
    errors = Column(Text)  # JSON string of errors
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    status = Column(String(20), default='running')  # running, completed, failed
    
    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'records_processed': self.records_processed,
            'records_added': self.records_added,
            'records_skipped': self.records_skipped,
            'errors': json.loads(self.errors) if self.errors else [],
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'status': self.status
        }