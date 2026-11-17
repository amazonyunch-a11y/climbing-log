from datetime import datetime, timedelta, timezone
import logging

import jwt
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient

import app.api.auth as auth_api
from app.core.config import get_settings
from app.core.password_reset import password_reset_rate_limiter
from app.core.security import create_access_token, verify_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.password_reset_code import PasswordResetCode, PasswordResetPurpose
from app.models.user import User
from app.services import resend
from app.services.resend import ResendDeliveryError
from tests.auth_helpers import mark_email_verified


REQUEST_MESSAGE = {
    "message": (
        "회원가입시 입력하신 이메일을 확인해 주세요. "
        "해당 메일주소로 인증 코드를 발송했습니다."
    )
}
CONFIRM_MESSAGE = {
    "message": "비밀번호가 변경되었습니다. 새 비밀번호로 로그인해 주세요."
}
INVALID_MESSAGE = {"message": "인증번호가 올바르지 않거나 만료되었습니다."}


@pytest.fixture(autouse=True)
def clear_password_reset_rate_limits():
    password_reset_rate_limiter.clear()
    yield
    password_reset_rate_limiter.clear()


@pytest.fixture
def client_and_engine():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session_local = sessionmaker(bind=engine)

    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client, engine

    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def delivered_codes(monkeypatch):
    delivered = []

    def fake_send(*, recipient: str, code: str) -> None:
        delivered.append({"recipient": recipient, "code": code})

    monkeypatch.setattr(auth_api, "send_password_reset_code_email", fake_send)
    return delivered


def signup(client: TestClient, email: str = "user@example.com") -> None:
    response = client.post(
        "/api/auth/signup",
        json={
            "email": email,
            "password": "correct-password",
            "nickname": "Climber01",
        },
    )
    assert response.status_code == 201
    mark_email_verified(email)


def request_reset(client: TestClient, email: str = "user@example.com"):
    return client.post(
        "/api/auth/password-reset/request",
        json={"email": email},
    )


def confirm_reset(
    client: TestClient,
    code: str,
    *,
    email: str = "user@example.com",
    password: str = "new-password",
):
    return client.post(
        "/api/auth/password-reset/confirm",
        json={
            "email": email,
            "code": code,
            "new_password": password,
            "new_password_confirm": password,
        },
    )


def test_request_is_identical_for_registered_and_unknown_email(
    client_and_engine, delivered_codes
) -> None:
    client, _ = client_and_engine
    signup(client)

    registered = request_reset(client, "  USER@EXAMPLE.COM ")
    unknown = request_reset(client, "missing@example.com")

    assert registered.status_code == unknown.status_code == 202
    assert registered.json() == unknown.json() == REQUEST_MESSAGE
    assert len(delivered_codes) == 1
    assert delivered_codes[0]["recipient"] == "user@example.com"


def test_request_stores_only_hash_and_sets_five_minute_expiry(
    client_and_engine, delivered_codes
) -> None:
    client, engine = client_and_engine
    signup(client)
    before = datetime.now(timezone.utc).replace(tzinfo=None)

    response = request_reset(client)

    assert response.status_code == 202
    code = delivered_codes[0]["code"]
    assert len(code) == 6 and code.isdigit()
    with Session(engine) as db:
        reset_code = db.scalar(select(PasswordResetCode))
        assert reset_code is not None
        assert reset_code.codeHash != code
        assert reset_code.purpose is PasswordResetPurpose.PASSWORD_RESET
        assert code not in reset_code.codeHash
        assert reset_code.requestedIp == "testclient"
        assert timedelta(minutes=4, seconds=59) <= reset_code.expiresAt - before
        assert reset_code.expiresAt - before <= timedelta(minutes=5, seconds=2)


def test_request_invalidates_previous_unused_code(
    client_and_engine, delivered_codes
) -> None:
    client, engine = client_and_engine
    signup(client)
    assert request_reset(client).status_code == 202
    with Session(engine) as db:
        first = db.scalar(select(PasswordResetCode))
        first.createdAt -= timedelta(seconds=61)
        db.commit()

    assert request_reset(client).status_code == 202

    with Session(engine) as db:
        codes = list(
            db.scalars(select(PasswordResetCode).order_by(PasswordResetCode.id))
        )
        assert len(codes) == 2
        assert codes[0].invalidatedAt is not None
        assert codes[0].usedAt is None
        assert codes[1].invalidatedAt is None


