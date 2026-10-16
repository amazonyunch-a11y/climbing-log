# Climbing Log MVP

클라이밍 운동 세션, 난이도 기록, 영상, 통계와 운동 스톱워치를 관리하는 모바일 MVP입니다.

- Backend: FastAPI, SQLAlchemy, PostgreSQL, Alembic
- Frontend: Expo SDK 57, React Native, Expo Router, React Native Paper
- Video storage: Supabase Storage
- Authentication: FastAPI JWT

## 프로젝트 구조

```text
backend/   FastAPI API, SQLAlchemy models, Alembic migrations, pytest
frontend/  Expo/React Native 모바일 앱
```

## 사전 준비

- Python 3.11 이상
- PostgreSQL
- Node.js 22.13 이상 및 npm
- Expo Go 또는 iOS/Android 개발 환경
- 영상 기능을 사용할 경우 Supabase 프로젝트

## 1. Backend 실행

프로젝트 루트에서 가상환경을 생성하고 의존성을 설치합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
```

환경변수 예제를 복사합니다.

```powershell
Copy-Item backend/.env.example backend/.env
```

`backend/.env`에 로컬 PostgreSQL URL과 충분히 긴 임의의 JWT secret을 설정합니다. 실제 값은 Git에 커밋하지 않습니다.

DB를 생성한 다음 migration을 적용합니다.

```powershell
Set-Location backend
alembic upgrade head
```

API 서버를 실행합니다. Expo Go 실기기에서 접근하려면 `0.0.0.0`으로 바인딩하고 Windows 방화벽에서 해당 포트를 허용해야 합니다.

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API 문서는 서버 실행 후 `http://localhost:8000/docs`에서 확인할 수 있습니다.

## 2. Frontend 실행

새 터미널에서 다음을 실행합니다.

```powershell
Set-Location frontend
Copy-Item .env.example .env
npm ci
npm run start
```

`frontend/.env`의 `EXPO_PUBLIC_API_BASE_URL`은 실행 환경에 맞게 설정합니다.

- Android emulator: `http://10.0.2.2:8000`
- Expo Go 실기기: `http://<개발 PC의 LAN IP>:8000`
- iOS simulator: 일반적으로 `http://127.0.0.1:8000`

`EXPO_PUBLIC_` 변수는 앱 번들에 포함될 수 있습니다. Supabase service-role key, DB URL, JWT secret을 절대 넣지 마세요.

## 3. 환경변수

Backend 전용:

| 이름 | 용도 |
| --- | --- |
| `DATABASE_URL` | PostgreSQL SQLAlchemy 연결 URL |
| `JWT_SECRET_KEY` | FastAPI JWT 서명 키 |
| `JWT_ALGORITHM` | JWT 알고리즘, 기본 `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | access token 유효시간 |
| `SUPABASE_URL` | Supabase 프로젝트 URL |
| `SUPABASE_STORAGE_BUCKET` | 영상 bucket 이름 |
| `SUPABASE_SERVICE_ROLE_KEY` | Storage 삭제 전용 서버 비밀키 |

Frontend 공개 설정:

| 이름 | 용도 |
| --- | --- |
| `EXPO_PUBLIC_API_BASE_URL` | FastAPI 주소 |
| `EXPO_PUBLIC_SUPABASE_URL` | Supabase 프로젝트 URL |
| `EXPO_PUBLIC_SUPABASE_ANON_KEY` | 모바일 직접 업로드용 공개 anon key |
| `EXPO_PUBLIC_SUPABASE_STORAGE_BUCKET` | 영상 bucket 이름 |

## 4. Supabase Storage 설정

1. Supabase Storage에 `climbing-videos` 같은 bucket을 생성합니다.
2. backend와 frontend의 bucket 환경변수에 동일한 이름을 설정합니다.
3. 현재 앱은 public file URL로 영상을 재생하므로 MVP bucket을 Public으로 설정합니다.
4. bucket의 최대 파일 크기를 50MB로 설정하고 `video/mp4`, `video/quicktime`, `video/x-m4v`만 허용하는 것을 권장합니다.
5. 모바일은 anon key로 직접 업로드하므로 `storage.objects`에 해당 bucket만 허용하는 `INSERT` 정책이 필요합니다. Public bucket도 업로드 권한은 별도 정책이 필요합니다.
6. `SUPABASE_SERVICE_ROLE_KEY`는 오직 `backend/.env`에만 설정합니다. 백엔드는 사용자 소유권을 확인한 뒤 이 키로 Storage 파일을 삭제합니다.

현재 MVP는 Supabase Auth를 사용하지 않습니다. 따라서 anon 업로드 정책은 테스트/MVP 용도로만 최소 범위로 제한하고, 운영 전에는 signed upload URL 또는 서버 중계 업로드 방식으로 강화하는 것을 권장합니다.

## 5. 테스트

Backend 전체 테스트:

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m pytest
```

Frontend 타입 검사:

```powershell
Set-Location frontend
npm run typecheck
```

현재 frontend에는 별도 자동화 테스트와 ESLint 설정이 없습니다.

## datetime 정책

- 사용자가 입력하고 앱에서 보는 시간: KST (`Asia/Seoul`)
- DB 저장과 API datetime 응답: UTC
- Calendar 날짜 기준: KST `sessionDate`
- 새벽 운동으로 UTC 날짜가 달라져도 Calendar는 `sessionDate`를 사용합니다.

## 구현된 MVP 기능

- 이메일 회원가입, 로그인, 로그아웃과 JWT 인증
- 암장 등록, 조회, 수정, 삭제
- Calendar 월간 기록 표시와 날짜별 세션 조회
- 운동 세션 생성, 상세 조회, 수정, 삭제
- 난이도별 시도/완등 기록 CRUD와 합계 계산
- 주간/월간 summary, 난이도별, 암장별 통계
- Supabase Storage 영상 다중 업로드, 재생, 실제 파일과 metadata 삭제
- 세션당 영상 최대 5개, 파일당 최대 50MB 제한
- 별도 stopwatch 엔터티 기반 시작, 일시정지, 이어하기, 초기화
- 네이비·블루 기반 모바일 UI와 loading/error/empty 상태

## 미구현 또는 향후 확장

- 비밀번호 재설정, 이메일 인증, refresh token, 소셜 로그인
- 프로필 정보 수정
- stopwatch 완료 기록을 climbing session으로 전환하는 기능
- 영상 지연 삭제, soft delete, 정리 scheduler
- private bucket과 signed URL 기반 영상 접근
- Supabase Auth 연동 또는 더 안전한 업로드 권한 모델
- push notification, 오프라인 동기화
- frontend 단위/E2E 테스트와 CI/CD
- 운영 배포용 로깅, 모니터링, rate limiting

## 보안 체크

- `backend/.env`와 `frontend/.env`는 커밋하지 않습니다.
- service-role key, DB URL, JWT secret은 서버 환경에만 둡니다.
- GitHub push 전 `git status`와 `git ls-files`로 `.env` 포함 여부를 다시 확인합니다.
