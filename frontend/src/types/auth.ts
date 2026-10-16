export type CurrentUser = {
  id: number;
  email: string;
  nickname: string;
};

export type LoginRequest = {
  email: string;
  password: string;
};

export type SignupRequest = LoginRequest & {
  nickname: string;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
};

export type SignupResponse = CurrentUser & {
  created_at: string;
};
