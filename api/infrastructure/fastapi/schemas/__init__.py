from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BeforeValidator


def _to_unix_timestamp(value: datetime | int) -> int:
    return int(value.timestamp()) if isinstance(value, datetime) else value


UnixTimestamp = Annotated[int, BeforeValidator(_to_unix_timestamp)]

MIN_PASSWORD_LENGTH: int = 6
MAX_PASSWORD_LENGTH: int = 72
# bcrypt reads at most 72 *bytes*: a password of 72 non-ASCII characters is longer than that once encoded.
MAX_PASSWORD_BYTES: int = 72


def _limit_password_bytes(value: str | None) -> str | None:
    if value is not None and len(value.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise ValueError(f"Password must not exceed {MAX_PASSWORD_BYTES} bytes once encoded in UTF-8.")
    return value


PasswordBytesLimit = AfterValidator(_limit_password_bytes)

__all__ = ["MAX_PASSWORD_BYTES", "MAX_PASSWORD_LENGTH", "MIN_PASSWORD_LENGTH", "PasswordBytesLimit", "UnixTimestamp"]
