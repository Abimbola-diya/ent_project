from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db
from ..utils.ai_client import generate_steps
from datetime import datetime

router = APIRouter(
    prefix="/troubleshoot",
    tags=["Troubleshooting"]
)


@router.post("/", response_model=schemas.ProblemOut)
def create_problem(problem: schemas.ProblemCreate, db: Session = Depends(get_db)):
    # 1. Save the problem in the DB
    db_problem = models.Problem(
        laptop_brand=problem.laptop_brand,
        laptop_model=problem.laptop_model,
        description=problem.description,
        created_at=datetime.utcnow()
    )
    db.add(db_problem)
    db.commit()
    db.refresh(db_problem)

    # 2. Generate AI steps
    steps = generate_steps(problem.laptop_brand, problem.laptop_model, problem.description)

    # 3. Save generated steps in DB
    for idx, step_text in enumerate(steps, start=1):
        db_step = models.Step(
            problem_id=db_problem.id,
            step_number=idx,
            instruction=step_text,
            completed=False
        )
        db.add(db_step)
    db.commit()

    # 4. Return the problem with steps
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
    This endpoint returns:
    - problem details (brand, model, description, created_at, solved status)
    - all steps with step_number, instruction, completed status
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
