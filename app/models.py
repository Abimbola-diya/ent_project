from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, Enum, Float
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime
import enum

class UserRole(str, enum.Enum):
    USER = "user"
    ENGINEER = "engineer"
    ADMIN = "admin"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.USER)
    is_active = Column(Boolean, default=True)

    problems = relationship("Problem", back_populates="user")
    bookings = relationship("Booking", back_populates="user")


class Problem(Base):
    __tablename__ = "problems"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    laptop_brand = Column(String, nullable=False)
    laptop_model = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    solved = Column(Boolean, default=False)

    user = relationship("User", back_populates="problems")
    steps = relationship("Step", back_populates="problem", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="problem")
    troubleshoots = relationship("Troubleshoot", back_populates="problem", cascade="all, delete-orphan")


class Step(Base):
    __tablename__ = "steps"
    id = Column(Integer, primary_key=True, index=True)
    problem_id = Column(Integer, ForeignKey("problems.id"))
    step_number = Column(Integer)
    instruction = Column(Text)
    completed = Column(Boolean, default=False)

    problem = relationship("Problem", back_populates="steps")


class Troubleshoot(Base):
    __tablename__ = "troubleshoots"
    id = Column(Integer, primary_key=True, index=True)
    problem_id = Column(Integer, ForeignKey("problems.id"))
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    problem = relationship("Problem", back_populates="troubleshoots")


class Engineer(Base):
    __tablename__ = "engineers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)

    # Precise location
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    available_times = Column(Text)  # JSON string (e.g., ISO time slots)

    bookings = relationship("Booking", back_populates="engineer")


class Booking(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    engineer_id = Column(Integer, ForeignKey("engineers.id"))
    problem_id = Column(Integer, ForeignKey("problems.id"))
    scheduled_time = Column(DateTime, nullable=False)
    confirmed = Column(Boolean, default=False)

    user = relationship("User", back_populates="bookings")
    engineer = relationship("Engineer", back_populates="bookings")
    problem = relationship("Problem", back_populates="bookings")
