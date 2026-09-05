# Salon Booking API

FastAPI-based salon booking backend built as a **modular monolith** — feature
modules live under `app/modules/*`, and shared infrastructure under
`app/core` / `app/common`.

## Project Structure

```
.
├── app/
│   ├── main.py                  # FastAPI app entrypoint
│   ├── core/                    # Infra: config, security, database, logging,
│   │                            #   exceptions, rate-limit, redis, token blacklist
│   ├── common/                  # Shared: dependencies, pagination, responses,
│   │                            #   repository/service bases, utils
│   ├── modules/
│   │   ├── auth/                # Authentication + RBAC (roles/permissions)
│   │   │   ├── router.py        #   /auth, /roles, /permissions endpoints
│   │   │   ├── schemas.py
│   │   │   ├── models.py        #   Role, Permission + association tables
│   │   │   ├── service.py       #   AuthService, RoleService, PermissionService
│   │   │   ├── repository.py
│   │   │   └── dependencies.py  #   Service factories
│   │   └── users/               # User management (+ Shop domain for now)
│   │       ├── router.py        #   /users endpoints
│   │       ├── schemas.py
│   │       ├── models.py        #   User, Shop
│   │       ├── service.py
│   │       └── repository.py
│   └── api/
│       └── router.py            # API v1 aggregator (mounts feature routers)
├── migrations/                  # Alembic migration scripts
├── tests/
│   ├── auth/
│   └── users/
├── scripts/
│   ├── entrypoint.sh            # Docker entrypoint (migrate + seed + run)
│   └── seed.py                  # RBAC / super-admin seed CLI
├── alembic.ini
├── pyproject.toml
├── requirements.txt             # Kept for Docker build compatibility
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

## Requirements

- Python 3.11+
- PostgreSQL 16
- Redis 7

## Setup

```bash
# 1. Copy and edit environment variables
cp .env.example .env

# 2. Create virtualenv and install
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Run database migrations
alembic upgrade head

# 4. Seed default permissions/roles and a super admin
python scripts/seed.py rbac
python scripts/seed.py create-admin \
    --email admin@example.com \
    --password 'ChangeMe!123'

# 5. Start the API
uvicorn app.main:app --reload
```

API docs: http://127.0.0.1:8000/docs

## Docker

```bash
docker compose up --build
```

The API container runs migrations + seeding automatically via `scripts/entrypoint.sh`.

## Testing

```bash
pytest
```

## Key Endpoints

| Method | Path                        | Description                |
| ------ | --------------------------- | -------------------------- |
| POST   | `/api/v1/auth/register`      | Create an account          |
| POST   | `/api/v1/auth/login`         | Get access/refresh tokens  |
| POST   | `/api/v1/auth/refresh`       | Rotate tokens              |
| GET    | `/api/v1/auth/me`            | Current profile            |
| POST   | `/api/v1/auth/logout`        | Revoke current token       |
| GET    | `/api/v1/users/`             | List users (paginated)     |
| GET    | `/api/v1/users/{user_id}`    | User detail                |
| PUT    | `/api/v1/users/{user_id}`    | Update user                |
| DELETE | `/api/v1/users/{user_id}`    | Soft/hard delete user      |
| CRUD   | `/api/v1/roles/`             | Role management (RBAC)     |
| CRUD   | `/api/v1/permissions/`       | Permission management      |
