# Fundamental Week

| Folder | Task | What it is |
|---|---|---|
| [`counter/`](counter/) | Task 2 | Counter app (Create React App) |
| [`employee-data-table-reusable/`](employee-data-table-reusable/) | Task 2 | Employee form with a reusable data table (Create React App) |
| [`user-management/`](user-management/) | Day 4 + Day 5 | Full-stack user management with login and roles: FastAPI backend + React frontend |

---

## User management (Day 4 + Day 5)

A full-stack app to list, search, create, edit and delete users. You must log in to see
or change users. **Admins** can change data; **viewers** can only read.

| Part | Stack | Docs |
|---|---|---|
| [`backend/`](user-management/backend/) | FastAPI, SQLAlchemy 2, Pydantic v2, Alembic, SQLite, PyJWT, Argon2 (`argon2-cffi`), pytest | [README](user-management/backend/README.md) |
| [`frontend/`](user-management/frontend/) | React 19, TypeScript, Vite, React Router | [README](user-management/frontend/README.md) |

### Day 4: Backend fundamentals and advanced API

- **Layered architecture:** router → service → repository → model. Each layer only talks
  to the one below it, and the service layer never imports FastAPI.
- **Full CRUD:** `GET`, `POST`, `PUT` (replace), `PATCH` (change only the fields sent),
  `DELETE` (soft delete).
- **Server-side search and pagination:** `GET /users?search=&page=&limit=` returns
  `{items, total, page, limit}`, with filtering, counting and paging done in SQL.
- **Centralized error handling:**
  - 404 for a missing user;
  - 409 for a duplicate email, including when two requests race;
  - 422 listing every invalid field at once;
  - a generic 500 that never leaks internal details. The real error is logged with the
    `logging` module.
- **Database migrations with Alembic:** `0001` users, `0002` the optional `city` column,
  `0003` accounts. `create_all()` is no longer used.
- **Request logging middleware:** every request gets an `X-Request-ID` and one log line
  with its method, path, status and duration.
- **Automated tests:** pytest with an in-memory test database. The real `users.db` is
  never touched.

### Day 5: Authentication and authorization

- **Accounts table:** separate from users, with a role restricted to `admin` or `viewer`
  by a database CHECK constraint.
- **Register / login / me / logout:** `POST /auth/register` (always creates a viewer),
  `POST /auth/login`, `GET /auth/me`, `POST /auth/logout`.
- **Password security:**
  - passwords are hashed with Argon2id and never returned or logged;
  - a wrong email and a wrong password get the same 401 message and take the same time,
    so the API never reveals which emails have accounts.
- **JWT in an httpOnly cookie:**
  - the token is a 30-minute HS256 JWT, stored in an `HttpOnly; Secure; SameSite=Strict`
    cookie, so JavaScript, and therefore XSS, can't read it;
  - the algorithm is pinned and `exp` is required;
  - the app refuses to start with a weak `JWT_SECRET`.
- **Protected routes and roles:**
  - every `/users` route needs a login, so a missing or invalid login gets **401**;
  - viewers can only read; creating, editing and deleting need the admin role, otherwise
    **403**.
- **Admin script:** `python -m scripts.create_admin`. Admins can't be created through the API.
- **Frontend auth:**
  - login and register pages, protected routes, and a header with the email, role and
    Logout;
  - a read-only table for viewers;
  - when the login expires, the user is sent back to the login page with
    "Session expired, please log in again."

### Documentation

| File | What it covers |
|---|---|
| [`backend/README.md`](user-management/backend/README.md) | Setup, environment variables, migrations, endpoints, error formats, tests |
| [`frontend/README.md`](user-management/frontend/README.md) | Setup, structure, how login, roles and errors work |
| [`backend/API_TESTS.md`](user-management/backend/API_TESTS.md) | Manual API test results (expected vs actual) |
| [`backend/AUTH_FLOW.md`](user-management/backend/AUTH_FLOW.md) | Register → login → cookie → protected request → 401/403 paths |
| [`backend/AUTH_NOTES.md`](user-management/backend/AUTH_NOTES.md) | Hashing, JWT structure, generic login error, cookie vs localStorage, roles |
| [`backend/BACKEND_FLOW.md`](user-management/backend/BACKEND_FLOW.md) | Request lifecycle, dependency injection, SQLAlchemy, validation, migrations, middleware |

---

## Getting started

### First-time setup

```powershell
# backend
cd user-management/backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
Copy-Item .env.example .env
# put a real secret in .env as JWT_SECRET:
python -c "import secrets; print(secrets.token_urlsafe(48))"
alembic upgrade head
python -m scripts.seed                                      # optional sample users
python -m scripts.create_admin --email admin@example.com    # asks for a password

# frontend
cd ../frontend
npm install
Copy-Item .env.example .env
```

### Run (two terminals)

```powershell
# backend: http://localhost:8000  (API docs at /docs)
cd user-management/backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --no-access-log

# frontend: http://localhost:5173
cd user-management/frontend
npm run dev
```

Log in with the admin account, or register a new (viewer) account on the login page.

### Tests

```powershell
cd user-management/backend
pytest -v
```

47 tests: the Day 4 users API, plus authentication and authorization (password hashing,
the auth cookie, invalid, tampered and expired tokens, and viewer vs admin access).
