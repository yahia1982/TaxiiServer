from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func # For server-side default timestamps
import uuid
from sqlalchemy.dialects.postgresql import UUID, JSONB # Using JSONB for better performance in Postgres

from app.core.database import Base

class ApiRoot(Base):
    __tablename__ = "api_roots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # path is not stored here, it's part of the routing/URL structure.
    # FastAPI will handle how an API root is accessed (e.g. /taxii/, /custom_api_root/)
    title = Column(String(255), nullable=False)
    description = Column(String)
    # versions should list supported TAXII versions, e.g., ["taxii-2.1"]
    versions = Column(JSONB, nullable=False, default=lambda: ["taxii-2.1"]) # Use JSONB
    max_content_length = Column(Integer, nullable=False) # In megabytes

    collections = relationship("Collection", back_populates="api_root", cascade="all, delete-orphan")

class Collection(Base):
    __tablename__ = "collections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # title, description, alias are human-readable
    title = Column(String(255), nullable=False)
    description = Column(String)
    alias = Column(String(100), unique=True, index=True, nullable=True) # Optional, user-defined alias

    # For TAXII, can_read and can_write are often determined by authentication/authorization logic
    # rather than being static booleans per collection for all users.
    # However, some TAXII servers might implement this for global collection settings.
    # We will primarily rely on role-based access tied to users.
    # These fields could define if a collection is *ever* readable or writable.
    is_public_readable = Column(Boolean, default=False) # If true, anyone can read (even unauthenticated)
                                                        # This needs careful handling in endpoint logic.
    # media_types defines what types of STIX objects this collection can contain/serve.
    media_types = Column(JSONB, nullable=False, default=lambda: ["application/stix+json;version=2.1"])

    api_root_id = Column(UUID(as_uuid=True), ForeignKey("api_roots.id"), nullable=False)
    api_root = relationship("ApiRoot", back_populates="collections")

    objects = relationship("StoredObject", back_populates="collection", cascade="all, delete-orphan")
    manifest_records = relationship("ManifestRecord", back_populates="collection", cascade="all, delete-orphan")


class StoredObject(Base):
    __tablename__ = "stored_objects"
    # This table stores the actual STIX objects.

    # Internal ID for the database record
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # STIX ID (e.g., "indicator--<uuid>")
    stix_id = Column(String(255), index=True, nullable=False)
    # STIX type (e.g., "indicator", "malware")
    type = Column(String(100), index=True, nullable=False)
    spec_version = Column(String(10), nullable=False, default="2.1") # e.g., "2.0", "2.1"

    # STIX 'created' and 'modified' are part of the object itself.
    # These are database timestamps for the record.
    db_created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    db_modified_at = Column(DateTime(timezone=True), onupdate=func.now())

    # The STIX object itself, stored as JSON.
    # Using JSONB for better indexing and performance in PostgreSQL.
    object = Column(JSONB, nullable=False)

    # Version of the STIX object (e.g., "2023-10-26T10:00:00.000Z")
    # This corresponds to the 'modified' field of the STIX object, typically.
    # Or could be a version number if versioning system is different.
    # For TAXII, this is usually the STIX object's modified timestamp.
    stix_modified_timestamp = Column(DateTime(timezone=True), index=True, nullable=False)

    collection_id = Column(UUID(as_uuid=True), ForeignKey("collections.id"), nullable=False, index=True)
    collection = relationship("Collection", back_populates="objects")

    # Unique constraint on stix_id and stix_modified_timestamp within a collection
    # to ensure each version of an object is stored only once per collection.
    # __table_args__ = (UniqueConstraint('stix_id', 'stix_modified_timestamp', 'collection_id', name='_stix_id_modified_collection_uc'),)
    # Actually, TAXII allows multiple objects with the same ID and version if they were added at different times.
    # The manifest uses (id, version, date_added).
    # Let's simplify: store one version of an object (stix_id + modified) per collection.
    # If a new version (same stix_id, different modified) comes, it's a new StoredObject.
    # If the same stix_id and modified is POSTed again, it could be an update to our db_modified_at or ignored.
    # TAXII spec: "If the Server receives an Object that has the same STIX ID and STIX version as an Object it already contains in the Collection, it SHOULD replace the existing Object."
    # This means (stix_id, stix_modified_timestamp, collection_id) should be unique.

class ManifestRecord(Base):
    __tablename__ = "manifest_records"
    # This table provides a manifest of objects in a collection.

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # STIX ID of the object this manifest record refers to.
    stix_id = Column(String(255), index=True, nullable=False)

    # The version of the STIX object this record pertains to (typically its 'modified' timestamp).
    stix_modified_timestamp = Column(DateTime(timezone=True), index=True, nullable=False)

    # Media type of the object, e.g., "application/stix+json;version=2.1"
    media_type = Column(String(255), nullable=False, default="application/stix+json;version=2.1")

    # Date when this specific version of the object was added to this collection.
    date_added_to_collection = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    collection_id = Column(UUID(as_uuid=True), ForeignKey("collections.id"), nullable=False, index=True)
    collection = relationship("Collection", back_populates="manifest_records")

    # A manifest record is unique by (stix_id, stix_modified_timestamp, collection_id)
    # This is implicitly handled if StoredObject is unique by this and ManifestRecord points to StoredObject.
    # However, the spec allows for objects to be added and removed, so a manifest record might exist
    # even if the object is (temporarily) unavailable.
    # For simplicity, our manifest will reflect what's in StoredObject.
    # When an object is added, a manifest record is created.
    # When an object version is updated/replaced, the manifest record's date_added_to_collection might update or a new one created if we track all additions.
    # TAXII 2.1 Section 3.4.1: "date_added: The date and time this specific version of the STIX Object was added to the Collection."
    # This implies (stix_id, stix_modified_timestamp, date_added_to_collection) could be a key if versions are re-added.
    # Let's assume for now that (stix_id, stix_modified_timestamp) is unique within a collection for StoredObject,
    # and ManifestRecord reflects this with its own date_added_to_collection.
