<div align="center">

<img src="assets/logo.svg" alt="DealerHub" width="300">

**Dealership management for companies that run more than one showroom.**

Several dealerships share one platform, and each one only ever sees its own cars, people and numbers.

![Python](https://img.shields.io/badge/Python-3.12-285b45?logo=python&logoColor=white) ![FastAPI](https://img.shields.io/badge/FastAPI-backend-285b45?logo=fastapi&logoColor=white) ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-285b45?logo=postgresql&logoColor=white) ![Redis](https://img.shields.io/badge/Redis-7-285b45?logo=redis&logoColor=white) ![Docker](https://img.shields.io/badge/Docker-Compose-285b45?logo=docker&logoColor=white)

[Getting started](#getting-started) · [Demo accounts](#demo-accounts) · [API](#api) · [Tests](#tests) · [Project structure](#project-structure)

</div>

<br>

![DealerHub dashboard](assets/dashboard.png)

## About

I wanted a system where a car dealership group can log in, manage its branches and staff, and not worry about another company on the same server seeing its data. Every request is tied to a company, and the backend makes sure queries stay inside it.

The backend is a REST API, so the web app (or anything else that speaks JSON) can talk to it without being coupled to it.

<table>
  <tr>
    <td width="70%"><img src="assets/inventory.png" alt="Inventory page"></td>
    <td width="30%"><img src="assets/mobile.png" alt="Dashboard on a phone"></td>
  </tr>
  <tr>
    <td align="center"><sub>Inventory with filters and status badges</sub></td>
    <td align="center"><sub>Works on phones too</sub></td>
  </tr>
</table>

## What's in here right now

This repository currently holds the backend core that everything else is built on:

| Feature | What it does |
|---|---|
| **Companies & branches** | Register a company with its owner account, then add branches |
| **Login** | JWT access tokens plus refresh tokens that rotate and can be revoked on logout |
| **Roles** | Owner, manager, salesperson, accountant, service and viewer, each with its own permissions |
| **Data isolation** | Records belong to a company and are filtered by it on every query |
| **Audit log** | Changes are recorded with who made them and when |
| **Health checks** | `/health` for liveness, `/health/ready` checks PostgreSQL and Redis |
| **Helpers** | Shared filtering, pagination and Redis caching used across the API |

The React web client shown in the screenshots is being added to the repo.

## Tech stack

- **FastAPI** with async SQLAlchemy 2
- **PostgreSQL 16**, schema managed by **Alembic** migrations
- **Redis 7** for caching
- **bcrypt** for passwords, **PyJWT** for tokens
- **pytest** against a real database, **ruff** for linting
- **Docker Compose** to run it all with one command

## Getting started

You need Docker with the Compose plugin.

```bash
git clone https://github.com/L0rikKelmendi/DealerHub.git
cd DealerHub
docker compose up --build -d
docker compose exec api python -m app.seed
```

Migrations run automatically when the API container starts. The seed script adds two demo companies with a few users, and running it again won't create duplicates.

Then open **http://localhost:8000/docs**.

| Service | Port on your machine |
|---|---|
| API | 8000 |
| PostgreSQL | 5433 |
| Redis | 6380 |

PostgreSQL and Redis use 5433 and 6380 so they don't clash with a local install. If something else is already using a port, override it:

```bash
POSTGRES_PORT=55433 REDIS_PORT=56380 API_PORT=58000 docker compose up --build -d
```

Stop everything with `docker compose down`. Your data stays in the volume unless you add `-v`.

<details>
<summary><b>Running the API without Docker</b></summary>

<br>

You still need the database and Redis, so start just those two, then run the API with Python 3.12+:

```bash
docker compose up -d db redis
make install
cp .env.example backend/.env
make migrate
make seed
make api
```

The `.env` goes in `backend/` because the API reads it from its working directory. Don't run this and the Docker API at the same time, they both want port 8000.

</details>

## Demo accounts

Password for all of them: `Password123!`

| Email | Company | Role |
|---|---|---|
| `owner@prishtina.dev` | Prishtina Motors | Owner |
| `sales@prishtina.dev` | Prishtina Motors | Salesperson |
| `accountant@prishtina.dev` | Prishtina Motors | Accountant |
| `owner@tirana.dev` | Tirana Auto Group | Owner |

Try logging in as both owners. Each one only gets their own company's users and branches back.

> These credentials and the default secrets in `.env.example` are only for running locally.

## API

Everything is under `/api/v1`. The easiest way to explore it is Swagger at `/docs` (ReDoc is at `/redoc`):

1. Call `POST /api/v1/auth/login` with one of the demo accounts
2. Copy the `access_token` from the response
3. Click **Authorize** and paste it in

![Swagger docs](assets/api-docs.png)

## Tests

38 tests cover auth, users, companies, health checks, middleware and the audit log. They run against real PostgreSQL and Redis instead of mocks, so the tenant filtering is tested the way it actually runs.

Create the test database once:

```bash
docker compose exec db createdb -U dealerhub dealerhub_test
```

Then:

```bash
export TEST_DATABASE_URL=postgresql+asyncpg://dealerhub:dealerhub@localhost:5433/dealerhub_test
export TEST_REDIS_URL=redis://localhost:6380/1
make test
make lint
cd backend && .venv/bin/alembic check
```

⚠️ The tests drop and recreate the schema and flush that Redis database, so never point them at data you care about.

## Project structure

```text
backend/
├── alembic/        migrations
├── app/
│   ├── api/        routes (health + /api/v1)
│   ├── core/       config, security, roles, middleware, filters, pagination, cache
│   ├── db/         session, base model, tenant-aware repository
│   ├── models/     company, branch, user, role, refresh token, audit log
│   ├── schemas/    request/response models
│   ├── services/   auth, company and user logic
│   └── seed.py     demo data
└── tests/
```

The first migration creates `companies`, `branches`, `users`, `roles`, `user_roles`, `refresh_tokens` and `audit_logs`.

## Development note

AI assistance was used in preparing this code.
