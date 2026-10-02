import React, { useState, useEffect } from 'react';
import { X, Check, AlertTriangle, ZoomIn, ZoomOut, RotateCcw, Edit3, Award, HelpCircle, FileText } from 'lucide-react';
import { Submission } from '../types';
import { apiClient } from '../api/client';

interface Props {
  submission: Submission | null;
  onClose: () => void;
  onUpdated: (updatedSub: Submission) => void;
}

export const VisualOverlayModal: React.FC<Props> = ({ submission, onClose, onUpdated }) => {
  const [sub, setSub] = useState<Submission | null>(submission);
  const [zoom, setZoom] = useState<number>(1);
  const [editingQ, setEditingQ] = useState<number | null>(null);
  const [overrideOpt, setOverrideOpt] = useState<string>('');
  const [saving, setSaving] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<'sheet' | 'answers'>('sheet');

  useEffect(() => {
    setSub(submission);
    setZoom(1);
    setEditingQ(null);
  }, [submission]);

  if (!sub) return null;

  const handleSaveOverride = async (qNum: number) => {
    setSaving(true);
    try {
      const updated = await apiClient.overrideAnswer(sub.id, qNum, overrideOpt);
      setSub(updated);
      onUpdated(updated);
      setEditingQ(null);
    } catch (e: any) {
      alert(e.message || 'Override failed');
    } finally {
      setSaving(false);
    }
  };

  const overlayUrl = sub.overlay_image_path
    ? `/static/overlays/${sub.overlay_image_path.split(/[\\/]/).pop()}`
    : '';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-6 bg-slate-950/70 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white w-full max-w-6xl h-[94vh] sm:h-[92vh] rounded-2xl shadow-2xl border border-slate-200 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="px-4 sm:px-6 py-3 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between bg-slate-50/90 gap-2 sm:gap-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-xl bg-gradient-to-tr from-sky-500 to-indigo-600 text-white flex items-center justify-center font-bold text-xs sm:text-sm shadow-sm shrink-0">
                {sub.student_roll.slice(-2) || 'OMR'}
              </div>
              <div>
                <div className="flex items-center gap-1.5 flex-wrap">
                  <h2 className="text-sm sm:text-base font-bold text-slate-800">
                    Roll: <span className="font-mono text-sky-700">{sub.student_roll}</span>
                  </h2>
                  <span
                    className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.2 rounded-full border ${
                      sub.status === 'graded'
                        ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                        : sub.status === 'flagged_review'
                        ? 'bg-amber-50 text-amber-700 border-amber-200'
                        : 'bg-indigo-50 text-indigo-700 border-indigo-200'
                    }`}
                  >
                    {sub.status.replace('_', ' ')}
                  </span>
                </div>
                <p className="text-[11px] sm:text-xs text-slate-500 line-clamp-1">
                  Score: <strong className="text-slate-800">{sub.total_score}</strong>/{sub.max_score} ({sub.percentage}%) • {sub.correct_count} Correct, {sub.incorrect_count} Wrong
                </p>
              </div>
            </div>

            <button
              onClick={onClose}
              className="sm:hidden p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-200 rounded-lg"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="flex items-center justify-between sm:justify-end gap-2">
            {/* Zoom controls */}
            <div className="flex items-center bg-white border border-slate-200 rounded-lg p-0.5 shadow-sm">
              <button
                onClick={() => setZoom((z) => Math.max(0.6, z - 0.2))}
                className="p-1 sm:p-1.5 hover:bg-slate-100 rounded text-slate-600"
                title="Zoom Out"
              >
                <ZoomOut className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
              </button>
              <span className="px-1.5 sm:px-2 text-[11px] sm:text-xs font-mono font-medium text-slate-600">
                {Math.round(zoom * 100)}%
              </span>
              <button
                onClick={() => setZoom((z) => Math.min(2.5, z + 0.2))}
                className="p-1 sm:p-1.5 hover:bg-slate-100 rounded text-slate-600"
                title="Zoom In"
              >
                <ZoomIn className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
              </button>
              <button
                onClick={() => setZoom(1)}
                className="p-1 sm:p-1.5 hover:bg-slate-100 rounded text-slate-600"
                title="Reset Zoom"
              >
                <RotateCcw className="w-3 sm:w-3.5 h-3 sm:h-3.5" />
              </button>
            </div>

            <button
              onClick={onClose}
              className="hidden sm:block p-2 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-xl transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Mobile Tab Switcher */}
        <div className="md:hidden flex border-b border-slate-200 bg-slate-100/90 p-1.5 gap-1.5 text-xs font-semibold">
          <button
            onClick={() => setActiveTab('sheet')}
            className={`flex-1 py-1.5 rounded-lg flex items-center justify-center gap-1.5 transition-all ${
              activeTab === 'sheet'
                ? 'bg-white text-slate-900 shadow-sm border border-slate-200 font-bold'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <FileText className="w-3.5 h-3.5 text-sky-600" />
            <span>Sheet Overlay</span>
          </button>
          <button
            onClick={() => setActiveTab('answers')}
            className={`flex-1 py-1.5 rounded-lg flex items-center justify-center gap-1.5 transition-all ${
              activeTab === 'answers'
                ? 'bg-white text-slate-900 shadow-sm border border-slate-200 font-bold'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Check className="w-3.5 h-3.5 text-emerald-600" />
            <span>Answers ({sub.answers.length})</span>
          </button>
        </div>

        {/* Content Body: Split view on Desktop, Tabbed on Mobile */}
        <div className="flex-1 flex flex-col md:flex-row overflow-hidden bg-slate-100">
          {/* Left: Scanned Sheet Overlay Image */}
          <div className={`flex-1 overflow-auto p-3 sm:p-4 flex items-center justify-center relative select-none ${
            activeTab === 'sheet' ? 'flex' : 'hidden md:flex'
          }`}>
            {overlayUrl ? (
              <img
                src={overlayUrl}
                alt="Evaluated OMR Sheet Overlay"
                style={{ transform: `scale(${zoom})`, transformOrigin: 'top center' }}
                className="max-h-full max-w-full rounded-lg shadow-lg border border-slate-300 transition-transform duration-100"
              />
            ) : (
              <div className="text-slate-400 text-sm flex flex-col items-center">
                <HelpCircle className="w-8 h-8 mb-2" />
                No visual overlay generated for this sheet.
              </div>
            )}
          </div>

          {/* Right: Question Breakdown & Manual Override Panel */}
          <div className={`w-full md:w-80 bg-white border-l border-slate-200 flex flex-col overflow-hidden ${
            activeTab === 'answers' ? 'flex flex-1' : 'hidden md:flex'
          }`}>
            <div className="p-3.5 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
                Responses ({sub.answers.length})
              </span>
              <span className="text-[11px] text-slate-500">Tap to edit</span>
            </div>

            <div className="flex-1 overflow-y-auto p-3 space-y-2">
              {sub.answers.map((ans) => {
                const isSelectedForEdit = editingQ === ans.question_number;
                return (
                  <div
                    key={ans.question_number}
                    className={`p-2.5 rounded-xl border text-xs transition-all ${
                      ans.is_flagged
                        ? 'bg-amber-50/70 border-amber-300'
                        : ans.is_correct
                        ? 'bg-emerald-50/40 border-emerald-200'
                        : ans.detected_option
                        ? 'bg-rose-50/40 border-rose-200'
                        : 'bg-slate-50 border-slate-200'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-slate-800 font-mono">
                          Q{ans.question_number}
                        </span>
                        {ans.is_flagged ? (
                          <span className="flex items-center gap-1 text-[10px] text-amber-700 font-bold bg-amber-100 px-1.5 py-0.5 rounded">
                            <AlertTriangle className="w-3 h-3" /> Review
                          </span>
                        ) : ans.is_correct ? (
                          <span className="flex items-center gap-1 text-[10px] text-emerald-700 font-semibold bg-emerald-100 px-1.5 py-0.5 rounded">
                            <Check className="w-3 h-3" /> Correct
                          </span>
                        ) : (
                          <span className="text-[10px] text-rose-700 font-semibold bg-rose-100 px-1.5 py-0.5 rounded">
                            {ans.detected_option ? 'Wrong' : 'Blank'}
                          </span>
                        )}
                      </div>

                      <button
                        onClick={() => {
                          setEditingQ(isSelectedForEdit ? null : ans.question_number);
                          setOverrideOpt(ans.detected_option || '');
                        }}
                        className="p-1 text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 rounded"
                        title="Edit answer"
                      >
                        <Edit3 className="w-3.5 h-3.5" />
                      </button>
                    </div>

                    <div className="mt-1.5 flex items-center justify-between text-[11px] text-slate-600">
                      <span>
                        Marked:{' '}
                        <strong
                          className={
                            ans.is_correct
                              ? 'text-emerald-700'
                              : ans.detected_option
                              ? 'text-rose-700'
                              : 'text-slate-400'
                          }
                        >
                          {ans.detected_option || 'None'}
                        </strong>
                      </span>
                      <span>
                        Key: <strong className="text-slate-800">{ans.correct_option}</strong>
                      </span>
                    </div>

                    {/* Inline edit form */}
                    {isSelectedForEdit && (
                      <div className="mt-2.5 pt-2 border-t border-slate-200/80 flex items-center gap-1.5">
                        <span className="text-[10px] font-bold text-slate-500 uppercase">Set:</span>
                        {['A', 'B', 'C', 'D'].map((opt) => (
                          <button
                            key={opt}
                            onClick={() => setOverrideOpt(opt)}
                            className={`px-2 py-0.5 rounded text-xs font-bold ${
                              overrideOpt === opt
                                ? 'bg-sky-600 text-white'
                                : 'bg-slate-200 text-slate-700 hover:bg-slate-300'
                            }`}
                          >
                            {opt}
                          </button>
                        ))}
                        <button
                          onClick={() => setOverrideOpt('')}
                          className={`px-1.5 py-0.5 rounded text-[10px] ${
                            overrideOpt === ''
                              ? 'bg-slate-700 text-white'
                              : 'bg-slate-200 text-slate-600'
                          }`}
                        >
                          Clear
                        </button>
                        <button
                          onClick={() => handleSaveOverride(ans.question_number)}
                          disabled={saving}
                          className="ml-auto px-2.5 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded text-[10px] font-bold shadow-sm"
                        >
                          {saving ? '...' : 'Save'}
                        </button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
