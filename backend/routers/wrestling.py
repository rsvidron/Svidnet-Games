"""
Wrestling Predictions API
"""
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone
from typing import Optional, List, Any
from pydantic import BaseModel
from jose import jwt, JWTError
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from models.wrestling import WrestlingEvent, WrestlingQuestion, WrestlingSubmission, WrestlingAnswer
from models.user import User

router = APIRouter(prefix="/api/wrestling", tags=["wrestling"])

SECRET_KEY = os.getenv("SECRET_KEY", "test-secret-key-for-development")
ALGORITHM  = "HS256"

ADMIN_USERNAMES = ["svidthekid"]
ADMIN_EMAILS    = ["svidron.robert@gmail.com"]


# ── DB ────────────────────────────────────────────────────────────────────────

def get_db():
    from database import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Auth helpers ──────────────────────────────────────────────────────────────

def get_current_user_id(authorization: Optional[str] = Header(None)) -> Optional[int]:
    if not authorization:
        return None
    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        uid = payload.get("sub") or payload.get("user_id")
        return int(uid) if uid else None
    except JWTError:
        return None


def require_user(authorization: Optional[str] = Header(None)) -> int:
    uid = get_current_user_id(authorization)
    if not uid:
        raise HTTPException(401, "Authentication required")
    return uid


def require_admin(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)) -> int:
    uid = require_user(authorization)
    user = db.query(User).filter(User.id == uid).first()
    if not user:
        raise HTTPException(401, "User not found")
    if (user.role == "admin" or user.username in ADMIN_USERNAMES or user.email in ADMIN_EMAILS):
        return uid
    raise HTTPException(403, "Admin access required")


# ── Schemas ───────────────────────────────────────────────────────────────────

class QuestionIn(BaseModel):
    question_text: str
    question_type: str          # short_answer | multiple_choice | dropdown | checkbox
    options: Optional[List[str]] = None
    counts_for_score: bool = True
    sort_order: int = 0


class QuestionUpdate(BaseModel):
    question_text: Optional[str] = None
    question_type: Optional[str] = None
    options: Optional[List[str]] = None
    counts_for_score: Optional[bool] = None
    sort_order: Optional[int] = None
    correct_answer: Optional[Any] = None


class EventIn(BaseModel):
    title: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    event_date: Optional[str] = None   # ISO string


class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    event_date: Optional[str] = None
    is_locked: Optional[bool] = None


class AnswerIn(BaseModel):
    question_id: int
    answer_value: Any           # str or list[str]


class SubmissionIn(BaseModel):
    answers: List[AnswerIn]


class GradeAnswerIn(BaseModel):
    question_id: int
    correct_answer: Any         # str or list[str]
    partial_points: Optional[float] = None  # override per-answer if needed


class GradeEventIn(BaseModel):
    answers: List[GradeAnswerIn]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _grade_answer(question: WrestlingQuestion, user_value: Any) -> tuple[bool, float]:
    """Returns (is_correct, points_earned). points_earned is 0 or 1 (or partial for checkbox)."""
    if not question.counts_for_score or question.correct_answer is None:
        return None, 0.0

    qt = question.question_type
    correct = question.correct_answer

    if qt in ("short_answer", "multiple_choice", "dropdown"):
        is_correct = str(user_value or "").strip().lower() == str(correct or "").strip().lower()
        return is_correct, 1.0 if is_correct else 0.0

    if qt == "checkbox":
        # correct is a list; user_value is a list
        correct_set = set(str(x).strip().lower() for x in (correct or []))
        user_set    = set(str(x).strip().lower() for x in (user_value or []))
        if not correct_set:
            return None, 0.0
        matched = len(correct_set & user_set)
        total   = len(correct_set)
        pts     = round(matched / total, 4)
        return pts >= 1.0, pts

    return None, 0.0


def _event_dict(event: WrestlingEvent, include_questions: bool = False) -> dict:
    d = {
        "id":          event.id,
        "title":       event.title,
        "description": event.description,
        "image_url":   event.image_url,
        "event_date":  event.event_date.isoformat() if event.event_date else None,
        "is_locked":   event.is_locked,
        "is_graded":   event.is_graded,
        "created_at":  event.created_at.isoformat() if event.created_at else None,
        "question_count": len(event.questions),
    }
    if include_questions:
        d["questions"] = [_question_dict(q) for q in event.questions]
    return d


