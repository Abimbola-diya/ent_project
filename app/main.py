from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models
from .database import engine
from .routers import auth, troubleshoot

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# ---- CORS Configuration ----
origins = [
    "http://localhost:3000",            
    "https://laptop-medic.vercel.app",   
    "https://ent-project.onrender.com",   
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,     
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Routers ----
app.include_router(auth.router)
app.include_router(troubleshoot.router)


@app.get("/")
def root():
    return {"message": "Laptop Repair API is live!"}
