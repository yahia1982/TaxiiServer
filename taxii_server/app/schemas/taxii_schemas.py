from enum import Enum

from pydantic import BaseModel, Field, AnyHttpUrl, conlist
from typing import List, Optional, Union, Dict, Any
from datetime import datetime
import uuid  # For UUIDs in responses if needed, though STIX IDs are strings


class UserScope(Enum):
    SYS_ADMIN = "sys-admin"
    ONLINE_DATA = "online-data"
    LITE_FEED = "lite-feed"


# Base STIX Object (highly simplified, as we mainly pass them through)
# The server doesn't need to understand the full STIX structure,
# just enough to store and retrieve it.
class STIXObject(BaseModel):
    type: str
    spec_version: Optional[str] = "2.1"
    id: str  # STIX ID e.g. "indicator--..."
    created: datetime
    modified: datetime
    # ... other common STIX fields ...
    # For this server, we'll often treat the STIX object as a Dict[str, Any]
    # after initial validation of required fields for TAXII.

    class Config:
        extra = "allow"  # Allow any other fields for STIX objects


# TAXII Error Message
class TAXIIError(BaseModel):
    title: str
    description: Optional[str] = None
    http_status: str  # e.g. "404"
    error_code: Optional[str] = None
    error_id: Optional[str] = None  # A request ID for tracking
    details: Optional[Dict[str, Any]] = None


# TAXII Discovery Endpoint Response (Section 4.1)
class ApiRootInfo(BaseModel):
    title: str
    description: Optional[str] = None
    versions: List[str] = ["taxii-2.1"]
    max_content_length: int  # In bytes as per spec, or MB as we defined in model? Let's stick to model for now.


class Discovery(BaseModel):
    title: str
    description: Optional[str] = None
    contact: Optional[str] = None
    default: Optional[AnyHttpUrl] = None  # URL of the default API Root
    api_roots: Optional[List[AnyHttpUrl]] = None


# API Root Response (Section 4.2) - This is essentially ApiRootInfo from our model
class ApiRoot(ApiRootInfo):
    pass  # It's the same structure as ApiRootInfo for TAXII 2.1


# Collection Response (Section 5.1)
class Collection(BaseModel):
    id: uuid.UUID  # Our internal UUID for the collection
    title: str
    description: Optional[str] = None
    alias: Optional[str] = None  # User-defined alias for the collection path
    can_read: bool  # Dynamically determined based on user auth
    can_write: bool  # Dynamically determined based on user auth
    media_types: Optional[List[str]] = ["application/stix+json;version=2.1"]


# Collections Response (List of Collections)
class Collections(BaseModel):
    collections: Optional[List[Collection]] = None


# TAXII Envelope for adding objects (Section 5.2.2)
class Envelope(BaseModel):
    # For TAXII 2.1, an envelope is just a list of STIX objects
    # but the spec also mentions 'more' and 'next' for pagination which are part of GET responses.
    # For POSTing objects, it's typically a list of STIX objects.
    # Let's define it as a list of STIX objects for requests.
    # For responses, it's more complex.
    objects: Optional[List[STIXObject]] = None
    # The spec says "The request BODY of this method contains a STIX bundle object."
    # A STIX Bundle is an object with type 'bundle' and an 'objects' key.
    # So, the client POSTs a STIX Bundle. Our server receives it.
    # Let's make this schema represent the *content* of the bundle for easier processing.


class STIXBundle(BaseModel):  # Represents a STIX Bundle object
    type: str = "bundle"
    id: str  # STIX ID for the bundle itself, e.g. "bundle--<uuid>"
    spec_version: Optional[str] = "2.1"
    objects: List[Dict[str, Any]]  # List of STIX objects as dicts


# Manifest Record (Section 5.4.1)
class ManifestRecord(BaseModel):
    id: str  # The STIX ID of the object
    date_added: datetime
    version: str  # The STIX modified timestamp, representing the version
    media_type: Optional[str] = "application/stix+json;version=2.1"


# Manifest Resource (Section 5.4)
class Manifest(BaseModel):
    objects: Optional[List[ManifestRecord]] = None
    # `more` and `next` for pagination would be added at the endpoint level if implemented


# Status Resource (Section 4.3) - Optional
class Status(BaseModel):
    id: uuid.UUID  # ID of the status resource / API Root it relates to
    status: str  # e.g. "pending", "complete", "error"
    request_timestamp: Optional[datetime] = None
    total_count: Optional[int] = None
    success_count: Optional[int] = None
    failure_count: Optional[int] = None
    pending_count: Optional[int] = None
    successes: Optional[List[str]] = None  # STIX IDs of successfully processed objects
    failures: Optional[List[Dict[str, str]]] = None  # STIX IDs and error messages
    pendings: Optional[List[str]] = None  # STIX IDs of pending objects


# Common query parameters for filtering objects
# These are not Pydantic schemas for request/response bodies,
# but will be used as FastAPI query parameters.
# We can define them here for reference or in the API endpoint functions directly.


# Example of how STIX object might be returned (if not in an envelope)
class ObjectById(BaseModel):
    # This would typically be a STIX object itself, or an envelope containing one.
    # The spec says: "The response BODY of this method contains the single STIX Object requested."
    # So, the response is just the STIX object (Dict[str, Any])
    pass  # No specific schema, the response is the STIX object itself.


# For listing objects in a collection (response for GET /collections/{id}/objects/)
class ObjectsEnvelope(BaseModel):
    more: Optional[bool] = False
    next: Optional[str] = None  # For pagination, URL to the next set of results
    objects: Optional[List[Dict[str, Any]]] = None  # List of STIX objects
