"""DB session for the asignacion module, bound to the requesting user.

The ported Postgres functions (`horarios.fn_usuario_actual()` and everything
built on it: fn_rol_actual, fn_puede_editar, ...) read the transaction-local
setting `app.usuario_id`, the replacement for Supabase's `auth.uid()`.

`set_config(..., true)` is the function form of `SET LOCAL`: it dies with the
transaction. A commit in the middle of a request would therefore drop it, so
the setting is re-applied on every transaction the session begins (SQLAlchemy
`after_begin` event), not only once.
"""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy import Connection, event, text
from sqlalchemy.orm import Session, SessionTransaction

from app.core.security import CurrentUser
from app.db.session import get_db
from app.services.asignacion_perfiles import ensure_perfil

_SET_USUARIO = text("select set_config('app.usuario_id', :usuario_id, true)")
_INFO_KEY = "asignacion_usuario_id"


def _apply(conn: Connection, usuario_id: int) -> None:
    conn.execute(_SET_USUARIO, {"usuario_id": str(usuario_id)})


def _on_begin(session: Session, _tx: SessionTransaction, conn: Connection) -> None:
    usuario_id = session.info.get(_INFO_KEY)
    if usuario_id is not None:
        _apply(conn, usuario_id)


def bind_usuario_context(db: Session, usuario_id: int) -> None:
    """Make every transaction of `db` run as `usuario_id` (now and after commits)."""
    already_bound = _INFO_KEY in db.info
    db.info[_INFO_KEY] = usuario_id
    if not already_bound:
        event.listen(db, "after_begin", _on_begin)
    if db.in_transaction():
        _apply(db.connection(), usuario_id)


def get_asignacion_db(
    user: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> Iterator[Session]:
    # The perfil sync is committed before binding the context (see ensure_perfil).
    ensure_perfil(db, user)
    db.commit()
    bind_usuario_context(db, user.id)
    yield db


AsignacionDb = Annotated[Session, Depends(get_asignacion_db)]