def test_email_rate_limits_do_not_send_or_create_rows(
    client_and_engine, delivered_codes
) -> None:
    client, engine = client_and_engine
    signup(client)

    assert request_reset(client).status_code == 202
    assert request_reset(client).status_code == 202
    assert len(delivered_codes) == 1

    for expected_count in (2, 3):
        with Session(engine) as db:
            latest = db.scalar(
                select(PasswordResetCode).order_by(PasswordResetCode.id.desc())
            )
            latest.createdAt = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
                seconds=61
            )
            db.commit()
        assert request_reset(client).status_code == 202
        assert len(delivered_codes) == expected_count

    with Session(engine) as db:
        latest = db.scalar(
            select(PasswordResetCode).order_by(PasswordResetCode.id.desc())
        )
        latest.createdAt = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
            seconds=61
        )
        db.commit()

    assert request_reset(client).status_code == 202
    assert len(delivered_codes) == 3
    with Session(engine) as db:
        assert len(list(db.scalars(select(PasswordResetCode)))) == 3


def test_request_ip_limit_includes_unknown_emails(
    client_and_engine, delivered_codes
) -> None:
    client, _ = client_and_engine
    signup(client)
    for index in range(10):
        response = request_reset(client, f"missing-{index}@example.com")
        assert response.status_code == 202

    response = request_reset(client)

    assert response.status_code == 202
    assert response.json() == REQUEST_MESSAGE
    assert delivered_codes == []


def test_resend_failure_returns_generic_success_and_rolls_back(
    client_and_engine, monkeypatch, caplog
) -> None:
    client, engine = client_and_engine
    signup(client)
    exposed_code = "654321"

    def fail_send(*, recipient: str, code: str) -> None:
        raise ResendDeliveryError(f"delivery failed for {exposed_code}")

    monkeypatch.setattr(auth_api, "send_password_reset_code_email", fail_send)
    with caplog.at_level(logging.WARNING):
        response = request_reset(client)

    assert response.status_code == 202
    assert response.json() == REQUEST_MESSAGE
    assert exposed_code not in caplog.text
    with Session(engine) as db:
        assert db.scalar(select(PasswordResetCode)) is None


def test_confirm_success_changes_password_version_and_invalidates_old_token(
    client_and_engine, delivered_codes
) -> None:
    client, engine = client_and_engine
    signup(client)
    old_token = client.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "correct-password"},
    ).json()["access_token"]
    assert request_reset(client).status_code == 202

    response = confirm_reset(client, delivered_codes[0]["code"])

    assert response.status_code == 202
    assert response.json() == CONFIRM_MESSAGE
    with Session(engine) as db:
        user = db.scalar(select(User).where(User.email == "user@example.com"))
        reset_code = db.scalar(select(PasswordResetCode))
        assert user.authVersion == 2
        assert user.passwordHash.startswith("$argon2")
        assert verify_password("new-password", user.passwordHash)
        assert reset_code.usedAt is not None
        assert reset_code.invalidatedAt is None

    old_me = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {old_token}"}
    )
    old_login = client.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "correct-password"},
    )
    new_login = client.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "new-password"},
    )
    new_me = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {new_login.json()['access_token']}"},
    )
    assert old_me.status_code == 401
    assert old_login.status_code == 401
    assert new_login.status_code == 200
    assert new_me.status_code == 200


def test_wrong_code_increments_attempts_and_fifth_failure_invalidates(
    client_and_engine, delivered_codes
) -> None:
    client, engine = client_and_engine
    signup(client)
    request_reset(client)

    for expected_attempts in range(1, 6):
        response = confirm_reset(client, "000000")
        assert response.status_code == 400
        assert response.json() == INVALID_MESSAGE
        with Session(engine) as db:
            reset_code = db.scalar(select(PasswordResetCode))
            assert reset_code.failedAttempts == expected_attempts
            assert (reset_code.invalidatedAt is not None) == (expected_attempts == 5)


