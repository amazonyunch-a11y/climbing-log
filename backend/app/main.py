from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.calendar import router as calendar_router
from app.api.grades import router as grades_router
from app.api.gyms import router as gyms_router
from app.api.profile import router as profile_router
from app.api.sessions import router as sessions_router
from app.api.statistics import router as statistics_router
from app.api.stopwatch import router as stopwatch_router
from app.api.videos import router as videos_router


app = FastAPI(title="Climbing Log API")
app.include_router(auth_router)
app.include_router(calendar_router)
app.include_router(gyms_router)
app.include_router(grades_router)
app.include_router(profile_router)
app.include_router(sessions_router)
app.include_router(statistics_router)
app.include_router(stopwatch_router)
app.include_router(videos_router)
