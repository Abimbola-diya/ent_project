from pydantic import BaseModel, EmailStr
from enum import Enum
from datetime import datetime
from typing import Optional

# ---------- Users ----------
class UserRole(str, Enum):
    USER = "user"
    ENGINEER = "engineer"
    ADMIN = "admin"

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: UserRole = UserRole.USER

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: UserRole

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str


# ---------- Problems ----------
class ProblemCreate(BaseModel):
    laptop_brand: str
    laptop_model: str
    description: str

class ProblemOut(BaseModel):
    id: int
    laptop_brand: str
    laptop_model: str
    description: str
    created_at: datetime
    solved: bool

    class Config:
        from_attributes = True


# ---------- Steps ----------
class StepOut(BaseModel):
    step_number: int
    instruction: str
    completed: bool

    class Config:
        from_attributes = True


# ---------- Troubleshoots ----------
class TroubleshootCreate(BaseModel):
    problem_id: int
    message: str

class TroubleshootOut(BaseModel):
    id: int
    problem_id: int
    message: str
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Engineers ----------
class EngineerOut(BaseModel):
    id: int
    name: str
    email: str
    latitude: Optional[float]
    longitude: Optional[float]
    available_times: Optional[str]  # JSON string

    class Config:
        from_attributes = True

class UserLocation(BaseModel):
    latitude: float
    longitude: float


# ---------- Booking ----------
class BookingCreate(BaseModel):
    problem_id: int
    engineer_id: int
    scheduled_time: datetime

class BookingOut(BaseModel):
    id: int
    problem_id: int
    engineer_id: int
    scheduled_time: datetime
    confirmed: bool

    class Config:
        from_attributes = True

class BookingConfirm(BaseModel):
    confirmed: bool
