"""Same-origin, capability-based personal workspaces, independent of demo ingestion."""

from __future__ import annotations

import hashlib
import secrets
import threading
import time
import uuid
from collections import OrderedDict
from datetime import date, datetime, timedelta, timezone
from typing import Literal
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from safetyops.core.settings import settings
from safetyops.db.session import get_session
from safetyops.db.workspace import CorrectiveAction, Observation, Workspace
from safetyops.domain.assessment import assess_observation

router = APIRouter(prefix="/api/workspace", tags=["Personal workspace"])
COOKIE = "safetyops_workspace"
_lock = threading.Lock()
_windows: OrderedDict = OrderedDict()


def same_origin(request: Request) -> None:
    if request.method in {"GET", "HEAD"}:
        return
    origin = request.headers.get("origin")
    if request.headers.get("sec-fetch-site") == "cross-site" or (
        origin and urlsplit(origin).netloc != request.headers.get("host")
    ):
        raise HTTPException(403, "Use this action from the SafetyOps website")
    # Bound memory and rate-limit by the direct network peer, never untrusted headers.
    peer = request.client.host if request.client else "unknown"
    now = time.monotonic()
    with _lock:
        hits = [t for t in _windows.pop(peer, []) if now - t < 60]
        if len(hits) >= 40:
            _windows[peer] = hits
            raise HTTPException(429, "Too many changes. Wait one minute and try again.")
        hits.append(now)
        _windows[peer] = hits
        if len(_windows) > 10000:
            _windows.popitem(last=False)


def session_dependency():
    with get_session() as session:
        yield session


def workspace_id(request: Request, session: Session = Depends(session_dependency)) -> str:
    token = request.cookies.get(COOKIE, "")
    if not 32 <= len(token) <= 128:
        raise HTTPException(401, "Create a workspace in this browser first")
    digest = hashlib.sha256(token.encode()).hexdigest()
    row = session.scalar(select(Workspace).where(Workspace.credential_hash == digest))
    if not row:
        raise HTTPException(401, "Workspace session expired. Create a new workspace.")
    return row.id


class ObservationInput(BaseModel):
    text: str = Field(min_length=12, max_length=5000)
    location: str = Field(default="Main site", min_length=1, max_length=160)

    @field_validator("text", "location", mode="before")
    @classmethod
    def strip_text(cls, value):
        return value.strip() if isinstance(value, str) else value


class ActionInput(BaseModel):
    observation_id: str = Field(max_length=64)
    title: str = Field(min_length=3, max_length=300)
    owner: str = Field(min_length=2, max_length=120)
    due_date: date

    @field_validator("title", "owner", mode="before")
    @classmethod
    def strip_text(cls, value):
        return value.strip() if isinstance(value, str) else value


class ActionUpdate(BaseModel):
    status: Literal["open", "in_progress", "closed"]
    closure_note: str = Field(default="", max_length=2000)
    revision: int = Field(ge=1)


def action_dict(row: CorrectiveAction) -> dict:
    return {
        key: getattr(row, key)
        for key in (
            "id",
            "observation_id",
            "title",
            "owner",
            "due_date",
            "status",
            "closure_note",
            "revision",
            "history",
            "created_at",
        )
    }


def observation_dict(row: Observation) -> dict:
    return {
        key: getattr(row, key) for key in ("id", "text", "location", "assessment", "created_at")
    }


@router.post("", dependencies=[Depends(same_origin)])
def create_workspace(
    request: Request, response: Response, session: Session = Depends(session_dependency)
):
    existing = request.cookies.get(COOKIE, "")
    digest = hashlib.sha256(existing.encode()).hexdigest()
    row = (
        session.scalar(select(Workspace).where(Workspace.credential_hash == digest))
        if existing
        else None
    )
    if row:
        return {"id": row.id}
    token = secrets.token_urlsafe(32)
    row = Workspace(id=uuid.uuid4().hex, credential_hash=hashlib.sha256(token.encode()).hexdigest())
    session.add(row)
    session.flush()
    response.set_cookie(
        COOKIE,
        token,
        httponly=True,
        secure=settings.deploy_mode == "cloud" or request.url.scheme == "https",
        samesite="strict",
        max_age=31536000,
        path="/",
    )
    return {"id": row.id}