def test_expired_used_and_duplicate_codes_are_rejected(
    client_and_engine, delivered_codes
) -> None:
    client, engine = client_and_engine
    signup(client)
    request_reset(client)
    first_code = delivered_codes[-1]["code"]
    with Session(engine) as db:
        reset_code = db.scalar(select(PasswordResetCode))
        reset_code.expiresAt = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
            seconds=1
        )
        db.commit()
    assert confirm_reset(client, first_code).status_code == 400

    with Session(engine) as db:
        reset_code = db.scalar(select(PasswordResetCode))
        reset_code.createdAt -= timedelta(seconds=61)
        db.commit()
    request_reset(client)
    second_code = delivered_codes[-1]["code"]
    assert confirm_reset(client, second_code).status_code == 202
    duplicate = confirm_reset(client, second_code)
    assert duplicate.status_code == 400
    assert duplicate.json() == INVALID_MESSAGE


def test_confirm_password_policy_and_ip_rate_limit(
    client_and_engine, delivered_codes
) -> None:
    client, _ = client_and_engine
    weak = client.post(
        "/api/auth/password-reset/confirm",
        json={
            "email": "user@example.com",
            "code": "123456",
            "new_password": "short",
            "new_password_confirm": "short",
        },
    )
    assert weak.status_code == 422
    assert weak.json() == {"message": "비밀번호는 8자 이상이어야 합니다."}

    password_reset_rate_limiter.clear()
    for _ in range(10):
        assert confirm_reset(client, "123456").status_code == 400
    limited = confirm_reset(client, "123456")
    assert limited.status_code == 429
    assert limited.json() == {
        "message": "요청이 너무 많습니다. 잠시 후 다시 시도해 주세요."
    }


def test_login_token_contains_and_enforces_auth_version(client_and_engine) -> None:
    client, engine = client_and_engine
    signup(client)
    token = client.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "correct-password"},
    ).json()["access_token"]
    settings = get_settings()
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    assert payload["auth_version"] == 1

    mismatched = create_access_token(1, auth_version=2)
    response = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {mismatched}"}
    )
    assert response.status_code == 401

    with Session(engine) as db:
        other = User(
            email="other@example.com",
            passwordHash="unused",
            nickname="OtherAa",
            createdAt="2026-11-12T00:00:00Z",
            updatedAt=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        db.add(other)
        db.commit()
        other_token = create_access_token(other.id, other.authVersion)
    other_me = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {other_token}"}
    )
    assert other_me.json()["email"] == "other@example.com"


def test_legacy_token_without_auth_version_only_works_at_version_one(
    client_and_engine,
) -> None:
    client, engine = client_and_engine
    signup(client)
    settings = get_settings()
    legacy_token = jwt.encode(
        {
            "sub": "1",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    before_reset = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {legacy_token}"},
    )
    assert before_reset.status_code == 200

    with Session(engine) as db:
        user = db.get(User, 1)
        user.authVersion = 2
        db.commit()

    after_reset = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {legacy_token}"},
    )
    assert after_reset.status_code == 401


def test_confirm_query_uses_postgresql_row_lock() -> None:
    statement = auth_api._latest_active_reset_code_statement(1)
    sql = str(statement.compile(dialect=postgresql.dialect()))

    assert "FOR UPDATE" in sql


def test_resend_payload_contains_code_and_five_minute_notice(monkeypatch) -> None:
    sent = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def post(self, url, **kwargs):
            sent["url"] = url
            sent.update(kwargs)
            return FakeResponse()

    monkeypatch.setattr(resend.httpx, "Client", FakeClient)
    resend.send_password_reset_code_email(
        recipient="user@example.com",
        code="123456",
    )

    assert sent["url"] == "https://api.resend.com/emails"
    assert sent["json"]["to"] == ["user@example.com"]
    assert "123456" in sent["json"]["html"]
    assert "5분" in sent["json"]["html"]
