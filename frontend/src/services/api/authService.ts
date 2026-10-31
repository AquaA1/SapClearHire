/**
 * ClearHire Authentication Service
 * Communicates directly with backend FastAPI auth endpoints:
 * - POST /api/v1/auth/login
 * - POST /api/v1/auth/register
 * - GET  /api/v1/auth/me
 */

import { apiClient } from './client';
import { User, LoginRequest, TokenResponse, CandidateRegisterRequest } from '../../contracts/models';

export const authService = {
  /**
   * Authenticate user with credentials to obtain a Bearer JWT.
   */
  async login(payload: LoginRequest): Promise<TokenResponse> {
    return apiClient.post<TokenResponse>('/auth/login', payload);
  },

  /**
   * Register a new candidate account.
   */
  async register(payload: CandidateRegisterRequest): Promise<User> {
    return apiClient.post<User>('/auth/register', payload);
  },

  /**
   * Fetch currently authenticated user identity and role.
   */
  async getMe(): Promise<User> {
    return apiClient.get<User>('/auth/me');
  },
};
