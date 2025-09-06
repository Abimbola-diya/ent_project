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


# -------- Problem Endpoints ----------
@router.post("/", response_model=schemas.ProblemOut)
def create_problem(problem: schemas.ProblemCreate, db: Session = Depends(get_db)):
    """
    Creates a problem and generates the AI steps.
    If you want to associate the problem to an authenticated user,
    add current_user: models.User = Depends(get_current_user)
    and set user_id=current_user.id below.
    """
    db_problem = models.Problem(
        # user_id=<set to current_user.id if you add auth above>,
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


@router.get("/{problem_id}", response_model=schemas.ProblemOut)
def get_problem(problem_id: int, db: Session = Depends(get_db)):
    problem = db.query(models.Problem).filter(models.Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    return problem


@router.patch("/{problem_id}/step/{step_id}")
def mark_step_completed(problem_id: int, step_id: int, db: Session = Depends(get_db)):
    step = db.query(models.Step).filter(
        models.Step.id == step_id,
        models.Step.problem_id == problem_id
    ).first()

    if not step:
        raise HTTPException(status_code=404, detail="Step not found")

    step.completed = True
    db.commit()
    return {"message": "Step marked as completed"}


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


# -------- Engineer Discovery ----------
@router.post("/engineers/nearby")
def get_nearby_engineers(
    location: schemas.UserLocation,
    db: Session = Depends(get_db),
    radius_km: float = Query(50, gt=0, description="Search radius in kilometers")
):
    """
    Returns engineers within `radius_km` of the user's (lat, lon),
    sorted by distance ascending.
    """
    engineers = db.query(models.Engineer).all()
    results = []

    for eng in engineers:
        if eng.latitude is None or eng.longitude is None:
            continue
        dist = haversine_distance(location.latitude, location.longitude, eng.latitude, eng.longitude)
        if dist <= radius_km:
            results.append({
                "id": eng.id,
                "name": eng.name,
                "email": eng.email,
                "latitude": eng.latitude,
                "longitude": eng.longitude,
                "distance_km": round(dist, 2)
            })

    results.sort(key=lambda e: e["distance_km"])
    return results


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
    Only ENGINEER (assigned to this booking) or ADMIN can confirm a booking.
    """
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    # Role-based access
    if current_user.role not in (models.UserRole.ENGINEER, models.UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Not authorized to confirm bookings")

    if current_user.role == models.UserRole.ENGINEER:
        engineer_record = db.query(models.Engineer).filter(models.Engineer.email == current_user.email).first()
        if engineer_record is None or engineer_record.id != booking.engineer_id:
            raise HTTPException(status_code=403, detail="You can only confirm your own bookings")

    booking.confirmed = confirm_data.confirmed
    db.commit()
    db.refresh(booking)

    return booking
