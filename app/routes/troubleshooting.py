from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from math import radians, sin, cos, sqrt, atan2
from datetime import datetime

from .. import models, schemas
from ..database import get_db
from ..utils.ai_client import generate_steps
from ..auth.jwt_handler import get_current_user

router = APIRouter(
    prefix="/troubleshoot",
    tags=["Troubleshooting"]
)

# -------- Utils: Haversine distance ----------
def haversine_distance(lat1, lon1, lat2, lon2) -> float:
    R = 6371.0  # Earth radius in km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

@router.post("/engineers", response_model=schemas.EngineerOut)
def create_engineer(engineer: schemas.EngineerCreate, db: Session = Depends(get_db)):
    new_engineer = models.Engineer(
        name=engineer.name,
        email=engineer.email,
        service_time=engineer.service_time,
        picture_url=engineer.picture_url
    )
    db.add(new_engineer)
    db.commit()
    db.refresh(new_engineer)
    return new_engineer

# -------- Engineer Discovery ----------
@router.get("/engineers", response_model=list[schemas.EngineerOut])
def list_engineers(db: Session = Depends(get_db)):
    """
    Returns all available engineers with their profile info.
    """
    engineers = db.query(models.Engineer).all()
    return engineers


# -------- Booking ----------
@router.post("/bookings", response_model=schemas.BookingOut)
def create_booking(booking: schemas.BookingCreate, db: Session = Depends(get_db)):
    """
    Create a booking between a problem and an engineer.
    """
    problem = db.query(models.Problem).filter(models.Problem.id == booking.problem_id).first()
    engineer = db.query(models.Engineer).filter(models.Engineer.id == booking.engineer_id).first()
    if not problem or not engineer:
        raise HTTPException(status_code=404, detail="Problem or Engineer not found")

    db_booking = models.Booking(
        user_id=problem.user_id,  # may be None if problem wasn't tied to a user
        engineer_id=engineer.id,
        problem_id=problem.id,
        scheduled_time=booking.scheduled_time,
        confirmed=False
    )
    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)
    return db_booking


@router.patch("/bookings/{booking_id}/confirm", response_model=schemas.BookingOut)
def confirm_booking(
    booking_id: int,
    confirm_data: schemas.BookingConfirm,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Engineers (or Admins) can confirm a booking.
    """
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if current_user.role not in (models.UserRole.ENGINEER, models.UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Not authorized to confirm bookings")

    if current_user.role == models.UserRole.ENGINEER:
        engineer_record = db.query(models.Engineer).filter(models.Engineer.email == current_user.email).first()
        if engineer_record is None or engineer_record.id != booking.engineer_id:
            raise HTTPException(status_code=403, detail="You can only confirm your own bookings")

    booking.confirmed = confirm_data.confirmed

    if confirm_data.message:
        db_message = models.Troubleshoot(
            problem_id=booking.problem_id,
            message=f"Engineer response: {confirm_data.message}",
            created_at=datetime.utcnow()
        )
        db.add(db_message)

    db.commit()
    db.refresh(booking)
    return booking


# -------- User Problems ----------
@router.get("/user/problems")
def get_user_problems(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get all problems submitted by the authenticated user.
    """
    problems = db.query(models.Problem).filter(models.Problem.user_id == current_user.id).all()
    if not problems:
        return {"message": "No problems found for this user"}

    return [
        {
            "id": problem.id,
            "laptop_brand": problem.laptop_brand,
            "laptop_model": problem.laptop_model,
            "description": problem.description,
            "created_at": problem.created_at,
            "solved": problem.solved,
        }
        for problem in problems
    ]


# -------- Problem Endpoints ----------
@router.post("/", response_model=schemas.ProblemOut)
def create_problem(
    problem: schemas.ProblemCreate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)   # <-- add this
):
    """
    Creates a problem and generates AI steps.
    """
    db_problem = models.Problem(
        user_id=current_user.id,   # <-- set user_id here
        laptop_brand=problem.laptop_brand,
        laptop_model=problem.laptop_model,
        description=problem.description,
        created_at=datetime.utcnow()
    )
    db.add(db_problem)
    db.commit()
    db.refresh(db_problem)

    steps = generate_steps(problem.laptop_brand, problem.laptop_model, problem.description)
    for idx, step_text in enumerate(steps, start=1):
        db_step = models.Step(
            problem_id=db_problem.id,
            step_number=idx,
            instruction=step_text,
            completed=False
        )
        db.add(db_step)
    db.commit()

    db.refresh(db_problem)
    return db_problem


@router.get("/problems/{problem_id}")
def get_problem_with_steps(problem_id: int, db: Session = Depends(get_db)):
    """
    Returns problem details and all steps.
    """
    problem = db.query(models.Problem).filter(models.Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    
    return {
        "id": problem.id,
        "laptop_brand": problem.laptop_brand,
        "laptop_model": problem.laptop_model,
        "description": problem.description,
        "created_at": problem.created_at,
        "solved": problem.solved,
        "steps": [
            {
                "id": step.id,
                "step_number": step.step_number,
                "instruction": step.instruction,
                "completed": step.completed
            }
            for step in problem.steps
        ]
    }


@router.get("/{problem_id}", response_model=schemas.ProblemOut)
def get_problem(problem_id: int, db: Session = Depends(get_db)):
    """
    Fetch a problem by its ID.
    """
    problem = db.query(models.Problem).filter(models.Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    return problem


@router.patch("/{problem_id}/step/{step_id}")
def mark_step_completed(problem_id: int, step_id: int, db: Session = Depends(get_db)):
    """
    Mark a specific step as completed.
    """
    step = db.query(models.Step).filter(
        models.Step.id == step_id,
        models.Step.problem_id == problem_id
    ).first()

    if not step:
        raise HTTPException(status_code=404, detail="Step not found")

    step.completed = True
    db.commit()
    return {"message": "Step marked as completed"}