def _question_dict(q: WrestlingQuestion, include_answer: bool = False) -> dict:
    d = {
        "id":               q.id,
        "event_id":         q.event_id,
        "question_text":    q.question_text,
        "question_type":    q.question_type,
        "options":          q.options,
        "counts_for_score": q.counts_for_score,
        "sort_order":       q.sort_order,
    }
    if include_answer:
        d["correct_answer"] = q.correct_answer
    return d


# ── Admin: Events ─────────────────────────────────────────────────────────────

@router.post("/events", status_code=201)
def create_event(data: EventIn, db: Session = Depends(get_db), admin_id: int = Depends(require_admin)):
    ev = WrestlingEvent(
        title       = data.title,
        description = data.description,
        image_url   = data.image_url,
        event_date  = datetime.fromisoformat(data.event_date) if data.event_date else None,
    )
    db.add(ev); db.commit(); db.refresh(ev)
    return _event_dict(ev, include_questions=True)


@router.patch("/events/{event_id}")
def update_event(event_id: int, data: EventUpdate, db: Session = Depends(get_db), admin_id: int = Depends(require_admin)):
    ev = db.query(WrestlingEvent).filter(WrestlingEvent.id == event_id).first()
    if not ev: raise HTTPException(404, "Event not found")
    if data.title       is not None: ev.title       = data.title
    if data.description is not None: ev.description = data.description
    if data.image_url   is not None: ev.image_url   = data.image_url
    if data.is_locked   is not None: ev.is_locked   = data.is_locked
    if data.event_date  is not None:
        ev.event_date = datetime.fromisoformat(data.event_date) if data.event_date else None
    db.commit(); db.refresh(ev)
    return _event_dict(ev, include_questions=True)


@router.delete("/events/{event_id}", status_code=204)
def delete_event(event_id: int, db: Session = Depends(get_db), admin_id: int = Depends(require_admin)):
    ev = db.query(WrestlingEvent).filter(WrestlingEvent.id == event_id).first()
    if not ev: raise HTTPException(404, "Event not found")
    db.delete(ev); db.commit()


# ── Admin: Questions ──────────────────────────────────────────────────────────

@router.post("/events/{event_id}/questions", status_code=201)
def add_question(event_id: int, data: QuestionIn, db: Session = Depends(get_db), admin_id: int = Depends(require_admin)):
    ev = db.query(WrestlingEvent).filter(WrestlingEvent.id == event_id).first()
    if not ev: raise HTTPException(404, "Event not found")
    q = WrestlingQuestion(
        event_id         = event_id,
        question_text    = data.question_text,
        question_type    = data.question_type,
        options          = data.options,
        counts_for_score = data.counts_for_score,
        sort_order       = data.sort_order,
    )
    db.add(q); db.commit(); db.refresh(q)
    return _question_dict(q, include_answer=True)


@router.patch("/questions/{question_id}")
def update_question(question_id: int, data: QuestionUpdate, db: Session = Depends(get_db), admin_id: int = Depends(require_admin)):
    q = db.query(WrestlingQuestion).filter(WrestlingQuestion.id == question_id).first()
    if not q: raise HTTPException(404, "Question not found")
    if data.question_text    is not None: q.question_text    = data.question_text
    if data.question_type    is not None: q.question_type    = data.question_type
    if data.options          is not None: q.options          = data.options
    if data.counts_for_score is not None: q.counts_for_score = data.counts_for_score
    if data.sort_order       is not None: q.sort_order       = data.sort_order
    if data.correct_answer   is not None: q.correct_answer   = data.correct_answer
    db.commit(); db.refresh(q)
    return _question_dict(q, include_answer=True)


@router.delete("/questions/{question_id}", status_code=204)
def delete_question(question_id: int, db: Session = Depends(get_db), admin_id: int = Depends(require_admin)):
    q = db.query(WrestlingQuestion).filter(WrestlingQuestion.id == question_id).first()
    if not q: raise HTTPException(404, "Question not found")
    db.delete(q); db.commit()


