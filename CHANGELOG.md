# Changelog

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

### Auth/Profile 고도화 예정

- 회원가입 시 닉네임·이메일 중복 확인 UX
- 비밀번호 두 번 입력 및 일치 여부 확인
- Profile에서 비밀번호 변경
- 생년월일, 키, 몸무게, 리치 입력·수정 UX 개선
