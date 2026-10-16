# Climbing Log Backend

FastAPI, SQLAlchemy, PostgreSQL 기반 Climbing Log API입니다. 전체 설정은 프로젝트 루트 `README.md`도 참고하세요.

## 로컬 실행

프로젝트 루트에서 가상환경을 생성하고 활성화합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

의존성을 설치합니다.

```powershell
python -m pip install -r backend/requirements.txt
```

`backend/.env.example`을 `backend/.env`로 복사한 뒤 PostgreSQL, JWT, Supabase 설정을 입력합니다. `.env`와 service-role key는 커밋하지 않습니다.

```powershell
Copy-Item backend/.env.example backend/.env
```

DB를 만든 뒤 migration을 적용합니다.

```powershell
cd backend
alembic upgrade head
```

`backend`에서 API를 실행합니다.

```powershell
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

테스트를 실행합니다.

```powershell
..\.venv\Scripts\python.exe -m pytest
```

API 문서: `http://localhost:8000/docs`
