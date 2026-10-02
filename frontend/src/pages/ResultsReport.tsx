import React, { useState, useEffect } from 'react';
import { 
  BarChart3, Download, FileSpreadsheet, Search, Eye, 
  ArrowLeft, CheckCircle2, XCircle, AlertTriangle, Users 
} from 'lucide-react';
import { Exam, Submission } from '../types';
import { apiClient } from '../api/client';
import { VisualOverlayModal } from '../components/VisualOverlayModal';

interface Props {
  examId: string;
  onBack: () => void;
}

export const ResultsReport: React.FC<Props> = ({ examId, onBack }) => {
  const [exam, setExam] = useState<Exam | null>(null);
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [searchRoll, setSearchRoll] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);
  const [inspectedSub, setInspectedSub] = useState<Submission | null>(null);

  useEffect(() => {
    loadData();
  }, [examId]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [exData, subsData] = await Promise.all([
        apiClient.getExam(examId),
        apiClient.listSubmissions(examId),
      ]);
      setExam(exData);
      setSubmissions(subsData);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const filteredSubs = submissions.filter((s) =>
    s.student_roll.toLowerCase().includes(searchRoll.toLowerCase())
  );

  // Statistics
  const totalStudents = submissions.length;
  const avgScore = totalStudents > 0
    ? (submissions.reduce((acc, s) => acc + s.total_score, 0) / totalStudents).toFixed(1)
    : '0.0';
  const maxScoreScored = totalStudents > 0
    ? Math.max(...submissions.map((s) => s.total_score)).toFixed(1)
    : '0.0';
  const minScoreScored = totalStudents > 0
    ? Math.min(...submissions.map((s) => s.total_score)).toFixed(1)
    : '0.0';
  const passCount = submissions.filter((s) => s.percentage >= 40).length;
  const passRate = totalStudents > 0 ? Math.round((passCount / totalStudents) * 100) : 0;

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-12">
      {/* Top action bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <button
          onClick={onBack}
          className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-800 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Dashboard</span>
        </button>

        <div className="flex flex-wrap items-center gap-2">
          <a
            href={apiClient.getExcelExportUrl(examId)}
            download
            className="px-3.5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold shadow-sm transition-all flex items-center gap-1.5"
          >
            <FileSpreadsheet className="w-3.5 h-3.5" />
            <span>Export to Excel (.xlsx)</span>
          </a>

          <a
            href={apiClient.getCsvExportUrl(examId)}
            download
            className="px-3.5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-semibold transition-colors flex items-center gap-1.5"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Download CSV</span>
          </a>
        </div>
      </div>

      {/* Exam Header */}
      {exam && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-sky-100 text-sky-800 font-mono">
                {exam.id}
              </span>
              <h2 className="text-xl font-extrabold text-slate-900 mt-1">{exam.title}</h2>
              <p className="text-xs text-slate-500 mt-1">
                Subject: <strong className="text-slate-700">{exam.subject}</strong> • Total Questions:{' '}
                <strong className="text-slate-700">{exam.questions.length}</strong> • Date:{' '}
                {exam.date_str || 'N/A'}
              </p>
            </div>

            <a
              href={apiClient.getPdfUrl(exam.id)}
              target="_blank"
              rel="noreferrer"
              className="px-3.5 py-2 bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-700 rounded-xl text-xs font-semibold self-start md:self-auto flex items-center gap-1.5 transition-colors"
            >
              <Download className="w-3.5 h-3.5 text-slate-500" />
              <span>Print Blank OMR Sheets</span>
            </a>
          </div>

          {/* Stat Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-6 pt-6 border-t border-slate-100">
            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/60">
              <span className="text-[11px] font-medium text-slate-500 flex items-center gap-1">
                <Users className="w-3.5 h-3.5" /> Students Graded
              </span>
              <p className="text-xl font-bold text-slate-900 mt-1">{totalStudents}</p>
            </div>

            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/60">
              <span className="text-[11px] font-medium text-slate-500 flex items-center gap-1">
                <BarChart3 className="w-3.5 h-3.5 text-sky-600" /> Class Average
              </span>
              <p className="text-xl font-bold text-sky-700 mt-1">
                {avgScore} <span className="text-xs font-normal text-slate-500">/ {exam.questions.length * exam.positive_marks}</span>
              </p>
            </div>

            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/60">
              <span className="text-[11px] font-medium text-slate-500 flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> Highest Score
              </span>
              <p className="text-xl font-bold text-emerald-700 mt-1">{maxScoreScored}</p>
            </div>

            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/60">
              <span className="text-[11px] font-medium text-slate-500">Pass Rate (&ge;40%)</span>
              <p className="text-xl font-bold text-indigo-700 mt-1">{passRate}%</p>
            </div>
          </div>
        </div>
      )}

      {/* Gradebook Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-50/50">
          <div>
            <h3 className="text-sm font-bold text-slate-800">Student Gradebook</h3>
            <p className="text-[11px] text-slate-500">Full score breakdown and evaluation audit trail</p>
          </div>

          <div className="relative w-full sm:w-64">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              value={searchRoll}
              onChange={(e) => setSearchRoll(e.target.value)}
              placeholder="Search by Roll Number..."
              className="w-full pl-9 pr-3 py-1.5 bg-white border border-slate-300 rounded-xl text-xs outline-none focus:ring-2 focus:ring-sky-500"
            />
          </div>
        </div>

        {loading ? (
          <div className="py-12 text-center text-slate-400 text-xs">Loading submissions...</div>
        ) : filteredSubs.length === 0 ? (
          <div className="py-12 text-center text-slate-400 text-xs">
            {searchRoll ? 'No students matched this roll number.' : 'No sheets evaluated yet.'}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-600">
              <thead className="bg-slate-50 text-[10px] uppercase font-bold text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="px-4 py-3">Roll No</th>
                  <th className="px-4 py-3">Score</th>
                  <th className="px-4 py-3">Percentage</th>
                  <th className="px-4 py-3 text-center">Correct</th>
                  <th className="px-4 py-3 text-center">Wrong</th>
                  <th className="px-4 py-3 text-center">Blank</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-medium">
                {filteredSubs.map((s) => (
                  <tr key={s.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-4 py-3 font-mono font-bold text-slate-900">
                      {s.student_roll}
                    </td>
                    <td className="px-4 py-3 font-bold text-slate-800">
                      {s.total_score} <span className="text-slate-400 font-normal">/ {s.max_score}</span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-16 bg-slate-200 rounded-full h-1.5 overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              s.percentage >= 75
                                ? 'bg-emerald-500'
                                : s.percentage >= 40
                                ? 'bg-sky-500'
                                : 'bg-rose-500'
                            }`}
                            style={{ width: `${Math.min(100, Math.max(0, s.percentage))}%` }}
                          />
                        </div>
                        <span className="font-semibold text-slate-700">{s.percentage}%</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-center font-semibold text-emerald-700">
                      {s.correct_count}
                    </td>
                    <td className="px-4 py-3 text-center font-semibold text-rose-700">
                      {s.incorrect_count}
                    </td>
                    <td className="px-4 py-3 text-center text-slate-400">
                      {s.unanswered_count}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full border ${
                          s.status === 'graded'
                            ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                            : s.status === 'flagged_review'
                            ? 'bg-amber-50 text-amber-700 border-amber-200'
                            : 'bg-indigo-50 text-indigo-700 border-indigo-200'
                        }`}
                      >
                        {s.status.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => setInspectedSub(s)}
                        className="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold inline-flex items-center gap-1 transition-colors"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        <span>Inspect</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Visual Overlay Modal */}
      {inspectedSub && (
        <VisualOverlayModal
          submission={inspectedSub}
          onClose={() => setInspectedSub(null)}
          onUpdated={(updated) => {
            setSubmissions((prev) => prev.map((s) => (s.id === updated.id ? updated : s)));
          }}
        />
      )}
    </div>
  );
};
