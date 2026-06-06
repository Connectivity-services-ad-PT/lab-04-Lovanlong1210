import os
import http.client
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


SERVICE_NAME = os.getenv("SERVICE_NAME", "analytics-service")
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "0.4.0")
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "local-dev-token")


app = FastAPI(
    title="FIT4110 Lab 04 - Analytics Service (A5)",
    version=SERVICE_VERSION,
    description="Dockerized Analytics API aligned with the Lab 03 OpenAPI/Postman contract.",
)


class AlertSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertStatus(str, Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


class ProblemDetails(BaseModel):
    type: str = "about:blank"
    title: str
    status: int = Field(..., ge=400, le=599)
    detail: str
    instance: Optional[str] = None
    errors: Optional[List[Dict]] = []


class HealthStatus(BaseModel):
    status: str
    service: str
    time: str


class CreateAlertRequest(BaseModel):
    sourceService: str = Field(..., min_length=2, max_length=80, pattern="^[a-z0-9-]+$")
    alertType: str = Field(..., description="UNAUTHORIZED_ACCESS, SENSOR_THRESHOLD_EXCEEDED, etc.")
    severity: AlertSeverity
    message: str = Field(..., min_length=5, max_length=500)
    relatedEventId: Optional[str] = None


class Alert(BaseModel):
    id: str
    sourceService: str
    alertType: str
    severity: AlertSeverity
    message: str
    relatedEventId: Optional[str] = None
    status: AlertStatus
    createdAt: str
    resolvedAt: Optional[str] = None


class AlertPage(BaseModel):
    items: List[Alert]
    nextCursor: Optional[str] = None
    hasMore: bool


class EventAccepted(BaseModel):
    eventId: str
    acceptedAt: str


# In-memory mock database
ALERTS: List[Dict] = []
EVENTS: List[Dict] = []


def build_problem(
    *,
    status_code: int,
    title: str,
    detail: str,
    instance: Optional[str] = None,
    problem_type: str = "about:blank",
    errors: List[Dict] = None,
) -> Dict:
    problem = {
        "type": problem_type,
        "title": title,
        "status": status_code,
        "detail": detail,
    }
    if instance:
        problem["instance"] = instance
    if errors is not None:
        problem["errors"] = errors
    return problem


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict):
        problem = exc.detail
    else:
        problem = build_problem(
            status_code=exc.status_code,
            title=http.client.responses.get(exc.status_code, "HTTP Error"),
            detail=str(exc.detail),
            instance=str(request.url.path),
        )

    problem.setdefault("status", exc.status_code)
    problem.setdefault("title", http.client.responses.get(exc.status_code, "HTTP Error"))
    problem.setdefault("type", "about:blank")
    problem.setdefault("detail", "Request failed")
    problem.setdefault("instance", str(request.url.path))
    problem.setdefault("errors", [])

    return JSONResponse(
        status_code=exc.status_code,
        content=problem,
        media_type="application/problem+json",
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = []
    for error in exc.errors():
        location = ".".join(str(item) for item in error.get("loc", []))
        errors.append({
            "field": location,
            "code": error.get("type", "validation_error"),
            "message": error.get("msg", "Invalid value")
        })

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=build_problem(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            title="Validation error",
            detail="Payload validation failed",
            instance=str(request.url.path),
            problem_type="https://campus.local/errors/validation",
            errors=errors,
        ),
        media_type="application/problem+json",
    )


def verify_bearer_token(authorization: Optional[str] = Header(default=None)) -> None:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=build_problem(
                status_code=status.HTTP_401_UNAUTHORIZED,
                title="Unauthorized",
                detail="Missing Authorization header",
                problem_type="https://campus.local/errors/unauthorized",
                errors=[],
            ),
        )

    expected = f"Bearer {AUTH_TOKEN}"
    if authorization != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=build_problem(
                status_code=status.HTTP_401_UNAUTHORIZED,
                title="Unauthorized",
                detail="Invalid bearer token",
                problem_type="https://campus.local/errors/unauthorized",
                errors=[],
            ),
        )


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@app.head("/health", response_class=Response)
@app.get("/health", response_model=HealthStatus)
def health(request: Request):
    if request.method == "HEAD":
        return Response(status_code=200)
    return HealthStatus(
        status="ok",
        service=SERVICE_NAME,
        time=now_iso(),
    )


