from pydantic import BaseModel, ConfigDict


class LoginIn(BaseModel):
    email: str
    password: str


class PasswordIn(BaseModel):
    actual: str
    nueva: str


class LoginUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    display_name: str
    role: str
    email: str
    estado_actual: str
    can_view_dashboard: bool


class LoginOut(BaseModel):
    token: str
    user: LoginUserOut
