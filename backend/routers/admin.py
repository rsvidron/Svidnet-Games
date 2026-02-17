"""
Admin API endpoints for managing categories and questions
"""
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel
import re

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from models.admin import TriviaCategory, CustomTriviaQuestion
from models.user import User

router = APIRouter(prefix="/api/admin", tags=["admin"])


def get_db():
    """Get database session"""
    from database import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user_id(authorization: Optional[str] = Header(None)) -> int:
    """Extract user ID from JWT token - for now returns 1"""
    # TODO: Implement proper JWT validation and admin role check
    return 1


def is_admin(user_id: int, db: Session) -> bool:
    """Check if user is admin"""
    user = db.query(User).filter(User.id == user_id).first()
    return user and user.role == "admin"


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug"""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text


# Schemas

class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    is_active: Optional[bool] = None


class CategoryResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str]
    icon: Optional[str]
    is_active: bool
    question_count: int = 0


class QuestionCreate(BaseModel):
    category_id: int
    question: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_answer: int  # 0-3
    explanation: Optional[str] = None
    difficulty: str = "medium"


class QuestionUpdate(BaseModel):
    question: Optional[str] = None
    option_a: Optional[str] = None
    option_b: Optional[str] = None
    option_c: Optional[str] = None
    option_d: Optional[str] = None
    correct_answer: Optional[int] = None
    explanation: Optional[str] = None
    difficulty: Optional[str] = None
    is_active: Optional[bool] = None


class QuestionResponse(BaseModel):
    id: int
    category_id: int
    question: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_answer: int
    explanation: Optional[str]
    difficulty: str
    is_active: bool
    times_used: int
    times_correct: int


# Category Endpoints

@router.get("/categories", response_model=List[CategoryResponse])
def list_categories(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """List all trivia categories with question counts"""
    categories = db.query(TriviaCategory).order_by(TriviaCategory.name).all()

    result = []
    for cat in categories:
        question_count = db.query(CustomTriviaQuestion).filter(
            CustomTriviaQuestion.category_id == cat.id,
            CustomTriviaQuestion.is_active == True
        ).count()

        result.append(CategoryResponse(
            id=cat.id,
            name=cat.name,
            slug=cat.slug,
            description=cat.description,
            icon=cat.icon,
            is_active=cat.is_active,
            question_count=question_count
        ))

    return result


@router.post("/categories", response_model=CategoryResponse)
def create_category(
    data: CategoryCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """Create a new trivia category"""
    if not is_admin(user_id, db):
        raise HTTPException(403, "Admin access required")

    slug = slugify(data.name)

    # Check if category already exists
    existing = db.query(TriviaCategory).filter(
        (TriviaCategory.name == data.name) | (TriviaCategory.slug == slug)
    ).first()
    if existing:
        raise HTTPException(400, "Category already exists")

    category = TriviaCategory(
        name=data.name,
        slug=slug,
        description=data.description,
        icon=data.icon,
        created_by=user_id
    )

    db.add(category)
    db.commit()
    db.refresh(category)

    return CategoryResponse(
        id=category.id,
        name=category.name,
        slug=category.slug,
        description=category.description,
        icon=category.icon,
        is_active=category.is_active,
        question_count=0
    )


@router.patch("/categories/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: int,
    data: CategoryUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """Update a category"""
    if not is_admin(user_id, db):
        raise HTTPException(403, "Admin access required")

    category = db.query(TriviaCategory).filter(TriviaCategory.id == category_id).first()
    if not category:
        raise HTTPException(404, "Category not found")

    if data.name is not None:
        category.name = data.name
        category.slug = slugify(data.name)
    if data.description is not None:
        category.description = data.description
    if data.icon is not None:
        category.icon = data.icon
    if data.is_active is not None:
        category.is_active = data.is_active

    category.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(category)

    question_count = db.query(CustomTriviaQuestion).filter(
        CustomTriviaQuestion.category_id == category.id,
        CustomTriviaQuestion.is_active == True
    ).count()

    return CategoryResponse(
        id=category.id,
        name=category.name,
        slug=category.slug,
        description=category.description,
        icon=category.icon,
        is_active=category.is_active,
        question_count=question_count
    )


@router.delete("/categories/{category_id}")
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """Delete a category (only if it has no questions)"""
    if not is_admin(user_id, db):
        raise HTTPException(403, "Admin access required")

    category = db.query(TriviaCategory).filter(TriviaCategory.id == category_id).first()
    if not category:
        raise HTTPException(404, "Category not found")

    # Check if category has questions
    question_count = db.query(CustomTriviaQuestion).filter(
        CustomTriviaQuestion.category_id == category_id
    ).count()

    if question_count > 0:
        raise HTTPException(400, f"Cannot delete category with {question_count} questions. Delete questions first.")

    db.delete(category)
    db.commit()

    return {"message": "Category deleted"}


# Question Endpoints

@router.get("/questions", response_model=List[QuestionResponse])
def list_questions(
    category_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """List all custom questions, optionally filtered by category"""
    query = db.query(CustomTriviaQuestion)

    if category_id:
        query = query.filter(CustomTriviaQuestion.category_id == category_id)

    questions = query.order_by(desc(CustomTriviaQuestion.created_at)).all()

    return [QuestionResponse(
        id=q.id,
        category_id=q.category_id,
        question=q.question,
        option_a=q.option_a,
        option_b=q.option_b,
        option_c=q.option_c,
        option_d=q.option_d,
        correct_answer=q.correct_answer,
        explanation=q.explanation,
        difficulty=q.difficulty,
        is_active=q.is_active,
        times_used=q.times_used,
        times_correct=q.times_correct
    ) for q in questions]


@router.post("/questions", response_model=QuestionResponse)
def create_question(
    data: QuestionCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """Create a new custom trivia question"""
    if not is_admin(user_id, db):
        raise HTTPException(403, "Admin access required")

    # Validate correct_answer
    if data.correct_answer not in [0, 1, 2, 3]:
        raise HTTPException(400, "correct_answer must be 0, 1, 2, or 3")

    # Verify category exists
    category = db.query(TriviaCategory).filter(TriviaCategory.id == data.category_id).first()
    if not category:
        raise HTTPException(404, "Category not found")

    question = CustomTriviaQuestion(
        category_id=data.category_id,
        question=data.question,
        option_a=data.option_a,
        option_b=data.option_b,
        option_c=data.option_c,
        option_d=data.option_d,
        correct_answer=data.correct_answer,
        explanation=data.explanation,
        difficulty=data.difficulty,
        created_by=user_id
    )

    db.add(question)
    db.commit()
    db.refresh(question)

    return QuestionResponse(
        id=question.id,
        category_id=question.category_id,
        question=question.question,
        option_a=question.option_a,
        option_b=question.option_b,
        option_c=question.option_c,
        option_d=question.option_d,
        correct_answer=question.correct_answer,
        explanation=question.explanation,
        difficulty=question.difficulty,
        is_active=question.is_active,
        times_used=question.times_used,
        times_correct=question.times_correct
    )


@router.patch("/questions/{question_id}", response_model=QuestionResponse)
def update_question(
    question_id: int,
    data: QuestionUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """Update a question"""
    if not is_admin(user_id, db):
        raise HTTPException(403, "Admin access required")

    question = db.query(CustomTriviaQuestion).filter(CustomTriviaQuestion.id == question_id).first()
    if not question:
        raise HTTPException(404, "Question not found")

    if data.question is not None:
        question.question = data.question
    if data.option_a is not None:
        question.option_a = data.option_a
    if data.option_b is not None:
        question.option_b = data.option_b
    if data.option_c is not None:
        question.option_c = data.option_c
    if data.option_d is not None:
        question.option_d = data.option_d
    if data.correct_answer is not None:
        if data.correct_answer not in [0, 1, 2, 3]:
            raise HTTPException(400, "correct_answer must be 0, 1, 2, or 3")
        question.correct_answer = data.correct_answer
    if data.explanation is not None:
        question.explanation = data.explanation
    if data.difficulty is not None:
        question.difficulty = data.difficulty
    if data.is_active is not None:
        question.is_active = data.is_active

    question.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(question)

    return QuestionResponse(
        id=question.id,
        category_id=question.category_id,
        question=question.question,
        option_a=question.option_a,
        option_b=question.option_b,
        option_c=question.option_c,
        option_d=question.option_d,
        correct_answer=question.correct_answer,
        explanation=question.explanation,
        difficulty=question.difficulty,
        is_active=question.is_active,
        times_used=question.times_used,
        times_correct=question.times_correct
    )


@router.delete("/questions/{question_id}")
def delete_question(
    question_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """Delete a question"""
    if not is_admin(user_id, db):
        raise HTTPException(403, "Admin access required")

    question = db.query(CustomTriviaQuestion).filter(CustomTriviaQuestion.id == question_id).first()
    if not question:
        raise HTTPException(404, "Question not found")

    db.delete(question)
    db.commit()

    return {"message": "Question deleted"}