# ── Admin: Grade event ────────────────────────────────────────────────────────

@router.post("/events/{event_id}/grade")
def grade_event(event_id: int, data: GradeEventIn, db: Session = Depends(get_db), admin_id: int = Depends(require_admin)):
    """
    Submit correct answers for all (or some) questions.
    Automatically scores every existing submission.
    """
    ev = db.query(WrestlingEvent).filter(WrestlingEvent.id == event_id).first()
    if not ev: raise HTTPException(404, "Event not found")

    # Save correct answers to questions
    answer_map = {ga.question_id: ga for ga in data.answers}
    questions  = db.query(WrestlingQuestion).filter(WrestlingQuestion.event_id == event_id).all()
    for q in questions:
        if q.id in answer_map:
            q.correct_answer = answer_map[q.id].correct_answer
    db.commit()

    # Re-grade all submissions
    submissions = db.query(WrestlingSubmission).filter(WrestlingSubmission.event_id == event_id).all()
    scoreable   = [q for q in questions if q.counts_for_score]
    max_score   = float(len(scoreable))

    for sub in submissions:
        total_pts = 0.0
        for ans in sub.answers:
            q = next((x for x in questions if x.id == ans.question_id), None)
            if not q:
                continue
            # Allow admin partial override
            ga = answer_map.get(ans.question_id)
            if ga and ga.partial_points is not None:
                pts = ga.partial_points
                ans.is_correct   = pts >= 1.0
                ans.points_earned = pts
            else:
                is_correct, pts = _grade_answer(q, ans.answer_value)
                ans.is_correct   = is_correct
                ans.points_earned = pts
            total_pts += pts
        sub.score     = round(total_pts, 2)
        sub.max_score = max_score

    ev.is_graded = True
    ev.is_locked = True
    db.commit()
    return {"message": f"Graded {len(submissions)} submissions", "max_score": max_score}


# ── Admin: All submissions for an event ──────────────────────────────────────

@router.get("/events/{event_id}/submissions")
def list_submissions(event_id: int, db: Session = Depends(get_db), admin_id: int = Depends(require_admin)):
    ev = db.query(WrestlingEvent).filter(WrestlingEvent.id == event_id).first()
    if not ev: raise HTTPException(404, "Event not found")
    subs = db.query(WrestlingSubmission).filter(WrestlingSubmission.event_id == event_id).all()
    result = []
    for sub in subs:
        user = db.query(User).filter(User.id == sub.user_id).first()
        result.append({
            "submission_id": sub.id,
            "user_id":       sub.user_id,
            "username":      user.username if user else "Unknown",
            "avatar_url":    user.avatar_url if user else None,
            "submitted_at":  sub.submitted_at.isoformat() if sub.submitted_at else None,
            "score":         sub.score,
            "max_score":     sub.max_score,
        })
    result.sort(key=lambda x: (x["score"] or 0), reverse=True)
    return result


# ── Public: List events ───────────────────────────────────────────────────────

@router.get("/events")
def list_events(db: Session = Depends(get_db), user_id: Optional[int] = Depends(get_current_user_id)):
    events = db.query(WrestlingEvent).order_by(WrestlingEvent.id.desc()).all()
    result = []
    for ev in events:
        d = _event_dict(ev)
        # has current user submitted?
        if user_id:
            sub = db.query(WrestlingSubmission).filter(
                WrestlingSubmission.event_id == ev.id,
                WrestlingSubmission.user_id  == user_id
            ).first()
            d["user_submitted"] = sub is not None
            d["user_score"]     = sub.score if sub else None
        else:
            d["user_submitted"] = False
            d["user_score"]     = None
        result.append(d)
    return result


