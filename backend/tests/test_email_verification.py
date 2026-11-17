from datetime import datetime, timedelta, timezone
import logging

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient

import app.api.auth as auth_api
from app.core.password_reset import (
    hash_password_reset_code,
    password_reset_rate_limiter,
)
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.password_reset_code import PasswordResetCode, PasswordResetPurpose
from app.models.user import User
from app.services import resend
from app.services.resend import ResendDeliveryError


REQUEST_MESSAGE = {"message": "입력한 이메일 주소로 인증번호를 발송했습니다."}
CONFIRM_MESSAGE = {"message": "이메일 인증이 완료되었습니다.", "verified": True}
INVALID_MESSAGE = {"message": "인증번호가 올바르지 않거나 만료되었습니다."}


@pytest.fixture(autouse=True)
def clear_rate_limits():
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

    monkeypatch.setattr(auth_api, "send_email_verification_code_email", fake_send)
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


def request_verification(client: TestClient, email: str = "user@example.com"):
    return client.post(
        "/api/auth/email-verification/request",
        json={"email": email},
    )


def confirm_verification(
    client: TestClient,
    code: str,
    email: str = "user@example.com",
):
    return client.post(
        "/api/auth/email-verification/confirm",
        json={"email": email, "code": code},
    )


def test_request_stores_email_verification_hash_and_ten_minute_expiry(
    client_and_engine, delivered_codes
) -> None:
    client, engine = client_and_engine
    signup(client)
    before = datetime.now(timezone.utc).replace(tzinfo=None)

    response = request_verification(client, "  USER@EXAMPLE.COM ")

    assert response.status_code == 202
    assert response.json() == REQUEST_MESSAGE
    code = delivered_codes[0]["code"]
    assert len(code) == 6 and code.isdigit()
    with Session(engine) as db:
        user = db.scalar(select(User))
        verification = db.scalar(select(PasswordResetCode))
        assert user.emailVerifiedAt is None
        assert verification.purpose is PasswordResetPurpose.EMAIL_VERIFICATION
        assert verification.codeHash != code
        assert code not in verification.codeHash
        assert timedelta(minutes=9, seconds=59) <= verification.expiresAt - before
        assert verification.expiresAt - before <= timedelta(minutes=10, seconds=2)


def test_request_hides_unknown_and_verified_accounts(
    client_and_engine, delivered_codes
) -> None:
    client, engine = client_and_engine
    signup(client)
    unknown = request_verification(client, "missing@example.com")
    with Session(engine) as db:
        user = db.scalar(select(User))
        user.emailVerifiedAt = datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()
    verified = request_verification(client)

    assert unknown.status_code == verified.status_code == 202
    assert unknown.json() == verified.json() == REQUEST_MESSAGE
    assert delivered_codes == []


def test_new_request_invalidates_only_previous_email_verification_code(
    client_and_engine, delivered_codes
) -> None:
    client, engine = client_and_engine
    signup(client)
    request_verification(client)
    with Session(engine) as db:
        user = db.scalar(select(User))
        first = db.scalar(select(PasswordResetCode))
        first.createdAt -= timedelta(seconds=61)
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        password_reset = PasswordResetCode(
            userId=user.id,
            codeHash=hash_password_reset_code(user_id=user.id, code="111111"),
            expiresAt=now + timedelta(minutes=5),
            failedAttempts=0,
            requestedIp="testclient",
            createdAt=now,
            updatedAt=now,
            purpose=PasswordResetPurpose.PASSWORD_RESET,
        )
        db.add(password_reset)
        db.commit()

    request_verification(client)

    with Session(engine) as db:
        verification_codes = list(
            db.scalars(
                select(PasswordResetCode)
                .where(
                    PasswordResetCode.purpose
                    == PasswordResetPurpose.EMAIL_VERIFICATION
                )
                .order_by(PasswordResetCode.id)
            )
        )
        password_reset = db.scalar(
            select(PasswordResetCode).where(
                PasswordResetCode.purpose == PasswordResetPurpose.PASSWORD_RESET
            )
        )
        assert verification_codes[0].invalidatedAt is not None
        assert verification_codes[1].invalidatedAt is None
        assert password_reset.invalidatedAt is None


def test_confirm_succeeds_without_changing_password_or_auth_version(
    client_and_engine, delivered_codes
) -> None:
    client, engine = client_and_engine
    signup(client)
    request_verification(client)
    code = delivered_codes[0]["code"]
    with Session(engine) as db:
        user = db.scalar(select(User))
        original_password_hash = user.passwordHash
        original_auth_version = user.authVersion

    response = confirm_verification(client, code)

    assert response.status_code == 200
    assert response.json() == CONFIRM_MESSAGE
    with Session(engine) as db:
        user = db.scalar(select(User))
        verification = db.scalar(select(PasswordResetCode))
        assert user.emailVerifiedAt is not None
        assert user.passwordHash == original_password_hash
        assert user.authVersion == original_auth_version
        assert verification.usedAt is not None
        assert verification.invalidatedAt is None

    login = client.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "correct-password"},
    )
    assert login.status_code == 200
    assert login.json()["access_token"]


def test_wrong_code_increments_attempts_and_fifth_failure_invalidates(
    client_and_engine, delivered_codes
) -> None:
    client, engine = client_and_engine
    signup(client)
    request_verification(client)

    for expected_attempts in range(1, 6):
        response = confirm_verification(client, "000000")
        assert response.status_code == 400
        assert response.json() == INVALID_MESSAGE
        with Session(engine) as db:
            verification = db.scalar(select(PasswordResetCode))
            assert verification.failedAttempts == expected_attempts
            assert (verification.invalidatedAt is not None) == (
                expected_attempts == 5
            )


