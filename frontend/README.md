# Climbing Log Mobile

Expo SDK 57, Expo Router, React Native Paper 기반 모바일 앱입니다. 전체 기능과 Backend/Supabase 설정은 프로젝트 루트 `README.md`를 참고하세요.

## 실행

1. `Copy-Item .env.example .env`로 로컬 환경변수를 만듭니다.
2. `EXPO_PUBLIC_API_BASE_URL`을 실행 환경에 맞게 설정합니다.
   - Android emulator: `http://10.0.2.2:8000`
   - Expo Go / physical device: `http://<your-computer-LAN-IP>:8000`
3. 프로젝트 루트의 안내대로 FastAPI와 migration을 준비합니다.
4. 의존성을 설치하고 실행합니다.

```powershell
npm ci
npm run start
```

타입 검사:

```powershell
npm run typecheck
```

`EXPO_PUBLIC_*` 값은 앱 번들에서 공개될 수 있습니다. Supabase service-role key, DB URL, JWT secret을 이 앱에 넣지 마세요.
