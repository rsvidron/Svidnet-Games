"""
Admin API endpoints for managing categories and questions
"""
from fastapi import APIRouter, Depends, HTTPException, Header, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel
import re

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from models.admin import TriviaCategory, CustomTriviaQuestion, WordleWord
from models.user import User
from fastapi.responses import StreamingResponse
import io
import csv

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
    if not user:
        return False

    # Default admin users
    admin_usernames = ["svidthekid"]
    admin_emails = ["svidron.robert@gmail.com"]

    # Check if user is marked as admin OR is in the default admin list
    return (user.role == "admin" or
            user.username in admin_usernames or
            user.email in admin_emails)


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


# ==================== CSV IMPORT/EXPORT ====================

@router.get("/export/categories/template")
def export_categories_template():
    """Export empty CSV template for categories"""
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(["name", "description", "icon"])

    # Write example row
    writer.writerow(["Science", "Questions about scientific topics", "🔬"])
    writer.writerow(["History", "Questions about historical events", "📜"])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=categories_template.csv"}
    )


@router.get("/export/questions/template")
def export_questions_template():
    """Export empty CSV template for questions"""
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(["category_name", "question", "option_a", "option_b", "option_c", "option_d", "correct_answer", "explanation", "difficulty"])

    # Write example rows
    writer.writerow([
        "Science",
        "What is the chemical symbol for water?",
        "H2O",
        "CO2",
        "O2",
        "N2",
        "0",
        "Water is composed of two hydrogen atoms and one oxygen atom",
        "easy"
    ])
    writer.writerow([
        "History",
        "In what year did World War II end?",
        "1943",
        "1944",
        "1945",
        "1946",
        "2",
        "World War II ended in 1945 with the surrender of Japan",
        "medium"
    ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=questions_template.csv"}
    )


@router.get("/export/wordle-words/template")
def export_wordle_words_template():
    """Export empty CSV template for Wordle words"""
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(["word", "difficulty"])

    # Write example rows
    writer.writerow(["APPLE", "easy"])
    writer.writerow(["BRAVE", "medium"])
    writer.writerow(["SWIFT", "hard"])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=wordle_words_template.csv"}
    )


