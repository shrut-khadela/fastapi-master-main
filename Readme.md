# Python-FastAPI Web-Server Boilerplate
This is a boilerplate for the FastAPI framework with best practices and pre-setup user domain. One can add the new domains as per the requirements after cloning it.

## This repo contains or will contain following things

- [x] Basic setup and configurations
- [x] Add User domain with Basic info
- [x] Support for JWT Auth
- [x] Alembic DataBase Migration support
- [x] Basic test cases setup
- [x] Test cases for user domain (SSO/3rd party login not implemented yet)
- [X] Docker support
- [X] pre-commit for code formatting and best practices checks
- [X] `requirements.txt` file and `dev-requirements.txt` files for raw and exact requirements

<br>

# Setup

## Environment Variables

Before running the project, you need to create a `.env` file from `.env-example`:

```bash
cp .env-example .env
```

Then edit the `.env` file and fill in the required values:
- `CONTACT_EMAIL`: Your contact email
- `LOG_LEVEL`: Logging level (e.g., INFO, DEBUG)
- `DEPLOYMENT_ENV`: Environment (e.g., DEV, PROD)
- `SERVER_PORT`: Server port (default: 8000)
- `SERVER_HOST`: Server host (default: 0.0.0.0)
- `TERMS_OF_SERVICE`: Terms of service URL
- `POSTGRES_USER`: PostgreSQL username
- `POSTGRES_PASSWORD`: PostgreSQL password
- `POSTGRES_DB`: PostgreSQL database name
- `POSTGRES_SERVER`: PostgreSQL server host
- `POSTGRES_PORT`: PostgreSQL server port

# Run the Project Using Uvicorn

### Create virtual env and activate it

    python3 -m venv venv
    source venv/bin/activate

### Install the requirements

    pip install -r requirements.txt

### If this shows any error in installation of any dependency, run the below command
    pip install -r dev-requirements.txt

### Run Server
    uvicorn src.main:create_app --host 0.0.0.0 --port 8000 --reload --factory


# Docker Setup

    docker compose up --build
    docker compose exec -it web /bin/bash

# Database Migration

Note: If any new entity is added to the Project, we need to add it to `alembic/env.py`.

## Alembic Commands

### Create a new version for migration
```bash
alembic revision --autogenerate -m "v0.0 initial commit"
```

### Upgrade to the newest version
```bash
alembic upgrade head
```

**Note:** Delete tables and data types from the database before migrating.

**Note:** Delete SQLAlchemy version scripts from the versions folder.

**Note:** One-to-one relationships return None when there's no data associated with a particular relation. One-to-many and others return an empty list, so keep checking if None in one-to-one before accessing db object's attributes.

# Docker Debug Endpoint using breakpoint

1. Start the Container in detached mode

- `docker compose up -d --build`

2. List docker running containers and get the id of the container you want to debug

- `docker container ps`

3. Attach a debugger to the container

- `docker attach <container ID>`

4. Add 'breakpoint()' in endpoint and hit the endpoint to stop at the breakpoint

# Run pytest

```bash
python -m pytest tests/ --cov=src/ --cov-fail-under=100 -v
```
