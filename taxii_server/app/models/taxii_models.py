from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func # For server-side default timestamps
import uuid
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base

class ApiRoot(Base):
    __tablename__ = "api_roots"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False, index=True) # Added index for potential filtering by title
    description = Column(String)
    versions = Column(JSONB, nullable=False, default=lambda: ["taxii-2.1"])
    max_content_length = Column(Integer, nullable=False)
    collections = relationship("Collection", back_populates="api_root", cascade="all, delete-orphan")

class Collection(Base):
    __tablename__ = "collections"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False, index=True) # Added index
    description = Column(String)
    alias = Column(String(100), unique=True, index=True, nullable=True) # Already unique indexed
    is_public_readable = Column(Boolean, default=False)
    media_types = Column(JSONB, nullable=False, default=lambda: ["application/stix+json;version=2.1"])
    api_root_id = Column(UUID(as_uuid=True), ForeignKey("api_roots.id"), nullable=False, index=True) # Added index
    api_root = relationship("ApiRoot", back_populates="collections")
    objects = relationship("StoredObject", back_populates="collection", cascade="all, delete-orphan")
    manifest_records = relationship("ManifestRecord", back_populates="collection", cascade="all, delete-orphan")

class StoredObject(Base):
    __tablename__ = "stored_objects"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stix_id = Column(String(255), index=True, nullable=False) # Already indexed
    type = Column(String(100), index=True, nullable=False) # Already indexed
    spec_version = Column(String(10), nullable=False, default="2.1")
    db_created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True) # Already indexed
    db_modified_at = Column(DateTime(timezone=True), onupdate=func.now())
    object = Column(JSONB, nullable=False)
    stix_modified_timestamp = Column(DateTime(timezone=True), index=True, nullable=False) # Already indexed
    collection_id = Column(UUID(as_uuid=True), ForeignKey("collections.id"), nullable=False, index=True) # Already indexed
    collection = relationship("Collection", back_populates="objects")

class ManifestRecord(Base):
    __tablename__ = "manifest_records"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stix_id = Column(String(255), index=True, nullable=False) # Already indexed
    stix_modified_timestamp = Column(DateTime(timezone=True), index=True, nullable=False) # Already indexed
    media_type = Column(String(255), nullable=False, default="application/stix+json;version=2.1")
    date_added_to_collection = Column(DateTime(timezone=True), server_default=func.now(), index=True) # Already indexed
    collection_id = Column(UUID(as_uuid=True), ForeignKey("collections.id"), nullable=False, index=True) # Already indexed
    collection = relationship("Collection", back_populates="manifest_records")
