from fastapi import FastAPI
from .database import Base, engine
from . import models
from .auth import routes as auth_routes
from .routes import troubleshooting
from fastapi.middleware.cors import CORSMiddleware

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Laptop Repair Backend",
    version="1.0.0",
    description="API for AI-powered laptop troubleshooting and repair bookings"
)

# ---- CORS Configuration ----
origins = [
    "http://localhost:3000",              # local frontend dev
    "https://laptop-medic.vercel.app",   # replace with actual deployed frontend URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,      # use ["*"] if you want to allow all for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth routes
app.include_router(auth_routes.router)

# Troubleshooting routes
app.include_router(troubleshooting.router)

@app.get("/")
def root():
    return {"message": "Laptop Repair API is running"}
