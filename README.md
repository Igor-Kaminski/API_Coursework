# Rail Reliability API

Coursework project for `COMP3011 Web Services and Web Data`.

This repository will contain a modular `FastAPI` backend for UK rail reliability and delay analytics. The system separates:

- reference data for `stations` and `routes`
- imported historical/operational data in `journey_records`
- user-generated operational data in `incidents`

## Planned Features

- public read endpoints for stations, routes, incidents, and analytics
- admin-only write endpoints for reference data
- incident CRUD for user and operator workflows
- modular import pipeline for rail reference and journey datasets
- analytics for route reliability, delay trends, hotspots, and delay reasons

## Tech Stack

- Python 3.11+
- FastAPI
- PostgreSQL
- SQLAlchemy 2.0
- Pydantic v2
- Alembic
- pytest

## Quick Start

1. Create a virtual environment.
2. Install dependencies with `pip install -e ".[dev]"`.
3. Copy values from `.env.example` into a local `.env`.
4. Run the API with `uvicorn app.main:app --reload`.

Detailed setup, migrations, import scripts, API usage, and coursework deliverables will be added as the project is implemented.
