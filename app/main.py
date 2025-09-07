from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models
from .database import engine
from .routers import auth, troubleshoot

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Laptop Repair Backend",
    version="1.0.0",
    description="API for AI-powered laptop troubleshooting and repair bookings"
)

# Allow requests from specific origins (like React at localhost:3000)
origins = [
    "http://localhost:3000",   # frontend dev
    "https://your-frontend.vercel.app"  # deployed frontend
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # or ["*"] to allow all
    allow_credentials=True,
    allow_methods=["*"],  # or specify ["GET", "POST"]
    allow_headers=["*"],  # or specify ["Content-Type", "Authorization"]
)

# ---- Routers ----
app.include_router(auth.router)
app.include_router(troubleshoot.router)


@app.get("/")
def root():
    return {"message": "Laptop Repair API is live!"}
