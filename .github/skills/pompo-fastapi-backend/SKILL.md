---
name: pompo-fastapi-backend
description: 'FastAPI backend architecture and environment setup for the Pompo payment application. Use when writing API routes, setting up authentication, designing database models, configuring Docker, implementing tests, handling errors, validating requests, or managing migrations. Enforces consistent patterns for API design, security, database schema, and deployment across the backend.'
argument-hint: 'Specify the component: routes, auth, models, docker, tests, errors, validation, or migrations'
user-invocable: true
---

# Pompo FastAPI Backend Architecture

## Mission

This skill ensures consistent, production-ready backend development across the Pompo payment application.

Every component—API route, authentication mechanism, database model, test fixture, Docker configuration, error handler, validation schema, and migration—follows predictable patterns that:

- Enable **predictable** API contracts
- Enforce **security** throughout the stack
- Provide **observability** via structured logging and request tracking
- Ensure **testability** with clear fixtures and mocking boundaries
- Support **scalability** through async/await, connection pooling, and caching
- Enable **maintainability** through consistent naming and structure

---

## When to Use This Skill

Use this skill when:

- Writing new FastAPI endpoints or modifying existing routes
- Implementing user authentication, permissions, or role-based access control
- Designing new SQLAlchemy ORM models or database entities
- Adding or updating Docker containerization
- Writing unit, integration, or end-to-end tests
- Implementing error handling and exception strategies
- Creating request/response schemas with Pydantic validation
- Running Alembic migrations or designing schema changes
- Debugging security or authentication issues

---

## Core Principles

### 1. Explicit API Versioning

All API endpoints are versioned.

**Pattern:**
```
/api/v1/users
/api/v1/payments
```

Do not create unversioned endpoints. When introducing breaking changes, create a new API version (v2, v3).

**Implementation:**
```python
from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, request: Request) -> TokenResponse:
    pass
```

### 2. Structured Request/Response Schemas

All inputs and outputs are explicitly defined with Pydantic schemas.

**Request Schema:**
```python
from pydantic import BaseModel, EmailStr, Field

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=255)
```

**Response Schema:**
```python
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int
```

Always use type hints and field validation.

### 3. Dependency Injection with Fastapi

Dependencies are defined in `app/api/deps.py` and injected via type hints.

**Pattern:**
```python
from typing import Annotated
from fastapi import Depends

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    # Verify and decode token
    return user

CurrentUserDep = Annotated[User, Depends(get_current_user)]

@router.get("/me")
async def get_current_user_info(current_user: CurrentUserDep) -> UserResponse:
    return current_user
```

Use type aliases (`CurrentUserDep`, `AuthServiceDep`) for clarity.

### 4. Async/Await Throughout

All I/O operations are async:

```python
@router.post("/create-order")
async def create_order(payload: OrderRequest, auth_service: AuthServiceDep) -> OrderResponse:
    order = await auth_service.create_order(payload)
    return order
```

Do not block the event loop with synchronous operations in endpoints.

### 5. Unified Error Responses

All errors follow a consistent structure.

**Error Schema:**
```python
class ErrorDetail(BaseModel):
    field: str
    code: str
    message: str

class ErrorResponse(BaseModel):
    error: dict
    code: str
    message: str
    details: list[ErrorDetail] | None = None
    request_id: str | None = None
```

**Usage:**
```python
from fastapi import HTTPException, status

@router.post("/login")
async def login(payload: LoginRequest) -> TokenResponse:
    try:
        tokens = await auth_service.login(payload.email, payload.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
```

### 6. Structured Logging with Request Context

All logs are structured and include request tracing context.

**Pattern:**
```python
from app.core.logging import get_logger

logger = get_logger(__name__)

@router.post("/login")
async def login(payload: LoginRequest, request: Request) -> TokenResponse:
    logger.info(
        "login_attempt",
        email=payload.email,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent"),
    )
    try:
        tokens = await auth_service.login(payload.email, payload.password)
        logger.info("login_success", email=payload.email)
    except InvalidCredentialsError:
        logger.warning("login_failed", email=payload.email)
        raise
    return tokens
```

Every log entry should include:
- Event name (first positional argument)
- Relevant context as keyword arguments
- No personally identifiable information unless necessary

### 7. SQLAlchemy ORM Models

Models use:
- UUID primary keys
- Timezone-aware timestamps
- Explicit relationships
- Type hints

