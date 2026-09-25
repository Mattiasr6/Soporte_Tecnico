"""JWT compatible .NET: HS256, mismos claims/iss/aud/expiración. Puro, sin DB."""

from datetime import UTC, datetime, timedelta

import jwt

ISSUER = "SoporteTecnico"
AUDIENCE = "SoporteTecnicoApp"
ALGORITHM = "HS256"
DIAS_EXPIRACION = 365

CLAIM_ID = "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/nameidentifier"
CLAIM_NOMBRE = "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name"
CLAIM_ROL = "http://schemas.microsoft.com/ws/2008/06/identity/claims/role"
CLAIM_EMAIL = "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress"
CLAIM_VERSION = "token_version"


def crear_token(
    usuario_id: int,
    display_name: str,
    role: str,
    email: str,
    secret: str,
    token_version: int = 0,
) -> str:
    ahora = datetime.now(UTC)
    return jwt.encode(
        {
            CLAIM_ID: str(usuario_id),
            CLAIM_NOMBRE: display_name,
            CLAIM_ROL: role,
            CLAIM_EMAIL: email,
            CLAIM_VERSION: token_version,
            "sub": str(usuario_id),
            "iss": ISSUER,
            "aud": AUDIENCE,
            "iat": ahora,
            "exp": ahora + timedelta(days=DIAS_EXPIRACION),
        },
        secret,
        algorithm=ALGORITHM,
    )


def validar_token(token: str, secret: str) -> dict[str, object]:
    return jwt.decode(
        token, secret, algorithms=[ALGORITHM], audience=AUDIENCE, issuer=ISSUER
    )
