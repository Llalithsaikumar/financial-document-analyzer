import os
import uuid
from typing import Generator, Optional

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, create_engine, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, declarative_base, relationship, sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/financial_analyzer",
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
DB_AVAILABLE = True
LAST_DB_ERROR: Optional[str] = None


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    analyses = relationship("AnalysisResult", back_populates="user")


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    query = Column(Text, nullable=False)
    source_file = Column(String(255), nullable=False)
    analysis = Column(Text, nullable=False)
    output_file = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="analyses")


def init_db() -> bool:
    global DB_AVAILABLE, LAST_DB_ERROR
    try:
        Base.metadata.create_all(bind=engine)
        DB_AVAILABLE = True
        LAST_DB_ERROR = None
        return True
    except SQLAlchemyError as exc:
        DB_AVAILABLE = False
        LAST_DB_ERROR = str(exc)
        return False


def is_db_available() -> bool:
    return DB_AVAILABLE


def get_db_error() -> Optional[str]:
    return LAST_DB_ERROR


def get_db() -> Generator[Optional[Session], None, None]:
    if not DB_AVAILABLE:
        yield None
        return

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