**Pattern:**
```python
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, UUIDPrimaryKeyMixin

class User(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "users"
    
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    refresh_sessions: Mapped[list["RefreshSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"
```

### 8. Database Migrations with Alembic

Every schema change requires a migration.

**Workflow:**
```bash
# After modifying a model:
alembic revision --autogenerate -m "Add user_profile table"

# Review the generated migration in migrations/versions/
# Then apply:
alembic upgrade head
```

**Migration principles:**
- Always provide both `upgrade()` and `downgrade()` implementations
- Use raw SQL for complex operations
- Add indexes for foreign keys and frequently queried columns
- Include data migrations in the same revision when necessary

### 9. Authentication & Authorization

#### OAuth2 with JWT

Access tokens are short-lived; refresh tokens enable long-lived sessions.

**Pattern:**
```python
# In services/auth.py
async def login(self, email: str, password: str) -> tuple[TokenPair, User]:
    user = await self.user_repo.get_by_email(email)
    if not user or not verify_password(password, user.password_hash):
        raise InvalidCredentialsError()
    
    access_token = self.create_access_token(user)
    refresh_token = self.create_refresh_token(user)
    
    return TokenPair(access=access_token, refresh=refresh_token), user
```

#### Refresh Token Rotation

Tokens are rotated on every refresh to detect replay attacks.

**Pattern:**
```python
async def refresh_access_token(self, refresh_token: str) -> TokenPair:
    session = await self.get_valid_refresh_session(refresh_token)
    
    # Create new tokens
    new_access = self.create_access_token(session.user)
    new_refresh = self.create_refresh_token(session.user)
    
    # Mark old session as replaced
    session.replaced_by_id = new_refresh_session.id
    
    return TokenPair(access=new_access, refresh=new_refresh)
```

#### Role-Based Access Control (RBAC)

Permissions are verified at the endpoint level using dependency injection.

**Pattern:**
```python
async def require_admin(current_user: CurrentUserDep) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Forbidden")
    return current_user

AdminUserDep = Annotated[User, Depends(require_admin)]

@router.delete("/users/{user_id}")
async def delete_user(user_id: UUID, admin: AdminUserDep) -> None:
    await user_service.delete(user_id)
```

### 10. Testing Strategy

#### Test Organization

```
tests/
├── conftest.py              # Shared fixtures
├── test_auth_api.py         # API endpoint tests
├── test_auth_service.py     # Service logic tests
├── test_models.py           # ORM model tests
├── test_health.py           # Health check tests
└── test_database.py         # Database integration tests
```

#### Test Database Setup

Each test runs against an isolated test database:

```python
# conftest.py
@pytest.fixture(scope="session")
def settings():
    get_settings.cache_clear()
    return get_settings()

@pytest.fixture
async def app(settings):
    application = create_app()
    yield application
    await application.state.redis_service.close()
    await dispose_engine()
```

#### Writing Tests

Use the provided client fixture to test endpoints:

```python
@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, auth_service: AuthServiceDep):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "password123"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
```

#### Fixtures for Common Patterns

```python
@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    user = User(email="test@example.com", password_hash=hash_password("password123"))
    db_session.add(user)
    await db_session.commit()
    return user

@pytest.fixture
async def authenticated_client(client: AsyncClient, test_user: User) -> AsyncClient:
    token = create_access_token(test_user)
    client.headers["Authorization"] = f"Bearer {token}"
    return client
```

### 11. Docker Configuration

#### Dockerfile

Multi-stage build minimizes image size:

```dockerfile
FROM python:3.11-slim as builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim

WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY app app/
COPY alembic alembic/
COPY alembic.ini .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Docker Compose

Services are orchestrated with Docker Compose:

```yaml
version: '3.9'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: pompo
      POSTGRES_PASSWORD: pompo_secret
      POSTGRES_DB: pompo
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  backend:
    build: .
    depends_on:
      - postgres
      - redis
    environment:
      DATABASE_URL: postgresql+asyncpg://pompo:pompo_secret@postgres:5432/pompo
      REDIS_URL: redis://redis:6379/0
    ports:
      - "8000:8000"
    volumes:
      - ./app:/app/app
```

**Run locally:**
```bash
docker compose up
```

**Run tests in container:**
```bash
docker compose exec backend pytest -v
```

### 12. Configuration Management

Environment-specific settings in `app/core/config/base.py`:

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "Pompo"
    app_version: str = "1.0.0"
    app_env: str  # "development", "staging", "production", "testing"
    
    database_url: str
    redis_url: str
    
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_seconds: int = 900  # 15 minutes
    
    class Config:
        env_file = ".env"
        case_sensitive = False

def get_settings() -> Settings:
    return Settings()
```

