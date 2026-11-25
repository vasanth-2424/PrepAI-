import { clearStoredToken, getStoredToken, setStoredToken } from '../auth/tokenStorage';
import { env } from '../config/env';
import type {
  ApiError,
  AuthResponse,
  EvaluationResponse,
  HealthResponse,
  HelpRequest,
  HelpResponse,
  InterviewQuestion,
  LoginRequest,
  QuestionsGenerateResponse,
  RegisterRequest,
  ResumeAnalysis,
  ResumeAnalyzeResponse,
  ResumeDetailResponse,
  ResumeUploadResponse,
  SessionCreateResponse,
  SessionMode,
  SessionQuestion,
  SessionResultResponse,
  SubmitAnswerRequest,
  TokenResponse,
  User,
} from '../types';

type UnauthorizedHandler = () => void;

class ApiClient {
  private baseUrl: string;
  private onUnauthorized: UnauthorizedHandler | null = null;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  setUnauthorizedHandler(handler: UnauthorizedHandler): void {
    this.onUnauthorized = handler;
  }

  getToken(): string | null {
    return getStoredToken();
  }

  setToken(token: string): void {
    setStoredToken(token);
  }

  clearToken(): void {
    clearStoredToken();
  }

  private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const token = getStoredToken();
    const headers = new Headers(options?.headers);

    if (token && !headers.has('Authorization')) {
      headers.set('Authorization', `Bearer ${token}`);
    }

    const response = await fetch(url, { ...options, headers });

    if (response.status === 401) {
      clearStoredToken();
      this.onUnauthorized?.();
    }

    if (!response.ok) {
      let errorMessage = `Request failed with status ${response.status}`;

      try {
        const errorBody = (await response.json()) as ApiError;
        errorMessage = errorBody.detail ?? errorMessage;
      } catch {
        // Response body is not JSON — use default message
      }

      throw new Error(errorMessage);
    }

    if (response.status === 204) {
      return undefined as T;
    }

    return response.json() as Promise<T>;
  }

  getHealth(): Promise<HealthResponse> {
    return this.request<HealthResponse>('/api/v1/health', {
      headers: { 'Content-Type': 'application/json' },
    });
  }

  register(payload: RegisterRequest): Promise<AuthResponse> {
    return this.request<AuthResponse>('/api/v1/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  }

  login(payload: LoginRequest): Promise<TokenResponse> {
    return this.request<TokenResponse>('/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  }

  getMe(): Promise<User> {
    return this.request<User>('/api/v1/auth/me', {
      headers: { 'Content-Type': 'application/json' },
    });
  }

  uploadResume(file: File): Promise<ResumeUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    return this.request<ResumeUploadResponse>('/api/v1/resume/upload', {
      method: 'POST',
      body: formData,
    });
  }

  listResumes(): Promise<ResumeDetailResponse[]> {
    return this.request<ResumeDetailResponse[]>('/api/v1/resume');
  }

  getResume(resumeId: number): Promise<ResumeDetailResponse> {
    return this.request<ResumeDetailResponse>(`/api/v1/resume/${resumeId}`);
  }

  updateResume(resumeId: number, filename: string): Promise<ResumeDetailResponse> {
    return this.request<ResumeDetailResponse>(`/api/v1/resume/${resumeId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filename }),
    });
  }

  deleteResume(resumeId: number): Promise<{ message: string; resume_id: number }> {
    return this.request<{ message: string; resume_id: number }>(`/api/v1/resume/${resumeId}`, {
      method: 'DELETE',
    });
  }

  analyzeResume(resumeId: number, text: string): Promise<ResumeAnalyzeResponse> {
    return this.request<ResumeAnalyzeResponse>('/api/v1/resume/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ resume_id: resumeId, text }),
    });
  }

  generateQuestions(analysis: ResumeAnalysis): Promise<QuestionsGenerateResponse> {
    return this.request<QuestionsGenerateResponse>('/api/v1/questions/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ analysis }),
    });
  }

  createInterviewSession(
    questions?: InterviewQuestion[],
    mode: SessionMode = 'standard',
  ): Promise<SessionCreateResponse> {
    return this.request<SessionCreateResponse>('/api/v1/interview/sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode, questions }),
    });
  }

  submitAnswer(sessionId: number, payload: SubmitAnswerRequest): Promise<EvaluationResponse> {
    return this.request<EvaluationResponse>(
      `/api/v1/interview/sessions/${sessionId}/answers`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      },
    );
  }

  getInterviewHelp(sessionId: number, payload: HelpRequest): Promise<HelpResponse> {
    return this.request<HelpResponse>(`/api/v1/interview/sessions/${sessionId}/help`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  }

  getNextQuestion(
    sessionId: number,
    currentIndex: number,
    projects: string[] = [],
    skills: string[] = [],
  ): Promise<SessionQuestion> {
    return this.request<SessionQuestion>(
      `/api/v1/interview/sessions/${sessionId}/next-question`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          current_index: currentIndex,
          projects,
          skills,
        }),
      },
    );
  }

  getSessionResults(sessionId: number): Promise<SessionResultResponse> {
    return this.request<SessionResultResponse>(
      `/api/v1/interview/sessions/${sessionId}/results`,
    );
  }

  completeSession(sessionId: number): Promise<void> {
    return this.request<void>(`/api/v1/interview/sessions/${sessionId}/complete`, {
      method: 'POST',
    });
  }
}

export const api = new ApiClient(env.apiBaseUrl);
