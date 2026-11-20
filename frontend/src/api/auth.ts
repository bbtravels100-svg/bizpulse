import { apiGet, apiPost, setAuthToken } from './client';

export interface AuthenticatedUser {
  id: string;
  email: string;
  name: string;
  role: string;
  department: string;
  is_active: boolean;
  created_at: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in_seconds: number;
  user: AuthenticatedUser;
}

export interface MessageResponse {
  message: string;
  status: string;
}

/** Authenticate with email and password. Sets in-memory token and HttpOnly cookie. */
export async function loginUser(email: string, password: string): Promise<LoginResponse> {
  const data = await apiPost<LoginResponse>('/api/auth/login', { email, password });
  if (data?.access_token) {
    setAuthToken(data.access_token);
  }
  return data;
}

/** Invalidate session and clear authentication cookie. */
export async function logoutUser(): Promise<MessageResponse> {
  try {
    const data = await apiPost<MessageResponse>('/api/auth/logout', {});
    return data;
  } finally {
    setAuthToken(null);
  }
}

/** Retrieve current authenticated user profile using HttpOnly cookie or in-memory token. */
export async function getCurrentUser(): Promise<AuthenticatedUser> {
  return apiGet<AuthenticatedUser>('/api/auth/me');
}
