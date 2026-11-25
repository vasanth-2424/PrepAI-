export interface HealthResponse {
  status: string;
  service: string;
  environment: string;
  version: string;
}

export interface ApiError {
  detail: string;
  success: false;
}

export interface User {
  id: number;
  name: string;
  email: string;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface AuthResponse extends TokenResponse {
  user: User;
}

export interface RegisterRequest {
  name: string;
  email: string;
  password: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface ResumeUploadResponse {
  resume_id: number;
  text: string;
  page_count: number;
  character_count: number;
}

export interface ResumeAnalysis {
  name: string;
  skills: string[];
  projects: string[];
  education: string[];
  experience: string[];
  certifications: string[];
}

export interface ResumeAnalyzeResponse {
  analysis: ResumeAnalysis;
}

export interface ResumeDetailResponse {
  id: number;
  filename: string;
  extracted_text: string;
  uploaded_at: string;
  skills: string[];
  projects: string[];
}

export interface StoredResumeItem {
  id: number;
  filename: string;
  uploaded_at: string;
  analysis: ResumeAnalysis;
  questions: InterviewQuestion[];
}

export type QuestionDifficulty = 'Beginner' | 'Intermediate' | 'Advanced';
export type QuestionType = 'technical' | 'project' | 'problem_solving' | 'hr';

export interface InterviewQuestion {
  category: string;
  difficulty: QuestionDifficulty;
  question: string;
  question_type: QuestionType;
}

export interface QuestionsGenerateResponse {
  questions: InterviewQuestion[];
}

export interface AnalysisResult {
  analysis: ResumeAnalysis;
  questions: InterviewQuestion[];
}

export type AnalysisStep = 'upload' | 'analyze' | 'generate';

// ---------------------------------------------------------------------------
// Stage 2 & 3 — Mock Interview & Adaptive System
// ---------------------------------------------------------------------------

export type SessionStatus = 'in_progress' | 'completed';
export type SessionMode = 'standard' | 'adaptive' | 'project_deep_dive';

export interface SessionQuestion {
  index: number;
  category: string;
  difficulty: QuestionDifficulty;
  question: string;
  question_type: QuestionType;
}

export interface SessionCreateRequest {
  mode?: SessionMode;
  questions?: InterviewQuestion[];
}

export interface SessionCreateResponse {
  session_id: number;
  mode: SessionMode;
  questions: SessionQuestion[];
}

export type HelpType = 'small_hint' | 'explain_concept' | 'show_approach' | 'suggested_answer';

export interface HelpRequest {
  question_text: string;
  question_category?: string;
  question_difficulty?: string;
  question_type?: string;
  help_type: HelpType;
}

export interface HelpResponse {
  help_type: HelpType;
  content: string;
  penalty: number;
}

export interface SubmitAnswerRequest {
  question_text: string;
  question_category?: string;
  question_difficulty?: string;
  question_type?: string;
  answer_text: string;
  assistance_used?: HelpType[];
}

export interface EvaluationResponse {
  answer_id: number;
  score: number;
  raw_score: number;
  adjusted_score: number;
  total_penalty: number;
  technical_accuracy: string;
  clarity: string;
  completeness: string;
  feedback: string;
  suggested_answer: string;
  assistance_used?: HelpType[];
}

export interface DimensionScore {
  dimension: string;
  score: number;
  details: string;
}

export interface FinalReport {
  overall_score: number;
  independent_score: number;
  independent_ratio: number;
  dimensions: DimensionScore[];
  strengths: string[];
  weaknesses: string[];
  mentor_feedback: string;
  recommended_improvements: string[];
  next_topics_to_practice: string[];
}

export interface AnswerResult {
  answer_id: number;
  question_text: string;
  question_category: string;
  question_difficulty: string;
  question_type: string;
  answer_text: string;
  score: number | null;
  raw_score?: number | null;
  adjusted_score?: number | null;
  assistance_used?: HelpType[];
  technical_accuracy: string | null;
  clarity: string | null;
  completeness: string | null;
  feedback: string | null;
  suggested_answer: string | null;
}

export interface SessionResultResponse {
  session_id: number;
  status: SessionStatus;
  mode: SessionMode;
  total_questions: number;
  average_score: number | null;
  answers: AnswerResult[];
  final_report?: FinalReport | null;
}

export type InterviewMode = 'text' | 'voice';
