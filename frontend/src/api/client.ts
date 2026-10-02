import { Exam, Submission, ScannerStatus } from '../types';

const API_BASE = '/api';
const SCANNER_BRIDGE_URL = 'http://127.0.0.1:8765';

export const apiClient = {
  // Exams
  async listExams(): Promise<Exam[]> {
    const res = await fetch(`${API_BASE}/exams`);
    if (!res.ok) throw new Error('Failed to fetch exams');
    return res.json();
  },

  async getExam(id: string): Promise<Exam> {
    const res = await fetch(`${API_BASE}/exams/${id}`);
    if (!res.ok) throw new Error('Failed to fetch exam');
    return res.json();
  },

  async createExam(data: any): Promise<Exam> {
    const res = await fetch(`${API_BASE}/exams`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to create exam');
    }
    return res.json();
  },

  async deleteExam(id: string): Promise<void> {
    const res = await fetch(`${API_BASE}/exams/${id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Failed to delete exam');
  },

  async bulkParse(text: string): Promise<any> {
    const res = await fetch(`${API_BASE}/exams/bulk-parse`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ raw_text: text }),
    });
    if (!res.ok) throw new Error('Failed to parse text');
    return res.json();
  },

  getPdfUrl(examId: string): string {
    return `${API_BASE}/exams/${examId}/pdf`;
  },

  // Grading
  async uploadSheet(file: File, examId?: string, studentName?: string, allowOverwrite?: boolean): Promise<Submission> {
    const formData = new FormData();
    formData.append('file', file);
    if (examId) formData.append('exam_id', examId);
    if (studentName) formData.append('student_name', studentName);
    if (allowOverwrite) formData.append('allow_overwrite', 'true');

    const res = await fetch(`${API_BASE}/grading/upload`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Evaluation failed');
    }
    return res.json();
  },

  async gradeBase64(base64Image: string, examId?: string, studentName?: string, allowOverwrite?: boolean): Promise<Submission> {
    const res = await fetch(`${API_BASE}/grading/base64`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        image_base64: base64Image,
        exam_id: examId,
        student_name: studentName || 'Student',
        allow_overwrite: allowOverwrite || false,
      }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Evaluation failed');
    }
    return res.json();
  },

  // Submissions
  async listSubmissions(examId: string): Promise<Submission[]> {
    const res = await fetch(`${API_BASE}/submissions/exam/${examId}`);
    if (!res.ok) throw new Error('Failed to fetch submissions');
    return res.json();
  },

  async getSubmission(subId: string): Promise<Submission> {
    const res = await fetch(`${API_BASE}/submissions/${subId}`);
    if (!res.ok) throw new Error('Failed to fetch submission');
    return res.json();
  },

  async overrideAnswer(subId: string, questionNumber: number, newOption: string): Promise<Submission> {
    const res = await fetch(`${API_BASE}/submissions/${subId}/override`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question_number: questionNumber,
        new_option: newOption,
      }),
    });
    if (!res.ok) throw new Error('Failed to override answer');
    return res.json();
  },

  getExcelExportUrl(examId: string): string {
    return `${API_BASE}/submissions/exam/${examId}/export/excel`;
  },

  getCsvExportUrl(examId: string): string {
    return `${API_BASE}/submissions/exam/${examId}/export/csv`;
  },

  // Local Scanner Bridge Client
  async checkScannerBridge(): Promise<ScannerStatus | null> {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 2000);
      const res = await fetch(`${SCANNER_BRIDGE_URL}/status`, {
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
      if (res.ok) {
        return res.json();
      }
    } catch {
      // Bridge is not running
    }
    return null;
  },

  async triggerScannerScan(params: {
    deviceId?: string;
    source?: 'flatbed' | 'feeder';
    dpi?: number;
    color?: string;
    useEmulated?: boolean;
  }): Promise<string[]> {
    const res = await fetch(`${SCANNER_BRIDGE_URL}/scan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        device_id: params.deviceId,
        source: params.source || 'flatbed',
        dpi: params.dpi || 200,
        color: params.color || 'gray',
        use_emulated: params.useEmulated || false,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Scanner acquisition failed');
    }
    const data = await res.json();
    return data.pages || [];
  },
};
