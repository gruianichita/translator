import uuid

from sqlalchemy import Column, DateTime, String, JSON, func, UUID
from sqlalchemy.orm import DeclarativeMeta, registry

mapper_registry = registry()


class Base(metaclass=DeclarativeMeta):
    __abstract__ = True

    registry = mapper_registry
    metadata = mapper_registry.metadata


class Word(Base):
    __tablename__ = "words"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_date = Column(DateTime, nullable=False, server_default=func.now())
    modified_date = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.current_timestamp())
    word = Column(String(255), unique=True)
    definitions = Column(JSON, default=list)
    synonyms = Column(JSON, default=list)
    translations = Column(JSON, default=list)
    examples = Column(JSON, default=list)
