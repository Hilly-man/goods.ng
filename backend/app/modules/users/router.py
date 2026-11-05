import uuid

from fastapi import APIRouter, File, UploadFile
from pydantic import BaseModel, Field

from app.core.deps import DB, CurrentUser
from app.core.security import clean_text
from app.integrations.storage import store_image
from app.models import NotificationPreference, Profile
from app.modules.auth.router import user_out
from app.modules.auth.schemas import UserOut
from app.modules.notifications.service import EVENTS, channels_for

router = APIRouter(prefix="/users", tags=["users"])


class ProfileIn(BaseModel):
    full_name: str | None = Field(None, min_length=2, max_length=120)
    bio: str | None = Field(None, max_length=1000)
    state: str | None = Field(None, max_length=60)
    city: str | None = Field(None, max_length=80)
    address: str | None = Field(None, max_length=300)


@router.patch("/me", response_model=UserOut)
def update_me(data: ProfileIn, user: CurrentUser, db: DB):
    if not user.profile:
        user.profile = Profile()
    if data.full_name:
        user.full_name = clean_text(data.full_name)
    if data.city is not None or data.state is not None:
        from app.modules.locations import canonical_city

        data.city = canonical_city(db, data.state or user.profile.state, data.city) if data.city else data.city
    for f in ("bio", "state", "city", "address"):
        v = getattr(data, f)
        if v is not None:
            setattr(user.profile, f, clean_text(v))
    db.commit()
    return user_out(db, user)


@router.post("/me/avatar", response_model=UserOut)
async def upload_avatar(user: CurrentUser, db: DB, file: UploadFile = File(...)):
    img = store_image(await file.read(), "avatars")
    if not user.profile:
        user.profile = Profile()
    user.profile.avatar_url = img.thumb_url
    db.commit()
    return user_out(db, user)


class PrefIn(BaseModel):
    event_type: str
    in_app: bool
    email: bool
    sms: bool


@router.get("/me/notification-preferences")
def get_prefs(user: CurrentUser, db: DB):
    return [{"event_type": e, **channels_for(db, user.id, e)} for e in EVENTS if e != "otp"]


@router.put("/me/notification-preferences")
def set_prefs(data: list[PrefIn], user: CurrentUser, db: DB):
    for p in data:
        if p.event_type not in EVENTS or p.event_type == "otp":
            continue
        pref = db.query(NotificationPreference).filter_by(user_id=user.id, event_type=p.event_type).one_or_none()
        if not pref:
            pref = NotificationPreference(user_id=user.id, event_type=p.event_type)
            db.add(pref)
        pref.in_app, pref.email, pref.sms = p.in_app, p.email, p.sms
    db.commit()
    return get_prefs(user, db)


class ReportIn(BaseModel):
    target_type: str = Field(pattern="^(product|seller|user|review)$")
    target_id: uuid.UUID
    reason: str = Field(min_length=3, max_length=60)
    details: str | None = Field(None, max_length=1000)


@router.post("/reports", status_code=201)
def report(data: ReportIn, user: CurrentUser, db: DB):
    """Report a listing, seller, user or review for moderation."""
    from app.core.cache import check_rate_limit
    from app.core.security import clean_text as ct
    from app.models import Report

    check_rate_limit(f"report:{user.id}", 20, 86400)
    db.add(Report(reporter_id=user.id, target_type=data.target_type, target_id=data.target_id,
                  reason=ct(data.reason), details=ct(data.details)))
    db.commit()
    return {"reported": True}