@router.get("/events/{event_id}")
def get_event(event_id: int, db: Session = Depends(get_db), user_id: Optional[int] = Depends(get_current_user_id)):
    ev = db.query(WrestlingEvent).filter(WrestlingEvent.id == event_id).first()
    if not ev: raise HTTPException(404, "Event not found")

    # Check if requester is admin — admins see correct answers
    is_admin_user = False
    if user_id:
        user = db.query(User).filter(User.id == user_id).first()
        if user and (user.role == "admin" or user.username in ADMIN_USERNAMES or user.email in ADMIN_EMAILS):
            is_admin_user = True

    d = _event_dict(ev)
    d["questions"] = [_question_dict(q, include_answer=is_admin_user) for q in ev.questions]

    # Attach user's existing submission if any
    if user_id:
        sub = db.query(WrestlingSubmission).filter(
            WrestlingSubmission.event_id == ev.id,
            WrestlingSubmission.user_id  == user_id
        ).first()
        if sub:
            d["user_submission"] = {
                "id":           sub.id,
                "submitted_at": sub.submitted_at.isoformat() if sub.submitted_at else None,
                "score":        sub.score,
                "max_score":    sub.max_score,
                "answers": {
                    a.question_id: {
                        "answer_value":  a.answer_value,
                        "is_correct":    a.is_correct,
                        "points_earned": a.points_earned,
                    } for a in sub.answers
                }
            }
        else:
            d["user_submission"] = None
    return d


# ── Public: Submit predictions ────────────────────────────────────────────────

@router.post("/events/{event_id}/submit")
def submit_predictions(event_id: int, data: SubmissionIn, db: Session = Depends(get_db), user_id: int = Depends(require_user)):
    ev = db.query(WrestlingEvent).filter(WrestlingEvent.id == event_id).first()
    if not ev: raise HTTPException(404, "Event not found")
    if ev.is_locked: raise HTTPException(400, "Predictions are locked for this event")

    # Upsert submission
    sub = db.query(WrestlingSubmission).filter(
        WrestlingSubmission.event_id == ev.id,
        WrestlingSubmission.user_id  == user_id
    ).first()
    if not sub:
        sub = WrestlingSubmission(event_id=event_id, user_id=user_id)
        db.add(sub)
        db.flush()
    else:
        # Delete old answers so we can re-insert
        for ans in sub.answers:
            db.delete(ans)
        db.flush()

    sub.submitted_at = datetime.now(timezone.utc)
    sub.score     = None
    sub.max_score = None

    for a in data.answers:
        db.add(WrestlingAnswer(
            submission_id = sub.id,
            question_id   = a.question_id,
            answer_value  = a.answer_value,
        ))
    db.commit()
    return {"message": "Predictions submitted", "submission_id": sub.id}


# ── Public: Leaderboards ──────────────────────────────────────────────────────

@router.get("/leaderboard/overall")
def overall_leaderboard(db: Session = Depends(get_db)):
    """All-time cumulative points across all graded events."""
    rows = (
        db.query(
            WrestlingSubmission.user_id,
            func.sum(WrestlingSubmission.score).label("total_pts"),
            func.sum(WrestlingSubmission.max_score).label("total_max"),
            func.count(WrestlingSubmission.id).label("events_played"),
        )
        .filter(WrestlingSubmission.score.isnot(None))
        .group_by(WrestlingSubmission.user_id)
        .order_by(func.sum(WrestlingSubmission.score).desc())
        .all()
    )
    result = []
    for row in rows:
        user = db.query(User).filter(User.id == row.user_id).first()
        pct  = round((row.total_pts / row.total_max) * 100, 1) if row.total_max else 0
        result.append({
            "user_id":      row.user_id,
            "username":     user.username if user else "Unknown",
            "avatar_url":   user.avatar_url if user else None,
            "total_pts":    round(row.total_pts, 2),
            "total_max":    round(row.total_max, 2),
            "pct":          pct,
            "events_played": row.events_played,
        })
    return result


@router.get("/leaderboard/event/{event_id}")
def event_leaderboard(event_id: int, db: Session = Depends(get_db)):
    """Leaderboard for a single event."""
    ev = db.query(WrestlingEvent).filter(WrestlingEvent.id == event_id).first()
    if not ev: raise HTTPException(404, "Event not found")
    subs = (
        db.query(WrestlingSubmission)
        .filter(WrestlingSubmission.event_id == event_id,
                WrestlingSubmission.score.isnot(None))
        .order_by(WrestlingSubmission.score.desc())
        .all()
    )
    result = []
    for sub in subs:
        user = db.query(User).filter(User.id == sub.user_id).first()
        pct  = round((sub.score / sub.max_score) * 100, 1) if sub.max_score else 0
        result.append({
            "user_id":    sub.user_id,
            "username":   user.username if user else "Unknown",
            "avatar_url": user.avatar_url if user else None,
            "score":      sub.score,
            "max_score":  sub.max_score,
            "pct":        pct,
        })
    return result


