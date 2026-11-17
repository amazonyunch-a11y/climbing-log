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

export type PasswordResetRequest = {
  email: string;
};

export type PasswordResetConfirmRequest = {
  email: string;
  code: string;
  new_password: string;
  new_password_confirm: string;
};

export type AuthMessageResponse = {
  message: string;
};

export type EmailVerificationRequest = {
  email: string;
};

export type EmailVerificationConfirmRequest = {
  email: string;
  code: string;
};

export type EmailVerificationConfirmResponse = {
  message: string;
  verified: boolean;
};
