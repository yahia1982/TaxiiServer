from .taxii_models import ApiRoot, Collection, StoredObject, ManifestRecord
from .user_models import User, Role # Re-add User and Role
from app.core.database import Base

# Ensure all models are imported here if Base.metadata.create_all is ever used directly,
# or for Alembic autogenerate to see all models.
# (Already handled by importing User, Role, and taxii_models which should import their contents)
