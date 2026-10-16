from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import configure_mappers

from app.db.base import Base
from app.models.climbing_session import ClimbingSession
from app.models.grade_logs import GradeLogs
from app.models.gyms import Gyms
from app.models.user import User
from app.models.user_profile import UserProfile
from app.models.videos import Videos
from app.models.stopwatch_session import StopwatchSession


def test_metadata_matches_erd_tables_and_columns() -> None:
    expected_columns = {
        "user": {
            "id": Integer,
            "email": String,
            "passwordHash": String,
            "nickname": String,
            "createdAt": String,
            "updatedAt": DateTime,
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
            "startedAt": DateTime,
            "endedAt": DateTime,
            "elapsedSeconds": Integer,
            "status": String,
            "createdAt": DateTime,
            "updatedAt": DateTime,
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
        "stopwatchSessions": {"userId": "user.id"},
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
    assert UserProfile.user.property.mapper.class_ is User
    assert Gyms.user.property.mapper.class_ is User
    assert Gyms.sessions.property.mapper.class_ is ClimbingSession
    assert ClimbingSession.user.property.mapper.class_ is User
    assert ClimbingSession.gym.property.mapper.class_ is Gyms
    assert ClimbingSession.grade_logs.property.mapper.class_ is GradeLogs
    assert ClimbingSession.videos.property.mapper.class_ is Videos
    assert GradeLogs.session.property.mapper.class_ is ClimbingSession
    assert Videos.user.property.mapper.class_ is User
    assert Videos.session.property.mapper.class_ is ClimbingSession
    assert StopwatchSession.user.property.mapper.class_ is User