Load settings with:
```python
from app.core.config.base import get_settings

settings = get_settings()
print(settings.database_url)
```

### 13. Middleware Stack

The application includes:

1. **RequestIDMiddleware**: Assigns unique IDs to every request for tracing
2. **RequestLoggingMiddleware**: Logs every request and response
3. **RateLimitMiddleware**: Enforces rate limits (Redis-backed)
4. **CORSMiddleware**: Configures cross-origin requests
5. **TrustedHostMiddleware**: Restricts allowed hosts
6. **ExceptionHandler**: Converts exceptions to consistent error responses

Configure in `main.py`:

```python
from app.middleware.cors import configure_cors
from app.middleware.exception_handler import register_exception_handlers

def create_app() -> FastAPI:
    app = FastAPI()
    
    configure_cors(app)
    register_exception_handlers(app)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)
    
    return app
```

### 14. Error Handling Strategy

Define custom exceptions in `app/core/security/exceptions.py`:

```python
class AuthError(Exception):
    """Base authentication error."""
    pass

class InvalidCredentialsError(AuthError):
    """Raised when email/password is incorrect."""
    pass

class InactiveUserError(AuthError):
    """Raised when user account is disabled."""
    pass
```

Catch them in endpoints:

```python
@router.post("/login")
async def login(payload: LoginRequest, auth_service: AuthServiceDep) -> TokenResponse:
    try:
        tokens = await auth_service.login(payload.email, payload.password)
    except (InvalidCredentialsError, InactiveUserError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    return tokens
```

### 15. Rate Limiting

Rate limits are Redis-backed and enforce per-endpoint thresholds.

**Configuration in middleware:**
```python
class RateLimitMiddleware:
    def __init__(self, app: FastAPI, redis_client):
        self.app = app
        self.redis = redis_client
    
    async def __call__(self, request: Request) -> Response:
        user_id = extract_user_id(request)
        key = f"rate_limit:{user_id}"
        
        count = await self.redis.incr(key)
        if count == 1:
            await self.redis.expire(key, 60)  # 60-second window
        
        if count > 100:  # 100 requests per minute
            raise HTTPException(status_code=429)
        
        return await self.app(request)
```

---

## Workflow: Adding a New API Endpoint

### Step 1: Design the Contract

Before writing code, document:

```python
"""
GET /api/v1/users/{user_id}

Returns the user with the given ID. Requires authentication.

Path Parameters:
  user_id: UUID

Response (200):
  {
    "id": "uuid",
    "email": "user@example.com",
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z"
  }

Errors:
  401: Not authenticated
  403: Not authorized (trying to access another user's profile)
  404: User not found
"""
```

### Step 2: Define Schemas

Create request/response models in `app/schemas/`:

```python
# app/schemas/user.py
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

class UserResponse(BaseModel):
    id: UUID
    email: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
```

### Step 3: Implement the Service

Business logic belongs in `app/services/`:

```python
# app/services/user.py
class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo
    
    async def get_user(self, user_id: UUID) -> User:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found")
        return user
```

### Step 4: Create the Endpoint

Define the route in `app/api/v1/users.py`:

```python
from fastapi import APIRouter, HTTPException, status
from app.api.deps import CurrentUserDep, UserServiceDep
from app.schemas.user import UserResponse
from uuid import UUID

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    current_user: CurrentUserDep,
    user_service: UserServiceDep
) -> UserResponse:
    """Get a user by ID."""
    if user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    
    user = await user_service.get_user(user_id)
    return user
```

### Step 5: Register the Router

Include the router in `app/api/v1/router.py`:

```python
from fastapi import APIRouter
from app.api.v1 import users, auth, health

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth.router)
api_v1_router.include_router(users.router)
api_v1_router.include_router(health.router)
```

### Step 6: Test the Endpoint

Write tests in `tests/test_users_api.py`:

```python
@pytest.mark.asyncio
async def test_get_user_success(authenticated_client: AsyncClient, test_user: User):
    response = await authenticated_client.get(f"/api/v1/users/{test_user.id}")
    assert response.status_code == 200
    assert response.json()["email"] == test_user.email

@pytest.mark.asyncio
async def test_get_user_forbidden(authenticated_client: AsyncClient):
    other_user_id = uuid.uuid4()
    response = await authenticated_client.get(f"/api/v1/users/{other_user_id}")
    assert response.status_code == 403
```