# ── Public: User stats ────────────────────────────────────────────────────────

@router.get("/stats/{target_user_id}")
def user_stats(target_user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == target_user_id).first()
    if not user: raise HTTPException(404, "User not found")

    subs = (
        db.query(WrestlingSubmission)
        .filter(WrestlingSubmission.user_id == target_user_id)
        .all()
    )
    graded = [s for s in subs if s.score is not None]
    total_pts = sum(s.score for s in graded)
    total_max = sum(s.max_score for s in graded if s.max_score)

    per_event = []
    for sub in subs:
        ev = db.query(WrestlingEvent).filter(WrestlingEvent.id == sub.event_id).first()
        pct = round((sub.score / sub.max_score) * 100, 1) if (sub.score is not None and sub.max_score) else None
        per_event.append({
            "event_id":    sub.event_id,
            "event_title": ev.title if ev else "Unknown",
            "event_date":  ev.event_date.isoformat() if ev and ev.event_date else None,
            "score":       sub.score,
            "max_score":   sub.max_score,
            "pct":         pct,
            "submitted_at": sub.submitted_at.isoformat() if sub.submitted_at else None,
        })
    per_event.sort(key=lambda x: x["event_id"], reverse=True)

    overall_pct = round((total_pts / total_max) * 100, 1) if total_max else 0

    return {
        "user_id":       target_user_id,
        "username":      user.username,
        "avatar_url":    user.avatar_url,
        "events_played": len(subs),
        "events_graded": len(graded),
        "total_pts":     round(total_pts, 2),
        "total_max":     round(total_max, 2),
        "overall_pct":   overall_pct,
        "per_event":     per_event,
    }


@router.get("/stats/me/summary")
def my_stats(db: Session = Depends(get_db), user_id: int = Depends(require_user)):
    return user_stats(user_id, db)


# ── Public: Head-to-head ──────────────────────────────────────────────────────

@router.get("/h2h/{user_a_id}/{user_b_id}")
def head_to_head(user_a_id: int, user_b_id: int, db: Session = Depends(get_db)):
    user_a = db.query(User).filter(User.id == user_a_id).first()
    user_b = db.query(User).filter(User.id == user_b_id).first()
    if not user_a or not user_b: raise HTTPException(404, "User not found")

    # Events both participated in
    subs_a = {s.event_id: s for s in db.query(WrestlingSubmission).filter(WrestlingSubmission.user_id == user_a_id).all()}
    subs_b = {s.event_id: s for s in db.query(WrestlingSubmission).filter(WrestlingSubmission.user_id == user_b_id).all()}
    shared = set(subs_a.keys()) & set(subs_b.keys())

    wins_a = wins_b = ties = 0
    events = []
    for eid in sorted(shared, reverse=True):
        sa = subs_a[eid]; sb = subs_b[eid]
        ev = db.query(WrestlingEvent).filter(WrestlingEvent.id == eid).first()
        graded = sa.score is not None and sb.score is not None
        winner = None
        if graded:
            if sa.score > sb.score:   wins_a += 1; winner = user_a_id
            elif sb.score > sa.score: wins_b += 1; winner = user_b_id
            else:                     ties   += 1
        events.append({
            "event_id":    eid,
            "event_title": ev.title if ev else "Unknown",
            "event_date":  ev.event_date.isoformat() if ev and ev.event_date else None,
            "graded":      graded,
            "score_a":     sa.score,
            "score_b":     sb.score,
            "max_score":   sa.max_score,
            "winner":      winner,
        })

    return {
        "user_a": {"id": user_a_id, "username": user_a.username, "avatar_url": user_a.avatar_url},
        "user_b": {"id": user_b_id, "username": user_b.username, "avatar_url": user_b.avatar_url},
        "shared_events": len(shared),
        "wins_a": wins_a,
        "wins_b": wins_b,
        "ties":   ties,
        "events": events,
    }
