from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db, engine
from app import models, schemas
from app.auth import hash_password, verify_password, create_access_token, get_current_user

# -----------------------
# Create Tables
# -----------------------
models.Base.metadata.create_all(bind=engine)

# -----------------------
# App Instance
# -----------------------
app = FastAPI(
    title="Product Inventory API",
    description="A REST API for managing product inventory with JWT authentication",
    version="1.0.0"
)

# -----------------------
# Routes - Auth
# -----------------------
@app.post("/auth/register", response_model=schemas.UserResponse, tags=["Authentication"])
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    if db.query(models.User).filter(models.User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = models.User(
        username=user.username,
        email=user.email,
        password=hash_password(user.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/auth/login", response_model=schemas.TokenResponse, tags=["Authentication"])
def login(request: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == request.username).first()
    if not user or not verify_password(request.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token(data={"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}

@app.post("/auth/token", include_in_schema=False)
def token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

# -----------------------
# Routes - Products
# -----------------------
@app.get("/products", response_model=List[schemas.ProductResponse], tags=["Products"])
def get_products(
    page: int = 1,
    limit: int = 10,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if page < 1:
        raise HTTPException(status_code=400, detail="Page must be greater than 0")
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 100")

    query = db.query(models.Product).filter(models.Product.user_id == current_user.id)

    if category:
        query = query.filter(models.Product.category == category)

    total = query.count()
    products = query.offset((page - 1) * limit).limit(limit).all()

    return products

@app.post("/products", response_model=schemas.ProductResponse, status_code=201, tags=["Products"])
def create_product(product: schemas.ProductCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    new_product = models.Product(
        name=product.name,
        description=product.description,
        price=product.price,
        quantity=product.quantity,
        category=product.category,
        user_id=current_user.id
    )
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return new_product

@app.get("/products/{id}", response_model=schemas.ProductResponse, tags=["Products"])
def get_product(id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    product = db.query(models.Product).filter(models.Product.id == id, models.Product.user_id == current_user.id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@app.put("/products/{id}", response_model=schemas.ProductResponse, tags=["Products"])
def update_product(id: int, updated: schemas.ProductUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    product = db.query(models.Product).filter(models.Product.id == id, models.Product.user_id == current_user.id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if updated.name is not None:
        product.name = updated.name
    if updated.description is not None:
        product.description = updated.description
    if updated.price is not None:
        product.price = updated.price
    if updated.quantity is not None:
        product.quantity = updated.quantity
    if updated.category is not None:
        product.category = updated.category

    db.commit()
    db.refresh(product)
    return product

@app.delete("/products/{id}", tags=["Products"])
def delete_product(id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    product = db.query(models.Product).filter(models.Product.id == id, models.Product.user_id == current_user.id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    db.delete(product)
    db.commit()
    return {"message": f"Product {id} deleted successfully"}

# -----------------------
# Routes - Health Check
# -----------------------
@app.get("/", tags=["Health"])
def root():
    return {"message": "Product Inventory API is running!", "docs": "/docs"}