def test_expired_and_used_codes_cannot_be_reused(
    client_and_engine, delivered_codes
) -> None:
    client, engine = client_and_engine
    signup(client)
    request_verification(client)
    expired_code = delivered_codes[-1]["code"]
    with Session(engine) as db:
        verification = db.scalar(select(PasswordResetCode))
        verification.expiresAt = datetime.now(timezone.utc).replace(
            tzinfo=None
        ) - timedelta(seconds=1)
        verification.createdAt -= timedelta(seconds=61)
        db.commit()
    assert confirm_verification(client, expired_code).status_code == 400

    request_verification(client)
    valid_code = delivered_codes[-1]["code"]
    assert confirm_verification(client, valid_code).status_code == 200
    reused = confirm_verification(client, valid_code)
    assert reused.status_code == 400
    assert reused.json() == INVALID_MESSAGE


def test_password_reset_and_email_verification_codes_cannot_mix(
    client_and_engine,
) -> None:
    client, engine = client_and_engine
    signup(client)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    with Session(engine) as db:
        user = db.scalar(select(User))
        db.add(
            PasswordResetCode(
                userId=user.id,
                codeHash=hash_password_reset_code(user_id=user.id, code="123456"),
                expiresAt=now + timedelta(minutes=5),
                failedAttempts=0,
                requestedIp="testclient",
                createdAt=now,
                updatedAt=now,
                purpose=PasswordResetPurpose.PASSWORD_RESET,
            )
        )
        db.commit()

    email_confirm = confirm_verification(client, "123456")
    password_confirm = client.post(
        "/api/auth/password-reset/confirm",
        json={
            "email": "user@example.com",
            "code": "123456",
            "new_password": "new-password",
            "new_password_confirm": "new-password",
        },
    )

    assert email_confirm.status_code == 400
    assert password_confirm.status_code == 202
    with Session(engine) as db:
        user = db.scalar(select(User))
        assert user.emailVerifiedAt is None


def test_email_and_ip_request_limits_do_not_send_or_create_codes(
    client_and_engine, delivered_codes
) -> None:
    client, engine = client_and_engine
    signup(client)
    assert request_verification(client).status_code == 202
    assert request_verification(client).status_code == 202
    assert len(delivered_codes) == 1
    with Session(engine) as db:
        assert len(list(db.scalars(select(PasswordResetCode)))) == 1

    password_reset_rate_limiter.clear()
    for index in range(10):
        assert request_verification(
            client, f"missing-{index}@example.com"
        ).status_code == 202
    blocked = request_verification(client)
    assert blocked.status_code == 202
    assert len(delivered_codes) == 1


def test_email_request_is_limited_to_three_times_per_fifteen_minutes(
    client_and_engine, delivered_codes
) -> None:
    client, engine = client_and_engine
    signup(client)

    for expected_count in range(1, 4):
        assert request_verification(client).status_code == 202
        assert len(delivered_codes) == expected_count
        with Session(engine) as db:
            latest = db.scalar(
                select(PasswordResetCode).order_by(PasswordResetCode.id.desc())
            )
            latest.createdAt = datetime.now(timezone.utc).replace(
                tzinfo=None
            ) - timedelta(seconds=61)
            db.commit()

    assert request_verification(client).status_code == 202
    assert len(delivered_codes) == 3
    with Session(engine) as db:
        assert len(list(db.scalars(select(PasswordResetCode)))) == 3


@pytest.mark.parametrize(
    "path,payload",
    [
        ("/api/auth/signup", {"email": "invalid", "password": "password", "nickname": "Climber01"}),
        ("/api/auth/email-verification/request", {"email": "invalid"}),
        ("/api/auth/email-verification/confirm", {"email": "invalid", "code": "123456"}),
    ],
)
def test_auth_email_fields_reject_invalid_format(
    client_and_engine, path: str, payload: dict
) -> None:
    client, _ = client_and_engine

    response = client.post(path, json=payload)

    assert response.status_code == 422


def test_resend_failure_is_generic_and_does_not_log_or_store_code(
    client_and_engine, monkeypatch, caplog
) -> None:
    client, engine = client_and_engine
    signup(client)
    exposed_code = "654321"

    def fail_send(*, recipient: str, code: str) -> None:
        raise ResendDeliveryError(f"failed for {exposed_code}")

    monkeypatch.setattr(auth_api, "send_email_verification_code_email", fail_send)
    with caplog.at_level(logging.WARNING):
        response = request_verification(client)

    assert response.status_code == 202
    assert response.json() == REQUEST_MESSAGE
    assert exposed_code not in caplog.text
    with Session(engine) as db:
        assert db.scalar(select(PasswordResetCode)) is None


def test_email_verification_resend_payload(monkeypatch) -> None:
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
            sent.update(kwargs)
            return FakeResponse()

    monkeypatch.setattr(resend.httpx, "Client", FakeClient)
    resend.send_email_verification_code_email(
        recipient="user@example.com",
        code="123456",
    )

    assert sent["json"]["to"] == ["user@example.com"]
    assert "123456" in sent["json"]["html"]
    assert "10분" in sent["json"]["html"]
    assert "이메일 인증" in sent["json"]["subject"]
