from datetime import datetime

import pytest
from sqlalchemy import DateTime, Enum, Integer, String, create_engine
from sqlalchemy.exc import StatementError
from sqlalchemy.orm import Session
from sqlalchemy.orm import configure_mappers

from app.db.base import Base
from app.models.climbing_session import ClimbingSession
from app.models.grade_logs import GradeLogs
from app.models.gyms import Gyms
from app.models.user import User
from app.models.user_profile import UserProfile
from app.models.videos import Videos
from app.models.stopwatch_session import StopwatchSession
from app.models.password_reset_code import PasswordResetCode, PasswordResetPurpose


def test_metadata_matches_erd_tables_and_columns() -> None:
    expected_columns = {
        "user": {
            "id": Integer,
            "email": String,
            "passwordHash": String,
            "nickname": String,
            "createdAt": String,
            "updatedAt": DateTime,
            "authVersion": Integer,
            "emailVerifiedAt": DateTime,
        },
        "userProfile": {
            "id": Integer,
            "userId": Integer,
            "birthDate": DateTime,
            "heightCm": Integer,
            "weightKg": Integer,
            "armLengthCm": Integer,
            "createdAt": DateTime,
            "updatedAt": DateTime,
        },
        "gyms": {
            "id": Integer,
            "userId": Integer,
            "name": String,
            "lacation": String,
            "createAt": DateTime,
            "updateAt": DateTime,
        },
        "climbingSession": {
            "id": Integer,
            "userId": Integer,
            "gymId": Integer,
            "sessionDate": DateTime,
            "startedAt": DateTime,
            "endedAt": DateTime,
            "durationMintes": Integer,
            "durationSource": String,
            "totalAteempts": Integer,
            "totalSends": Integer,
            "notes": String,
            "createdAt": DateTime,
        },
        "gradeLogs": {
            "id": Integer,
            "sessionId": Integer,
            "gradeLabel": String,
            "attempts": Integer,
            "sends": Integer,
            "createdAt": DateTime,
            "endedAt": DateTime,
        },
        "videos": {
            "id": Integer,
            "userId": Integer,
            "sessionId": Integer,
            "storagePath": String,
            "thumbnailPath": String,
            "title": String,
            "gradLabel": Integer,
            "notes": String,
            "orginaFilename": String,
            "fileSize": String,
            "durationSeconds": String,
            "mimeTpe": String,
            "recordedAt": DateTime,
            "createdAt": DateTime,
            "updateAt": DateTime,
        },
        "stopwatchSessions": {
            "id": Integer,
            "userId": Integer,
            "climbingSessionId": Integer,
            "startedAt": DateTime,
            "endedAt": DateTime,
            "elapsedSeconds": Integer,
            "status": String,
            "createdAt": DateTime,
            "updatedAt": DateTime,
        },
        "passwordResetCodes": {
            "id": Integer,
            "userId": Integer,
            "codeHash": String,
            "expiresAt": DateTime,
            "usedAt": DateTime,
            "invalidatedAt": DateTime,
            "failedAttempts": Integer,
            "requestedIp": String,
            "createdAt": DateTime,
            "updatedAt": DateTime,
            "purpose": Enum,
        },
    }

    assert set(Base.metadata.tables) == set(expected_columns)

    for table_name, expected in expected_columns.items():
        table = Base.metadata.tables[table_name]
        assert {column.name: type(column.type) for column in table.columns} == expected
        assert [column.name for column in table.primary_key.columns] == ["id"]

    user_table = Base.metadata.tables["user"]
    assert user_table.c.email.unique is True
    assert user_table.c.createdAt.unique is True


def test_foreign_keys_match_erd() -> None:
    expected_foreign_keys = {
        "userProfile": {"userId": "user.id"},
        "gyms": {"userId": "user.id"},
        "climbingSession": {"userId": "user.id", "gymId": "gyms.id"},
        "gradeLogs": {"sessionId": "climbingSession.id"},
        "videos": {"userId": "user.id", "sessionId": "climbingSession.id"},
        "stopwatchSessions": {
            "userId": "user.id",
            "climbingSessionId": "climbingSession.id",
        },
        "passwordResetCodes": {"userId": "user.id"},
    }

    for table_name, expected in expected_foreign_keys.items():
        table = Base.metadata.tables[table_name]
        actual = {
            foreign_key.parent.name: foreign_key.target_fullname
            for foreign_key in table.foreign_keys
        }
        assert actual == expected


def test_relationships_match_erd() -> None:
    configure_mappers()

    assert User.profiles.property.mapper.class_ is UserProfile
    assert User.gyms.property.mapper.class_ is Gyms
    assert User.sessions.property.mapper.class_ is ClimbingSession
    assert User.videos.property.mapper.class_ is Videos
    assert User.stopwatch_sessions.property.mapper.class_ is StopwatchSession
    assert User.password_reset_codes.property.mapper.class_ is PasswordResetCode
    assert UserProfile.user.property.mapper.class_ is User
    assert Gyms.user.property.mapper.class_ is User
    assert Gyms.sessions.property.mapper.class_ is ClimbingSession
    assert ClimbingSession.user.property.mapper.class_ is User
    assert ClimbingSession.gym.property.mapper.class_ is Gyms
    assert ClimbingSession.grade_logs.property.mapper.class_ is GradeLogs
    assert ClimbingSession.videos.property.mapper.class_ is Videos
    assert ClimbingSession.stopwatch_session.property.mapper.class_ is StopwatchSession
    assert ClimbingSession.stopwatch_session.property.uselist is False
    assert GradeLogs.session.property.mapper.class_ is ClimbingSession
    assert Videos.user.property.mapper.class_ is User
    assert Videos.session.property.mapper.class_ is ClimbingSession
    assert StopwatchSession.user.property.mapper.class_ is User
    assert StopwatchSession.climbing_session.property.mapper.class_ is ClimbingSession
    assert PasswordResetCode.user.property.mapper.class_ is User


