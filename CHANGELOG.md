# Changelog

## v0.3.0 - 2026-11-17

### Added

- 회원가입 후 이메일 인증번호 발송·확인 화면과 미인증 계정 로그인 제한
- 비밀번호 재설정 인증번호 발송·확인 및 새 비밀번호 설정 화면
- 회원가입 비밀번호 확인 입력과 일치 여부 검증
- 닉네임 형식 검증, 대소문자를 구분하는 중복 방지와 이메일·닉네임 중복 오류 안내
- Profile 닉네임 변경과 생년월일·키·몸무게·팔 리치 입력·수정 UI

### Database

- `20261110_0006`: `user.nickname` unique 제약조건과 기존 중복 데이터 사전 점검
- `20261112_0007`: `user.authVersion`, `passwordResetCodes` 테이블 및 사용자·시각·코드 해시 관련 인덱스
- `20261112_0008`: 인증번호 `invalidatedAt`과 사용자별 무효화 시각 인덱스
- `20261115_0009`: 인증번호 `purpose` (`password_reset`, `email_verification`) 구분
- `20261115_0010`: `user.emailVerifiedAt` 및 기존 계정 인증 상태 보정

### Security

- 인증번호를 HMAC 해시로 저장하고 용도별로 분리
- 인증번호 만료·재사용·실패 횟수·재발급 제한 및 이전 번호 무효화
- 인증번호 요청 시 이메일 존재 여부를 동일한 응답으로 처리
- 비밀번호 재설정 후 `authVersion` 증가로 기존 JWT 무효화
- 서버 전용 Resend·코드 해시 비밀값을 환경변수로 설정하고 Git에서 실제 `.env` 제외

### Verified

- Backend pytest: 191개 통과, 경고 2건
- Frontend TypeScript 검사 통과
- Alembic history 및 연결된 DB의 `20261115_0010` head 확인
- Expo Doctor: 18/20 통과. `expo-font` 직접 의존성 누락과 Expo SDK 권장 버전 차이는 후속 점검 필요
- 이메일 발송과 Expo Go의 실제 기기 흐름은 이번 검사에서 수동 검증하지 않음

## v0.2.0 - 2026-11-07

### Added

- 카카오 지도 기반 암장 검색과 검색 결과의 암장명·주소 자동 입력
- Stopwatch 운동 종료 및 완료 기록 저장
- 일시정지·이어하기 후 누적 운동 시간 보존
- 완료된 Stopwatch의 pending 조회 및 세션 자동 연결
- 세션 생성 시 pending 기록 1건 자동 선택과 여러 건 중 사용자 선택
- 선택한 Stopwatch의 시작·종료 시간 자동 입력 및 수동 수정

### Changed

- Gym 등록 흐름에 지도 검색을 추가하고 직접 입력을 유지
- Stopwatch 완료 기록을 Calendar 세션과 연결하여 운동 시간을 표시하고 Statistics 집계에 반영
- UTC 저장·KST 표시 기준에서 Stopwatch 최초 시작 시각과 완료 시각을 구분
- Expo SDK 58로 프론트엔드 의존성 갱신

### Verified

- Backend pytest: 127개 통과, 경고 2건
- Frontend TypeScript 검사 통과
- Stopwatch start/pause/resume/finish 및 Session 자동 연결: 백엔드 테스트 통과
- Expo Go 주요 화면: 수동 확인 필요
- Expo Doctor: 18/20 통과. `expo-font` 직접 의존성 누락과 Expo SDK 권장 버전 차이 5건은 후속 점검 필요

## v0.1.0 - 2026-10-16

### Initial MVP

첫 배포 기준 커밋: `ba3f1f4efd9c34604fbc502b45359caf3c3dba77` (`chore: initialize Climbing Log monorepo`). 첫 배포 태그는 생성되지 않았습니다.

- 이메일 회원가입·로그인, JWT 인증, Profile 조회·수정
- Gym, Session, Grade Log CRUD
- Calendar 날짜별 세션 조회 및 주간·월간 Statistics
- Supabase Storage 영상 업로드·재생·삭제
- Stopwatch 시작·일시정지·이어하기·초기화
- UTC 저장·KST 화면 표시와 세션 날짜 기준 Calendar

## Next

### 계정 관리 및 운영 점검

- Profile에서 비밀번호 재설정 흐름으로 이동하는 계정 관리 UI
- 이메일 발송 서비스와 Expo Go 실기기에서 회원가입·재설정 흐름 검증
- `expo-font` 직접 의존성과 Expo SDK 권장 패키지 버전 점검
