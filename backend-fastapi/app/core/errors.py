from fastapi import HTTPException


def unauthorized(detail: str) -> HTTPException:
    return HTTPException(status_code=401, detail=detail)


def forbidden(detail: str = "Sin permiso") -> HTTPException:
    return HTTPException(status_code=403, detail=detail)


def not_found(detail: str = "No encontrado") -> HTTPException:
    return HTTPException(status_code=404, detail=detail)


def bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=400, detail=detail)
