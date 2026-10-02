export interface Question {
  id?: number;
  question_number: number;
  question_text: string;
  options: string[];
  correct_option: string;
  marks?: number;
  negative_marks?: number;
}

export interface Exam {
  id: string;
  title: string;
  subject: string;
  date_str?: string;
  instructions?: string;
  roll_length: number;
  options_per_question: number;
  layout_type: 'split' | 'duplex';
  positive_marks: number;
  negative_marks: number;
  created_at: string;
  questions: Question[];
  submissions_count?: number;
}

export interface StudentAnswer {
  question_number: number;
  detected_option: string | null;
  correct_option: string;
  is_correct: boolean;
  confidence: number;
  is_flagged: boolean;
}

export interface Submission {
  id: string;
  exam_id: string;
  student_roll: string;
  student_name: string;
  total_score: number;
  max_score: number;
  percentage: number;
  correct_count: number;
  incorrect_count: number;
  unanswered_count: number;
  status: 'graded' | 'flagged_review' | 'overridden';
  original_image_path?: string;
  overlay_image_path?: string;
  created_at: string;
  is_duplicate?: boolean;
  duplicate_message?: string;
  answers: StudentAnswer[];
}

export interface ScannerInfo {
  id: string;
  name: string;
  type: string;
}

export interface ScannerStatus {
  online: boolean;
  physical_scanner_connected: boolean;
  scanners: ScannerInfo[];
  supported_sources: string[];
  supported_dpis: number[];
}