@app.post(
    "/events",
    response_model=EventAccepted,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_bearer_token)],
)
def create_event(payload: Dict[Any, Any]) -> EventAccepted:
    event_type = payload.get("eventType")
    if not event_type:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=build_problem(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                title="Validation error",
                detail="eventType is required",
                problem_type="https://campus.local/errors/validation",
            )
        )
    
    allowed_event_types = ["telemetry.ingested", "camera.motion.detected", "alert.resolved", "policy.decision.created", "access.log.created"]
    if event_type not in allowed_event_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=build_problem(
                status_code=status.HTTP_400_BAD_REQUEST,
                title="Invalid Event Type",
                detail="eventType is not supported",
                problem_type="https://campus.local/errors/validation",
            )
        )

    value = payload.get("value")
    if value is not None and (value < -100 or value > 1000):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=build_problem(
                status_code=status.HTTP_400_BAD_REQUEST,
                title="Invalid Value",
                detail="Value out of range",
                problem_type="https://campus.local/errors/validation",
            )
        )

    event_id = payload.get("eventId", str(uuid.uuid4()))
    payload["eventId"] = event_id
    payload["acceptedAt"] = now_iso()
    EVENTS.append(payload)

    return EventAccepted(
        eventId=event_id,
        acceptedAt=payload["acceptedAt"],
    )


@app.post(
    "/alerts",
    response_model=Alert,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_bearer_token)],
)
def create_alert(payload: CreateAlertRequest, response: Response) -> Alert:
    allowed_alerts = ["UNAUTHORIZED_ACCESS", "SENSOR_THRESHOLD_EXCEEDED", "UNKNOWN_PERSON", "SYSTEM_ERROR"]
    if payload.alertType not in allowed_alerts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=build_problem(
                status_code=status.HTTP_400_BAD_REQUEST,
                title="Invalid Alert Type",
                detail="alertType must be one of allowed values",
                problem_type="https://campus.local/errors/validation",
            )
        )

    alert_id = str(uuid.uuid4())
    created_at = now_iso()
    
    alert = {
        "id": alert_id,
        "sourceService": payload.sourceService,
        "alertType": payload.alertType,
        "severity": payload.severity,
        "message": payload.message,
        "relatedEventId": payload.relatedEventId,
        "status": AlertStatus.OPEN.value,
        "createdAt": created_at,
        "resolvedAt": None,
    }
    
    ALERTS.append(alert)
    response.headers["Location"] = f"/alerts/{alert_id}"

    return Alert(**alert)


@app.get(
    "/alerts/recent",
    dependencies=[Depends(verify_bearer_token)],
)
def get_recent_alerts(limit: int = Query(default=20, ge=1, le=100)) -> Dict[str, List[Dict]]:
    return {"items": ALERTS[-limit:]}


@app.get(
    "/alerts",
    response_model=AlertPage,
    dependencies=[Depends(verify_bearer_token)],
)
def list_alerts(
    cursor: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
) -> AlertPage:
    items = ALERTS[-limit:]
    return AlertPage(
        items=items,
        nextCursor=None,
        hasMore=False,
    )


@app.get(
    "/alerts/{alert_id}",
    response_model=Alert,
    dependencies=[Depends(verify_bearer_token)],
)
def get_alert(alert_id: str) -> Alert:
    for alert in ALERTS:
        if alert["id"] == alert_id:
            return Alert(**alert)

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=build_problem(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Not Found",
            detail=f"Alert {alert_id} not found",
            instance=f"/alerts/{alert_id}",
            problem_type="https://campus.local/errors/not-found",
        ),
    )
