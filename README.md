# DealerHub

DealerHub is a backend for car dealerships that share one application but keep their company data separate. It handles company accounts, branches, users, permissions and request auditing through a REST API.

Built with **FastAPI · PostgreSQL · SQLAlchemy · Alembic · Redis**.

![DealerHub API documentation showing authentication and company endpoints](assets/api-docs.png)

*The running API, explored through its built-in Swagger interface. This repository contains the backend; a web frontend is not included.*

## Features

- Register a company and its owner account, then log in through the API.
- Use JWT access tokens and rotating refresh tokens; revoke a refresh token on logout.
- Manage users, company details and branches with the appropriate permissions.
- Assign the six roles: owner, manager, salesperson, accountant, service and viewer.
- Keep tenant-owned records scoped to the authenticated user's company.
- Record changes in the audit log and check database/Redis readiness.

The backend uses PostgreSQL 16 and SQLAlchemy 2 for persistence, Alembic for schema changes, and Redis for caching. Passwords are hashed with bcrypt. Any client can connect through REST/JSON; Swagger provides a way to try the endpoints without a separate interface.

## Run with Docker

Install Docker with the Compose plugin, then run these commands from the repository root:

```bash
git clone https://github.com/L0rikKelmendi/DealerHub.git
cd DealerHub
docker compose up --build -d
docker compose exec api python -m app.seed
```

The API applies its migration before starting. The seed adds two demo companies, two branches and four users. It skips those demo records if they already exist.

- Swagger: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health: http://localhost:8000/health
- Database and Redis readiness: http://localhost:8000/health/ready

The default host ports are **8000** for the API, **5433** for PostgreSQL and **6380** for Redis. They are bound to localhost. If another local project is using them, stop that project's services or choose different ports:

```bash
POSTGRES_PORT=55433 REDIS_PORT=56380 API_PORT=58000 docker compose up --build -d
```

With those overrides, Swagger is at `http://localhost:58000/docs`. Containers still connect to PostgreSQL and Redis using their internal service ports.

To view logs or stop the stack:

```bash
docker compose logs -f api
docker compose down
```

`docker compose down` keeps the database volume. Do not add `-v` unless you intend to delete its data.

## Demo accounts

All four accounts use the password `Password123!`.

| Account | Company | Role |
|---|---|---|
| `owner@prishtina.dev` | Prishtina Motors | Owner |
| `sales@prishtina.dev` | Prishtina Motors | Salesperson |
| `accountant@prishtina.dev` | Prishtina Motors | Accountant |
| `owner@tirana.dev` | Tirana Auto Group | Owner |

In Swagger, call `POST /api/v1/auth/login`, copy the returned `access_token`, and paste it into **Authorize**. You can then try the protected endpoints. Logging in as the second company's owner is useful for checking that company data stays separate.

These are public demo credentials. The default database password and signing key are for local development only, not a public deployment.

## Run the API locally

Use Python 3.12 or newer and `make`. Start just the database and Redis containers, then install the backend dependencies:

```bash
docker compose up -d db redis
make install
cp .env.example backend/.env
make migrate
make seed
make api
```

Run these commands from the repository root. The API reads `.env` from its working directory, so the local configuration belongs in **`backend/.env`**, not the repository root. The example URLs already match ports 5433 and 6380; update them if you changed the host ports.

Do not run the local API and the Compose API on port 8000 at the same time.

## Tests and migration checks

The backend has **38 tests** covering authentication, user and company APIs, health checks, and middleware/audit behavior. They use real PostgreSQL and Redis rather than replacing the database with a mock.

Create a dedicated test database once:

```bash
docker compose exec db createdb -U dealerhub dealerhub_test
```

Then run the checks from the repository root after `make install`:

```bash
export TEST_DATABASE_URL=postgresql+asyncpg://dealerhub:dealerhub@localhost:5433/dealerhub_test
export TEST_REDIS_URL=redis://localhost:6380/1
make test
make lint
cd backend
.venv/bin/alembic check
```

The test suite recreates the test schema and flushes the selected Redis database. **Never point these test variables at a database containing data you want to keep.** Redis database 1 is reserved for tests here; the application uses database 0. Run migrations before `alembic check`.

## Code layout

```text
backend/
  alembic/             Initial migration and migration configuration
  app/
    api/               Health routes and versioned API routers
    core/              Settings, authentication, roles, middleware and shared helpers
    db/                Sessions, model base and repositories
    models/            Company, branch, user, role, token and audit models
    schemas/           Request and response validation
    services/          Authentication, company and user operations
    seed.py            Demo accounts and companies
  tests/               API and middleware tests
```

The initial migration creates seven tables: `companies`, `branches`, `users`, `roles`, `user_roles`, `refresh_tokens` and `audit_logs`. Filtering, pagination and caching helpers live alongside the authentication and configuration code.

## Development note

AI assistance was used in preparing this code.
