from pydantic import BaseModel


class AnnouncementIn(BaseModel):
    message: str | None = None


class AnnouncementOut(BaseModel):
    message: str | None = None
