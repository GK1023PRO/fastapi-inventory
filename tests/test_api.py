import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db

# -----------------------
# Test Database (SQLite)
# -----------------------
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# -----------------------
# Setup & Teardown
# -----------------------
@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

client = TestClient(app)

# -----------------------
# Helper
# -----------------------
def register_and_login():
    client.post("/auth/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "123456"
    })
    response = client.post("/auth/login", json={
        "username": "testuser",
        "password": "123456"
    })
    return response.json()["access_token"]

def auth_headers():
    token = register_and_login()
    return {"Authorization": f"Bearer {token}"}

# -----------------------
# Auth Tests
# -----------------------
def test_register_user():
    response = client.post("/auth/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "123456"
    })
    assert response.status_code == 200
    assert response.json()["username"] == "testuser"

def test_register_duplicate_username():
    client.post("/auth/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "123456"
    })
    response = client.post("/auth/register", json={
        "username": "testuser",
        "email": "other@example.com",
        "password": "123456"
    })
    assert response.status_code == 400
    assert response.json()["detail"] == "Username already exists"

def test_login_success():
    client.post("/auth/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "123456"
    })
    response = client.post("/auth/login", json={
        "username": "testuser",
        "password": "123456"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_login_wrong_password():
    client.post("/auth/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "123456"
    })
    response = client.post("/auth/login", json={
        "username": "testuser",
        "password": "wrongpassword"
    })
    assert response.status_code == 401

# -----------------------
# Product Tests
# -----------------------
def test_create_product():
    headers = auth_headers()
    response = client.post("/products", json={
        "name": "Laptop",
        "description": "Gaming laptop",
        "price": 1200.00,
        "quantity": 5,
        "category": "Electronics"
    }, headers=headers)
    assert response.status_code == 201
    assert response.json()["name"] == "Laptop"

def test_create_product_invalid_price():
    headers = auth_headers()
    response = client.post("/products", json={
        "name": "Laptop",
        "price": -100,
        "quantity": 5
    }, headers=headers)
    assert response.status_code == 422

def test_create_product_invalid_quantity():
    headers = auth_headers()
    response = client.post("/products", json={
        "name": "Laptop",
        "price": 100,
        "quantity": -1
    }, headers=headers)
    assert response.status_code == 422

def test_get_products():
    headers = auth_headers()
    client.post("/products", json={
        "name": "Laptop",
        "price": 1200.00,
        "quantity": 5
    }, headers=headers)
    response = client.get("/products", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 1

def test_get_products_pagination():
    headers = auth_headers()
    for i in range(15):
        client.post("/products", json={
            "name": f"Product {i}",
            "price": 10.00,
            "quantity": 1
        }, headers=headers)
    response = client.get("/products?page=1&limit=10", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 10

    response = client.get("/products?page=2&limit=10", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 5

def test_get_single_product():
    headers = auth_headers()
    created = client.post("/products", json={
        "name": "Laptop",
        "price": 1200.00,
        "quantity": 5
    }, headers=headers).json()
    response = client.get(f"/products/{created['id']}", headers=headers)
    assert response.status_code == 200
    assert response.json()["name"] == "Laptop"

def test_update_product():
    headers = auth_headers()
    created = client.post("/products", json={
        "name": "Laptop",
        "price": 1200.00,
        "quantity": 5
    }, headers=headers).json()
    response = client.put(f"/products/{created['id']}", json={
        "price": 999.00
    }, headers=headers)
    assert response.status_code == 200
    assert response.json()["price"] == 999.00

def test_delete_product():
    headers = auth_headers()
    created = client.post("/products", json={
        "name": "Laptop",
        "price": 1200.00,
        "quantity": 5
    }, headers=headers).json()
    response = client.delete(f"/products/{created['id']}", headers=headers)
    assert response.status_code == 200

    response = client.get(f"/products/{created['id']}", headers=headers)
    assert response.status_code == 404

def test_unauthorized_access():
    response = client.get("/products")
    assert response.status_code == 401