@router.post("/import/categories")
async def import_categories(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """Import categories from CSV"""
    if not is_admin(user_id, db):
        raise HTTPException(403, "Admin access required")

    try:
        content = (await file.read()).decode('utf-8')
        reader = csv.DictReader(io.StringIO(content))

        imported = 0
        errors = []

        for row_num, row in enumerate(reader, start=2):
            try:
                name = row.get('name', '').strip()
                if not name:
                    errors.append(f"Row {row_num}: Missing name")
                    continue

                # Check if category already exists
                existing = db.query(TriviaCategory).filter(TriviaCategory.name == name).first()
                if existing:
                    errors.append(f"Row {row_num}: Category '{name}' already exists")
                    continue

                category = TriviaCategory(
                    name=name,
                    slug=slugify(name),
                    description=row.get('description', '').strip() or None,
                    icon=row.get('icon', '').strip() or None,
                    created_by=user_id
                )
                db.add(category)
                imported += 1

            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")

        db.commit()

        return {
            "imported": imported,
            "errors": errors,
            "message": f"Successfully imported {imported} categories"
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(400, f"Failed to import CSV: {str(e)}")


@router.post("/import/questions")
async def import_questions(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """Import questions from CSV"""
    if not is_admin(user_id, db):
        raise HTTPException(403, "Admin access required")

    try:
        content = (await file.read()).decode('utf-8')
        reader = csv.DictReader(io.StringIO(content))

        imported = 0
        errors = []

        for row_num, row in enumerate(reader, start=2):
            try:
                category_name = row.get('category_name', '').strip()
                question_text = row.get('question', '').strip()

                if not category_name or not question_text:
                    errors.append(f"Row {row_num}: Missing category_name or question")
                    continue

                # Find category
                category = db.query(TriviaCategory).filter(TriviaCategory.name == category_name).first()
                if not category:
                    errors.append(f"Row {row_num}: Category '{category_name}' not found")
                    continue

                # Parse correct answer (0-3)
                try:
                    correct_answer = int(row.get('correct_answer', '0'))
                    if correct_answer not in [0, 1, 2, 3]:
                        raise ValueError("Must be 0-3")
                except ValueError:
                    errors.append(f"Row {row_num}: Invalid correct_answer (must be 0-3)")
                    continue

                question = CustomTriviaQuestion(
                    category_id=category.id,
                    question=question_text,
                    option_a=row.get('option_a', '').strip(),
                    option_b=row.get('option_b', '').strip(),
                    option_c=row.get('option_c', '').strip(),
                    option_d=row.get('option_d', '').strip(),
                    correct_answer=correct_answer,
                    explanation=row.get('explanation', '').strip() or None,
                    difficulty=row.get('difficulty', 'medium').strip(),
                    created_by=user_id
                )
                db.add(question)
                imported += 1

            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")

        db.commit()

        return {
            "imported": imported,
            "errors": errors,
            "message": f"Successfully imported {imported} questions"
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(400, f"Failed to import CSV: {str(e)}")


@router.post("/import/wordle-words")
async def import_wordle_words(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """Import Wordle words from CSV"""
    if not is_admin(user_id, db):
        raise HTTPException(403, "Admin access required")

    try:
        content = (await file.read()).decode('utf-8')
        reader = csv.DictReader(io.StringIO(content))

        imported = 0
        errors = []

        for row_num, row in enumerate(reader, start=2):
            try:
                word = row.get('word', '').strip().upper()

                if not word:
                    errors.append(f"Row {row_num}: Missing word")
                    continue

                if len(word) != 5:
                    errors.append(f"Row {row_num}: Word must be exactly 5 letters")
                    continue

                if not word.isalpha():
                    errors.append(f"Row {row_num}: Word must contain only letters")
                    continue

                # Check if word already exists
                existing = db.query(WordleWord).filter(WordleWord.word == word).first()
                if existing:
                    errors.append(f"Row {row_num}: Word '{word}' already exists")
                    continue

                wordle_word = WordleWord(
                    word=word,
                    difficulty=row.get('difficulty', 'medium').strip(),
                    created_by=user_id
                )
                db.add(wordle_word)
                imported += 1

            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")

        db.commit()

        return {
            "imported": imported,
            "errors": errors,
            "message": f"Successfully imported {imported} words"
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(400, f"Failed to import CSV: {str(e)}")


# ==================== WORDLE WORDS MANAGEMENT ====================

class WordleWordResponse(BaseModel):
    id: int
    word: str
    difficulty: str
    is_active: bool
    times_used: int
    created_at: str


class WordleWordCreate(BaseModel):
    word: str
    difficulty: str = "medium"


class WordleWordUpdate(BaseModel):
    difficulty: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("/wordle-words")
def get_wordle_words(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """Get all Wordle words"""
    if not is_admin(user_id, db):
        raise HTTPException(403, "Admin access required")

    words = db.query(WordleWord).order_by(WordleWord.word).all()

    return [
        WordleWordResponse(
            id=word.id,
            word=word.word,
            difficulty=word.difficulty,
            is_active=word.is_active,
            times_used=word.times_used,
            created_at=word.created_at.isoformat() if word.created_at else ""
        )
        for word in words
    ]


@router.post("/wordle-words")
def create_wordle_word(
    data: WordleWordCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """Create a new Wordle word"""
    if not is_admin(user_id, db):
        raise HTTPException(403, "Admin access required")

    word = data.word.strip().upper()

    if len(word) != 5:
        raise HTTPException(400, "Word must be exactly 5 letters")

    if not word.isalpha():
        raise HTTPException(400, "Word must contain only letters")

    # Check if word already exists
    existing = db.query(WordleWord).filter(WordleWord.word == word).first()
    if existing:
        raise HTTPException(400, f"Word '{word}' already exists")

    wordle_word = WordleWord(
        word=word,
        difficulty=data.difficulty,
        created_by=user_id
    )
    db.add(wordle_word)
    db.commit()
    db.refresh(wordle_word)

    return WordleWordResponse(
        id=wordle_word.id,
        word=wordle_word.word,
        difficulty=wordle_word.difficulty,
        is_active=wordle_word.is_active,
        times_used=wordle_word.times_used,
        created_at=wordle_word.created_at.isoformat() if wordle_word.created_at else ""
    )


@router.patch("/wordle-words/{word_id}")
def update_wordle_word(
    word_id: int,
    data: WordleWordUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """Update a Wordle word"""
    if not is_admin(user_id, db):
        raise HTTPException(403, "Admin access required")

    word = db.query(WordleWord).filter(WordleWord.id == word_id).first()
    if not word:
        raise HTTPException(404, "Word not found")

    if data.difficulty is not None:
        word.difficulty = data.difficulty
    if data.is_active is not None:
        word.is_active = data.is_active

    db.commit()
    db.refresh(word)

    return WordleWordResponse(
        id=word.id,
        word=word.word,
        difficulty=word.difficulty,
        is_active=word.is_active,
        times_used=word.times_used,
        created_at=word.created_at.isoformat() if word.created_at else ""
    )


@router.delete("/wordle-words/{word_id}")
def delete_wordle_word(
    word_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """Delete a Wordle word"""
    if not is_admin(user_id, db):
        raise HTTPException(403, "Admin access required")

    word = db.query(WordleWord).filter(WordleWord.id == word_id).first()
    if not word:
        raise HTTPException(404, "Word not found")

    db.delete(word)
    db.commit()

    return {"message": "Word deleted"}
