from pydantic import ValidationError
import pytest

from api.infrastructure.configuration import Settings
from api.infrastructure.fastapi.schemas.admin.users import CreateUserBody, UserUpdateRequest
from api.infrastructure.fastapi.schemas.auth import AuthLoginBody
from api.infrastructure.fastapi.schemas.me import UpdateMeBody

# bcrypt reads at most 72 bytes: 36 "é" are exactly 72 bytes in UTF-8, 37 are 74 bytes for only 37 characters
FITS = "é" * 36
TOO_LONG_IN_BYTES = "é" * 37


def _create_user(password: str) -> CreateUserBody:
    return CreateUserBody(email="user@example.com", password=password, role_id=1, organization_id=1)


def _update_user(**passwords: str) -> UserUpdateRequest:
    return UserUpdateRequest(email="user@example.com", name=None, role_id=1, organization_id=1, expires=None, priority=0, **passwords)


def _update_user_password(password: str) -> UserUpdateRequest:
    return _update_user(current_password="current-password", password=password)


def _update_user_current_password(password: str) -> UserUpdateRequest:
    return _update_user(current_password=password, password="new-password")


def _update_me(**passwords: str) -> UpdateMeBody:
    return UpdateMeBody(name="User", email="user@example.com", **passwords)


def _update_me_password(password: str) -> UpdateMeBody:
    return _update_me(current_password="current-password", password=password)


def _update_me_current_password(password: str) -> UpdateMeBody:
    return _update_me(current_password=password, password="new-password")


def _login(password: str) -> AuthLoginBody:
    return AuthLoginBody(email="user@example.com", password=password)


BUILDERS = [
    pytest.param(_create_user, id="create-user"),
    pytest.param(_update_user_password, id="update-user-password"),
    pytest.param(_update_user_current_password, id="update-user-current-password"),
    pytest.param(_update_me_password, id="update-me-password"),
    pytest.param(_update_me_current_password, id="update-me-current-password"),
    pytest.param(_login, id="login"),
]


@pytest.mark.parametrize("build", BUILDERS)
class TestPasswordsAreLimitedInBytes:
    """bcrypt raises a ValueError above 72 bytes, which would surface as a 500: the schema must reject such a password with a 422."""

    @pytest.mark.parametrize("password", ["a" * 72, FITS], ids=["72-ascii-characters", "72-bytes-of-non-ascii"])
    def test_should_accept_a_password_of_at_most_72_bytes(self, build, password):
        build(password)

    @pytest.mark.parametrize(
        "password", [TOO_LONG_IN_BYTES, "é" * 72, "a" * 73], ids=["37-non-ascii-characters", "72-non-ascii-characters", "73-ascii"]
    )
    def test_should_reject_a_password_longer_than_72_bytes(self, build, password):
        with pytest.raises(ValidationError):
            build(password)


@pytest.mark.parametrize("build", [_create_user, _update_user_password, _update_user_current_password, _login])
def test_should_count_the_bytes_after_stripping_the_whitespace(build):
    build(f"  {FITS}  ")


def test_should_leave_the_optional_passwords_unset():
    assert _update_user().password is None
    assert _update_me().password is None


def test_should_reject_a_bootstrap_admin_password_longer_than_72_bytes():
    with pytest.raises(ValidationError) as error:
        Settings.model_validate({"auth_bootsrap_admin_password": TOO_LONG_IN_BYTES})

    assert any(e["loc"] == ("auth_bootsrap_admin_password",) for e in error.value.errors())
