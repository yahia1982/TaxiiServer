import pytest
from fastapi.testclient import TestClient
from fastapi import Security # Added for api_key_header_scheme in mock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session as SQLAlchemySession
from typing import Generator, Any, List, Dict, Optional
from unittest.mock import MagicMock # Removed patch, not directly used
import uuid

# Add project root to sys.path
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app
from app.core.database import Base, get_db
from app.core.config import settings
from app.models.user_models import User as UserModel, Role as RoleModel
from app.schemas.user_schemas import UserCreate, RoleCreate
from app.crud.crud_user import user_crud
from app.crud.crud_role import role_crud
from app.auth.dependencies import ROLE_ADMIN, ROLE_LITE_FEED, ROLE_FULL_ACCESS # Import roles
from app.auth.apikey import validate_api_key as real_validate_api_key, api_key_header_scheme # For mocking

TEST_SQLALCHEMY_DATABASE_URL = getattr(settings, "TEST_DATABASE_URL", "sqlite:///./test.db")
engine = create_engine(TEST_SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in TEST_SQLALCHEMY_DATABASE_URL else {})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session", autouse=True)
def create_test_database():
    if "sqlite" in TEST_SQLALCHEMY_DATABASE_URL and os.path.exists(TEST_SQLALCHEMY_DATABASE_URL.replace("sqlite:///","")):
        os.remove(TEST_SQLALCHEMY_DATABASE_URL.replace("sqlite:///","")) # Ensure clean DB for session
    Base.metadata.create_all(bind=engine)
    yield
    if "sqlite" in TEST_SQLALCHEMY_DATABASE_URL and os.path.exists(TEST_SQLALCHEMY_DATABASE_URL.replace("sqlite:///","")):
        os.remove(TEST_SQLALCHEMY_DATABASE_URL.replace("sqlite:///","")) # Clean up test DB file

@pytest.fixture(scope="function")
def db_session(create_test_database) -> Generator[SQLAlchemySession, Any, None]: # Depends on create_test_database
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    # Create default roles for tests that might need them
    role_crud["get_by_name"](session, name=ROLE_ADMIN) or role_crud["create"](session, RoleCreate(name=ROLE_ADMIN, description="Admin Role"))
    role_crud["get_by_name"](session, name=ROLE_LITE_FEED) or role_crud["create"](session, RoleCreate(name=ROLE_LITE_FEED, description="Lite Feed Role"))
    role_crud["get_by_name"](session, name=ROLE_FULL_ACCESS) or role_crud["create"](session, RoleCreate(name=ROLE_FULL_ACCESS, description="Full Access Role"))
    session.commit() # Commit roles
    yield session
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def client(db_session: SQLAlchemySession) -> Generator[TestClient, Any, None]:
    def override_get_db(): yield db_session
    app.dependency_overrides[get_db] = override_get_db

    # Store original dependency to restore it later
    original_validate_api_key = app.dependency_overrides.get(real_validate_api_key)
    async def mock_validate_no_key(api_key: Optional[str] = Security(api_key_header_scheme)): return None
    app.dependency_overrides[real_validate_api_key] = mock_validate_no_key

    with TestClient(app) as c: yield c

    # Restore original dependencies
    app.dependency_overrides[get_db] = get_db # Restore original get_db
    if original_validate_api_key is not None:
        app.dependency_overrides[real_validate_api_key] = original_validate_api_key
    else:
        if real_validate_api_key in app.dependency_overrides:
             del app.dependency_overrides[real_validate_api_key]

# --- Helper to create users with specific roles for testing ---
def create_test_user(db: SQLAlchemySession, username: str, password: str, role_name: str) -> UserModel:
    role = role_crud["get_by_name"](db, name=role_name)
    if not role: role = role_crud["create"](db, RoleCreate(name=role_name, description=f"{role_name} role"))
    # Check if user already exists, if so, update their role or return existing
    user = user_crud["get_by_username"](db, username=username)
    if user:
        user.role_id = role.id # Update role if user exists
        db.commit(); db.refresh(user)
        return user
    user = user_crud["create"](db, user_in=UserCreate(username=username, password=password, role_name=role_name))
    return user

@pytest.fixture(scope="function")
def test_admin_user(db_session: SQLAlchemySession) -> UserModel:
    return create_test_user(db_session, username="admin_user_for_test@example.com", password="adminpass", role_name=ROLE_ADMIN)

@pytest.fixture(scope="function")
def test_lite_feed_user(db_session: SQLAlchemySession) -> UserModel:
    return create_test_user(db_session, username="lite_user_for_test@example.com", password="litepass", role_name=ROLE_LITE_FEED)

@pytest.fixture(scope="function")
def test_full_access_user(db_session: SQLAlchemySession) -> UserModel:
    return create_test_user(db_session, username="full_user_for_test@example.com", password="fullpass", role_name=ROLE_FULL_ACCESS)

# --- Mocking API Key Validation ---
@pytest.fixture
def mock_api_key_validator(): # Removed monkeypatch for direct override
    """Fixture to mock the validate_api_key function.
    Usage in a test:
    mock_return_value = {'user_id': 'test_apikey_user', 'username': 'test_apikey_user', 'role': ROLE_ADMIN, 'auth_method': 'apikey'}
    async def custom_mock_validate(api_key: Optional[str] = Security(api_key_header_scheme)):
        if api_key == 'VALID_KEY': return mock_return_value
        return None
    app.dependency_overrides[real_validate_api_key] = custom_mock_validate
    yield
    # Clean up: remove the override after the test
    if real_validate_api_key in app.dependency_overrides:
        del app.dependency_overrides[real_validate_api_key]
    """
    # This fixture now just provides a context for setting the override in the test itself.
    # It doesn't return a controller object anymore, the test directly sets the override.
    # This is a common pattern if the mock logic needs to be highly test-specific.
    yield # Allows test to run with the override set in the test function
    # Cleanup is handled by the test or a broader fixture like 'client' if it manages this override
