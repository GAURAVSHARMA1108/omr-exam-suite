import React, { useEffect, useState } from 'react';
import { PlusCircle, FileText, CheckSquare, BarChart3, Download, Trash2, Calendar, BookOpen, Layers } from 'lucide-react';
import { Exam } from '../types';
import { apiClient } from '../api/client';

interface Props {
  onSelectExam: (examId: string, action: 'grade' | 'results') => void;
  onNavigateCreate: () => void;
}

export const Dashboard: React.FC<Props> = ({ onSelectExam, onNavigateCreate }) => {
  const [exams, setExams] = useState<Exam[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchExams = async () => {
    setLoading(true);
    try {
      const data = await apiClient.listExams();
      setExams(data);
    } catch (e: any) {
      setError(e.message || 'Failed to load exams');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchExams();
  }, []);

  const handleDelete = async (id: string, title: string) => {
    if (!window.confirm(`Are you sure you want to delete "${title}"?`)) return;
    try {
      await apiClient.deleteExam(id);
      fetchExams();
    } catch (e: any) {
      alert(e.message || 'Failed to delete');
    }
  };

  return (
    <div className="space-y-6">
      {/* Hero Banner */}
      <div className="bg-gradient-to-r from-sky-800 via-sky-700 to-indigo-800 rounded-2xl p-6 sm:p-8 text-white shadow-xl relative overflow-hidden">
        <div className="relative z-10 max-w-2xl">
          <span className="px-2.5 py-1 rounded-full bg-white/20 backdrop-blur-sm text-xs font-semibold uppercase tracking-wider text-sky-100">
            Intelligent OMR Suite
          </span>
          <h2 className="text-2xl sm:text-3xl font-extrabold mt-3 tracking-tight">
            Create Print-Ready Tests & Grade Sheets Instantly
          </h2>
          <p className="mt-2 text-sm text-sky-100/90 leading-relaxed">
            Generate high-precision OMR answer sheets with integrated question papers. Grade batches of tests using connected document scanners (flatbed/ADF) or phone camera photos.
          </p>
          <div className="mt-5 flex flex-wrap gap-3">
            <button
              onClick={onNavigateCreate}
              className="px-4 py-2.5 bg-white text-sky-900 hover:bg-sky-50 rounded-xl text-xs font-bold shadow-md hover:shadow-lg transition-all flex items-center gap-2"
            >
              <PlusCircle className="w-4 h-4 text-sky-600" />
              <span>Create New Test</span>
            </button>
            <button
              onClick={() => onSelectExam(exams[0]?.id || '', 'grade')}
              disabled={exams.length === 0}
              className="px-4 py-2.5 bg-sky-600/60 hover:bg-sky-600/80 border border-white/20 text-white rounded-xl text-xs font-bold backdrop-blur-sm transition-all flex items-center gap-2 disabled:opacity-40"
            >
              <CheckSquare className="w-4 h-4" />
              <span>Start Grading</span>
            </button>
          </div>
        </div>
      </div>

      {/* Exams List Section */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-bold text-slate-900">Your Tests & Exams</h3>
            <p className="text-xs text-slate-500">Manage questions, download ready-to-print PDFs, and inspect grades</p>
          </div>
          <button
            onClick={onNavigateCreate}
            className="px-3.5 py-2 bg-sky-600 hover:bg-sky-700 text-white rounded-xl text-xs font-semibold shadow-sm flex items-center gap-1.5 transition-colors"
          >
            <PlusCircle className="w-3.5 h-3.5" />
            <span>Create Test</span>
          </button>
        </div>

        {loading ? (
          <div className="py-16 text-center text-slate-400 text-sm">Loading exams...</div>
        ) : error ? (
          <div className="p-4 bg-rose-50 border border-rose-200 text-rose-700 rounded-xl text-xs">
            {error}
          </div>
        ) : exams.length === 0 ? (
          <div className="border-2 border-dashed border-slate-200 rounded-2xl p-12 text-center bg-white">
            <div className="w-12 h-12 rounded-2xl bg-sky-50 text-sky-600 flex items-center justify-center mx-auto mb-3">
              <FileText className="w-6 h-6" />
            </div>
            <h4 className="text-sm font-bold text-slate-800">No Tests Created Yet</h4>
            <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
              Create your first test by entering questions or pasting from Microsoft Word. The system will generate print-ready OMR sheets immediately.
            </p>
            <button
              onClick={onNavigateCreate}
              className="mt-4 px-4 py-2 bg-sky-600 text-white rounded-xl text-xs font-semibold hover:bg-sky-700 transition-colors inline-flex items-center gap-1.5"
            >
              <PlusCircle className="w-3.5 h-3.5" />
              <span>Create First Test</span>
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {exams.map((exam) => (
              <div
                key={exam.id}
                className="bg-white rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow p-5 flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-start justify-between">
                    <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 font-mono">
                      {exam.id}
                    </span>
                    <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200 flex items-center gap-1">
                      <Layers className="w-3 h-3" />
                      {exam.layout_type === 'split' ? 'Split View' : 'Duplex'}
                    </span>
                  </div>

                  <h4 className="text-base font-bold text-slate-900 mt-2.5 line-clamp-1">
                    {exam.title}
                  </h4>
                  <div className="mt-1 flex items-center gap-3 text-xs text-slate-500">
                    <span className="flex items-center gap-1">
                      <BookOpen className="w-3.5 h-3.5 text-slate-400" />
                      {exam.subject}
                    </span>
                    <span>•</span>
                    <span>{exam.questions.length} Questions</span>
                  </div>
                </div>

                <div className="mt-5 pt-4 border-t border-slate-100">
                  <div className="flex items-center justify-between text-xs text-slate-600 mb-3">
                    <span className="flex items-center gap-1 text-[11px] text-slate-400">
                      <Calendar className="w-3.5 h-3.5" />
                      {exam.date_str || 'No date'}
                    </span>
                    <span className="font-semibold text-slate-800">
                      {exam.submissions_count || 0} Graded
                    </span>
                  </div>

                  <div className="grid grid-cols-3 gap-1.5 pt-1">
                    <a
                      href={apiClient.getPdfUrl(exam.id)}
                      target="_blank"
                      rel="noreferrer"
                      className="px-2 py-2 bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-700 rounded-lg text-[11px] font-semibold text-center flex items-center justify-center gap-1 transition-colors"
                      title="Download Ready-to-Print PDF"
                    >
                      <Download className="w-3 h-3 text-slate-500" />
                      <span>Print PDF</span>
                    </a>

                    <button
                      onClick={() => onSelectExam(exam.id, 'grade')}
                      className="px-2 py-2 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 text-emerald-800 rounded-lg text-[11px] font-bold text-center flex items-center justify-center gap-1 transition-colors"
                    >
                      <CheckSquare className="w-3 h-3 text-emerald-600" />
                      <span>Grade</span>
                    </button>

                    <button
                      onClick={() => onSelectExam(exam.id, 'results')}
                      className="px-2 py-2 bg-sky-50 hover:bg-sky-100 border border-sky-200 text-sky-800 rounded-lg text-[11px] font-bold text-center flex items-center justify-center gap-1 transition-colors"
                    >
                      <BarChart3 className="w-3 h-3 text-sky-600" />
                      <span>Results</span>
                    </button>
                  </div>

                  <div className="mt-2 text-right">
                    <button
                      onClick={() => handleDelete(exam.id, exam.title)}
                      className="text-[11px] text-slate-400 hover:text-rose-600 transition-colors inline-flex items-center gap-1"
                    >
                      <Trash2 className="w-3 h-3" />
                      <span>Delete</span>
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