def test_stopwatch_session_link_constraints() -> None:
    stopwatch_table = Base.metadata.tables["stopwatchSessions"]
    climbing_table = Base.metadata.tables["climbingSession"]

    climbing_session_fk = next(
        foreign_key
        for foreign_key in stopwatch_table.foreign_keys
        if foreign_key.parent.name == "climbingSessionId"
    )
    assert climbing_session_fk.target_fullname == "climbingSession.id"
    assert climbing_session_fk.ondelete == "SET NULL"
    assert any(
        constraint.name == "uq_stopwatchSessions_climbingSessionId"
        for constraint in stopwatch_table.constraints
    )
    assert any(index.name == "ix_stopwatchSessions_userId" for index in stopwatch_table.indexes)
    assert climbing_table.c.durationSource.default.arg == "manual"
    assert climbing_table.c.durationSource.server_default.arg == "manual"


def test_password_reset_code_constraints_and_indexes() -> None:
    user_table = Base.metadata.tables["user"]
    reset_table = Base.metadata.tables["passwordResetCodes"]

    assert user_table.c.authVersion.nullable is False
    assert user_table.c.authVersion.default.arg == 1
    assert user_table.c.authVersion.server_default.arg == "1"
    assert reset_table.c.codeHash.nullable is False
    assert isinstance(reset_table.c.invalidatedAt.type, DateTime)
    assert reset_table.c.invalidatedAt.nullable is True
    assert reset_table.c.invalidatedAt.default is None
    assert reset_table.c.invalidatedAt.server_default is None
    assert isinstance(reset_table.c.purpose.type, Enum)
    assert reset_table.c.purpose.type.name == "password_reset_purpose"
    assert set(reset_table.c.purpose.type.enums) == {
        "password_reset",
        "email_verification",
    }
    assert reset_table.c.purpose.nullable is False
    assert reset_table.c.purpose.default.arg is PasswordResetPurpose.PASSWORD_RESET
    assert reset_table.c.purpose.server_default.arg == "password_reset"
    assert "code" not in reset_table.c
    assert "rawCode" not in reset_table.c
    assert reset_table.c.failedAttempts.default.arg == 0
    assert reset_table.c.failedAttempts.server_default.arg == "0"
    reset_fk = next(iter(reset_table.foreign_keys))
    assert reset_fk.target_fullname == "user.id"
    assert reset_fk.ondelete == "CASCADE"
    assert {index.name for index in reset_table.indexes} == {
        "ix_passwordResetCodes_userId_createdAt",
        "ix_passwordResetCodes_requestedIp_createdAt",
        "ix_passwordResetCodes_expiresAt",
        "ix_passwordResetCodes_usedAt",
        "ix_passwordResetCodes_userId_invalidatedAt",
        "ix_passwordResetCodes_codeHash",
    }

    invalidation_index = next(
        index
        for index in reset_table.indexes
        if index.name == "ix_passwordResetCodes_userId_invalidatedAt"
    )
    assert [column.name for column in invalidation_index.columns] == [
        "userId",
        "invalidatedAt",
    ]


def test_user_email_verified_at_is_optional_without_a_default() -> None:
    user_table = Base.metadata.tables["user"]

    assert isinstance(user_table.c.emailVerifiedAt.type, DateTime)
    assert user_table.c.emailVerifiedAt.nullable is True
    assert user_table.c.emailVerifiedAt.default is None
    assert user_table.c.emailVerifiedAt.server_default is None
    assert User().emailVerifiedAt is None


def test_password_reset_code_invalidated_at_defaults_to_none() -> None:
    reset_code = PasswordResetCode()

    assert reset_code.invalidatedAt is None


def test_password_reset_code_purpose_defaults_and_rejects_invalid_values() -> None:
    engine = create_engine("sqlite+pysqlite://")
    Base.metadata.create_all(engine)
    now = datetime(2026, 11, 15)

    with Session(engine) as db:
        valid = PasswordResetCode(
            userId=1,
            codeHash="hashed-code",
            expiresAt=now,
            requestedIp="127.0.0.1",
            createdAt=now,
            updatedAt=now,
        )
        db.add(valid)
        db.flush()
        assert valid.purpose is PasswordResetPurpose.PASSWORD_RESET

        db.add(
            PasswordResetCode(
                userId=1,
                codeHash="another-hash",
                expiresAt=now,
                requestedIp="127.0.0.1",
                createdAt=now,
                updatedAt=now,
                purpose="passwordReset",
            )
        )
        with pytest.raises(StatementError):
            db.flush()

    engine.dispose()