---

## Workflow: Adding a New Database Model

### Step 1: Define the Model

Create in `app/models/`:

```python
# app/models/order.py
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, UUIDPrimaryKeyMixin
from datetime import datetime

class Order(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "orders"
    
    user_id: Mapped[UUID] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
```

### Step 2: Create a Migration

```bash
alembic revision --autogenerate -m "Add orders table"
```

Review and apply:

```bash
alembic upgrade head
```

### Step 3: Create a Repository

Implement data access in `app/repositories/order.py`:

```python
class OrderRepository(BaseRepository):
    async def create(self, user_id: UUID, amount: Decimal) -> Order:
        order = Order(user_id=user_id, amount=amount)
        self.session.add(order)
        await self.session.commit()
        return order
    
    async def get_by_id(self, order_id: UUID) -> Order | None:
        return await self.session.get(Order, order_id)
```

### Step 4: Create Tests

Write in `tests/test_models.py`:

```python
@pytest.mark.asyncio
async def test_order_creation(db_session: AsyncSession, test_user: User):
    order = Order(user_id=test_user.id, amount=Decimal("99.99"))
    db_session.add(order)
    await db_session.commit()
    
    fetched = await db_session.get(Order, order.id)
    assert fetched.amount == Decimal("99.99")
```

---

## Workflow: Implementing Authentication

### Step 1: Create User Model with Password Hashing

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, hash: str) -> bool:
    return pwd_context.verify(password, hash)
```

### Step 2: Implement Auth Service

```python
class AuthService:
    async def login(self, email: str, password: str) -> tuple[TokenPair, User]:
        user = await self.user_repo.get_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            raise InvalidCredentialsError()
        
        access_token = self.create_access_token(user)
        refresh_token = self.create_refresh_token(user)
        
        return TokenPair(access=access_token, refresh=refresh_token), user
```

### Step 3: Create JWT Utilities

```python
from datetime import datetime, timedelta
from jose import jwt

def create_access_token(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "exp": datetime.utcnow() + timedelta(minutes=15),
        "type": "access"
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")
```

### Step 4: Create Dependency for Current User

```python
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
        user_id = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = await user_repo.get_by_id(UUID(user_id))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user

CurrentUserDep = Annotated[User, Depends(get_current_user)]
```

### Step 5: Use in Protected Endpoints

```python
@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: CurrentUserDep) -> UserResponse:
    return current_user
```

---

## Common Patterns & Checklist

Before submitting a PR, verify:

- [ ] **API Contract**: Endpoint is documented with input/output schemas
- [ ] **Versioning**: Endpoint uses `/api/v1/` pattern
- [ ] **Schemas**: Request and response use Pydantic models
- [ ] **Error Handling**: Returns consistent error responses with status codes
- [ ] **Authentication**: Protected endpoints use `CurrentUserDep` dependency
- [ ] **Logging**: All significant operations are logged with context
- [ ] **Database**: Uses async SQLAlchemy with type-hinted models
- [ ] **Migrations**: Schema changes include Alembic migrations
- [ ] **Tests**: Endpoint has unit and integration tests
- [ ] **Docker**: Changes are compatible with Docker Compose setup
- [ ] **Configuration**: Settings are externalized to environment variables

---

## Reference Files

Consult these files for patterns and templates:

- **Application**: `app/main.py` — FastAPI app factory and lifespan
- **Dependencies**: `app/api/deps.py` — Injected dependencies
- **Auth Endpoints**: `app/api/v1/auth.py` — Login, refresh, logout patterns
- **Models**: `app/models/user.py`, `app/models/auth.py` — ORM patterns
- **Services**: `app/services/auth.py` — Business logic organization
- **Repositories**: `app/repositories/user.py` — Data access patterns
- **Middleware**: `app/middleware/` — Request logging, rate limiting, etc.
- **Configuration**: `app/core/config/base.py` — Settings management
- **Tests**: `tests/conftest.py` — Fixtures and test setup
- **Docker**: `docker-compose.yml`, `docker/Dockerfile` — Containerization

---

## Golden Rule

> **Design the API contract first. Enforce async/await throughout. Use dependency injection for testability. Log structured context. Validate all inputs. Return consistent errors. Test everything. Scale with caching and connection pooling.**
