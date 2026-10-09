"""SQL helpers for the asignacion module: permissions, writes and DB errors.

Permissions reproduce the old Supabase RLS policies
(`alembic/sql/0021_horarios/99_rls_reference.sql`) by calling the same SQL
helpers (`horarios.fn_puede_*`), which read the requesting user from the
session context set by `get_asignacion_db`.

Validation stays in Postgres (constraints and triggers). Their errors are
returned as `detail = {message, code, hint}` (the PostgREST error shape), so the
Angular `ErrorSistema` keeps translating them exactly as before.
"""

import json
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from enum import StrEnum
from typing import Any

from fastapi import HTTPException
from sqlalchemy import RowMapping, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

FORBIDDEN_MESSAGE = "No tiene permisos para realizar esta acción."

# SQLSTATE -> HTTP status. Class 22 (data exception) is matched by prefix below.
_STATUS_BY_SQLSTATE = {
    "23505": 409,  # unique_violation
    "23503": 409,  # foreign_key_violation
    "23514": 422,  # check_violation
    "23502": 422,  # not_null_violation
    "P0001": 422,  # raise exception (business rules in triggers/functions)
    "42501": 403,  # insufficient_privilege
}


class Permission(StrEnum):
    """Whitelisted SQL permission helpers (value = function in schema horarios)."""

    VER = "fn_puede_ver"
    EDITAR = "fn_puede_editar"
    OPERAR = "fn_puede_operar"
    GESTIONAR_AUXILIARES = "fn_puede_gestionar_auxiliares"
    ADMIN = "fn_es_admin"


_PERMISSION_SQL = {p: text(f"select horarios.{p.value}()") for p in Permission}


def error_detail(message: str, code: str | None, hint: str | None = None) -> dict:
    return {"message": message, "code": code, "hint": hint}


def require(db: Session, permission: Permission) -> None:
    """403 unless the SQL permission helper allows the current user."""
    if not db.execute(_PERMISSION_SQL[permission]).scalar():
        raise HTTPException(403, error_detail(FORBIDDEN_MESSAGE, "42501"))


def not_found() -> HTTPException:
    return HTTPException(404, error_detail("No encontrado.", None))


def http_error_from_db(exc: DBAPIError) -> HTTPException | None:
    """Map a Postgres error to an HTTP error, or None if it is not a client error."""
    orig = exc.orig
    sqlstate = getattr(orig, "sqlstate", None)
    if not sqlstate:
        return None
    status = _STATUS_BY_SQLSTATE.get(sqlstate)
    if status is None and sqlstate.startswith("22"):
        status = 422
    if status is None:
        return None
    diag = getattr(orig, "diag", None)
    message = getattr(diag, "message_primary", None) or str(orig)
    hint = getattr(diag, "message_hint", None)
    return HTTPException(status, error_detail(message, sqlstate, hint))


@contextmanager
def writing(db: Session) -> Iterator[None]:
    """Run a write and commit it; DB errors become HTTP errors after a rollback.

    The commit is inside the block so deferred constraint triggers are mapped too.
    """
    try:
        yield
        db.commit()
    except DBAPIError as exc:
        db.rollback()
        mapped = http_error_from_db(exc)
        if mapped is None:
            raise
        raise mapped from None


def _check_columns(values: Mapping[str, Any]) -> None:
    # Column names come from Pydantic field names (extra="forbid"); this guard
    # only protects against a future caller passing raw user keys.
    for column in values:
        if not column.isidentifier():
            raise ValueError(f"invalid column name: {column!r}")


def insert_returning_id(db: Session, table: str, values: Mapping[str, Any]) -> Any:
    """INSERT into horarios.<table> and return the new id (DB defaults apply)."""
    _check_columns(values)
    if values:
        columns = ", ".join(values)
        params = ", ".join(f":{c}" for c in values)
        sql = f"insert into horarios.{table} ({columns}) values ({params}) returning id"
    else:
        sql = f"insert into horarios.{table} default values returning id"
    return db.execute(text(sql), dict(values)).scalar_one()


def update_by_id(
    db: Session, table: str, row_id: int, values: Mapping[str, Any]
) -> bool:
    """UPDATE horarios.<table> by id; False when the row does not exist."""
    _check_columns(values)
    if not values:
        sql = f"select 1 from horarios.{table} where id = :_id"
    else:
        assignments = ", ".join(f"{c} = :{c}" for c in values)
        sql = f"update horarios.{table} set {assignments} where id = :_id returning 1"
    return db.execute(text(sql), {**values, "_id": row_id}).first() is not None


def delete_by_id(db: Session, table: str, row_id: int) -> bool:
    sql = text(f"delete from horarios.{table} where id = :id returning 1")
    return db.execute(sql, {"id": row_id}).first() is not None


def rows(
    db: Session, sql: Any, params: Mapping[str, Any] | None = None
) -> list[RowMapping]:
    return list(db.execute(sql, dict(params or {})).mappings().all())


def call_rpc(db: Session, function: str, payload: Mapping[str, Any]) -> Any:
    """Call `horarios.<function>(p jsonb)` with `payload` bound as one JSON value.

    `function` must be a literal from the code (never user input); the payload
    is serialized here and only ever travels as a bound parameter.
    """
    if not function.isidentifier():
        raise ValueError(f"invalid function name: {function!r}")
    sql = text(f"select horarios.{function}(cast(:p as jsonb))")
    return db.execute(sql, {"p": json.dumps(payload, default=str)}).scalar_one()
