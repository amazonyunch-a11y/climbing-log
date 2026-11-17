const NICKNAME_PATTERN = /^(?=.*[A-Z])(?=.*[a-z])[A-Za-z0-9]{5,15}$/;

export const NICKNAME_RULE = '닉네임은 영문 대·소문자를 각각 1개 이상 포함한 5~15자의 영문·숫자만 사용할 수 있습니다.';

export function normalizeNickname(value: string): string {
  return value.replace(/^ +| +$/g, '');
}

export function validateNickname(value: string): string | undefined {
  const normalized = normalizeNickname(value);
  return normalized.match(NICKNAME_PATTERN)?.[0] === normalized ? undefined : NICKNAME_RULE;
}

export function nicknameApiError(message: string, status?: number): string {
  if (message === 'Nickname is already taken') return '이미 사용 중인 닉네임입니다.';
  if (message === 'Email is already registered') return '이미 가입된 이메일입니다.';
  if (status === 422) return NICKNAME_RULE;
  return message;
}