@router.get("")
def get_workspace(wid: str = Depends(workspace_id), session: Session = Depends(session_dependency)):
    observations = session.scalars(
        select(Observation)
        .where(Observation.workspace_id == wid)
        .order_by(Observation.created_at.desc())
    ).all()
    actions = session.scalars(
        select(CorrectiveAction)
        .where(CorrectiveAction.workspace_id == wid)
        .order_by(CorrectiveAction.due_date)
    ).all()
    return {
        "id": wid,
        "observations": [observation_dict(x) for x in observations],
        "actions": [action_dict(x) for x in actions],
    }


@router.post("/observations", dependencies=[Depends(same_origin)], status_code=201)
def add_observation(
    body: ObservationInput,
    wid: str = Depends(workspace_id),
    session: Session = Depends(session_dependency),
):
    count = session.scalar(
        select(func.count()).select_from(Observation).where(Observation.workspace_id == wid)
    )
    if count >= 500:
        raise HTTPException(
            409, "Workspace limit reached (500 observations). Export your handover first."
        )
    assessment = assess_observation(body.text, allow_model_loading=False)
    since = datetime.now(timezone.utc) - timedelta(days=7)
    previous = session.scalars(
        select(Observation).where(Observation.workspace_id == wid, Observation.created_at >= since)
    ).all()
    recurrence = sum(x.assessment.get("category") == assessment["category"] for x in previous)
    boost = min(15, recurrence * 3)
    assessment["risk_score"] += boost
    assessment["score_breakdown"].update(
        recurrence_points=boost, related_observations_7d=recurrence
    )
    row = Observation(
        id=uuid.uuid4().hex,
        workspace_id=wid,
        text=body.text,
        location=body.location,
        assessment=assessment,
    )
    session.add(row)
    session.flush()
    return observation_dict(row)


@router.post("/actions", dependencies=[Depends(same_origin)], status_code=201)
def add_action(
    body: ActionInput,
    wid: str = Depends(workspace_id),
    session: Session = Depends(session_dependency),
):
    incident = session.scalar(
        select(Observation).where(
            Observation.id == body.observation_id, Observation.workspace_id == wid
        )
    )
    if not incident:
        raise HTTPException(404, "Observation not found in this workspace")
    count = session.scalar(
        select(func.count())
        .select_from(CorrectiveAction)
        .where(CorrectiveAction.workspace_id == wid)
    )
    if count >= 1000:
        raise HTTPException(409, "Workspace action limit reached (1000)")
    row = CorrectiveAction(
        id=uuid.uuid4().hex,
        workspace_id=wid,
        **body.model_dump(exclude={"due_date"}),
        due_date=body.due_date.isoformat(),
        history=[{"status": "open", "at": datetime.now(timezone.utc).isoformat()}],
    )
    session.add(row)
    session.flush()
    return action_dict(row)


@router.patch("/actions/{action_id}", dependencies=[Depends(same_origin)])
def change_action(
    action_id: str,
    body: ActionUpdate,
    wid: str = Depends(workspace_id),
    session: Session = Depends(session_dependency),
):
    row = session.scalar(
        select(CorrectiveAction).where(
            CorrectiveAction.id == action_id, CorrectiveAction.workspace_id == wid
        )
    )
    if not row:
        raise HTTPException(404, "Action not found in this workspace")
    if body.status == "closed" and len(body.closure_note.strip()) < 8:
        raise HTTPException(422, "Add closure evidence (at least 8 characters)")
    history = [
        *row.history,
        {
            "status": body.status,
            "note": body.closure_note.strip(),
            "at": datetime.now(timezone.utc).isoformat(),
        },
    ]
    result = session.execute(
        update(CorrectiveAction)
        .where(
            CorrectiveAction.id == action_id,
            CorrectiveAction.workspace_id == wid,
            CorrectiveAction.revision == body.revision,
        )
        .values(
            status=body.status,
            closure_note=body.closure_note.strip(),
            revision=body.revision + 1,
            history=history,
        )
    )
    if result.rowcount != 1:
        raise HTTPException(409, "This action changed in another tab. Refresh and try again.")
    session.flush()
    session.refresh(row)
    return action_dict(row)


@router.delete("", dependencies=[Depends(same_origin)], status_code=204)
def delete_workspace(
    response: Response,
    wid: str = Depends(workspace_id),
    session: Session = Depends(session_dependency),
):
    for model in (CorrectiveAction, Observation, Workspace):
        key = model.id if model is Workspace else model.workspace_id
        session.execute(delete(model).where(key == wid))
    response.delete_cookie(COOKIE, path="/")
