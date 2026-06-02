export interface User {
  user_id: string;
  email: string;
  name: string;
}

export interface LoginResponse {
  user_id: string;
  email: string;
  name: string;
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface RegisterResponse {
  message: string;
  email: string;
}
