# Product Inventory REST API

A production-style REST API built with FastAPI, PostgreSQL, JWT Authentication, Docker, and Pytest.

## Features
- JWT Authentication (register, login)
- Full CRUD for products
- Pagination and category filtering
- Input validation
- 13 automated tests (all passing)
- Docker Compose deployment
- Automatic Swagger documentation at /docs

## Tech Stack
- FastAPI
- PostgreSQL
- SQLAlchemy
- Docker Compose
- Pytest

## Run the project
docker-compose up --build

## Run tests
docker-compose exec web pytest tests/ -v