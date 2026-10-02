import React, { useState } from 'react';
import { X, Sparkles, Check, AlertCircle, FileText } from 'lucide-react';
import { apiClient } from '../api/client';
import { Question } from '../types';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onImport: (questions: Question[]) => void;
}

const SAMPLE_TEXT = `1. What is the powerhouse of the cell?
A) Nucleus
B) Mitochondria
C) Ribosome
D) Chloroplast
Answer: B

2. Which gas do plants primarily absorb during photosynthesis?
(A) Oxygen
(B) Carbon Dioxide
(C) Nitrogen
(D) Hydrogen
Ans: B

3. What is the chemical symbol for Gold?
A. Ag
B. Fe
C. Au
D. Pb
Correct: C

4. What is the speed of light in vacuum approximately?
A. 300,000 km/s
B. 150,000 km/s
C. 1,000,000 km/s
D. 30,000 km/s
Answer: A`;

export const BulkPasteModal: React.FC<Props> = ({ isOpen, onClose, onImport }) => {
  const [text, setText] = useState<string>(SAMPLE_TEXT);
  const [loading, setLoading] = useState<boolean>(false);
  const [parsed, setParsed] = useState<Question[]>([]);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleParse = async () => {
    if (!text.trim()) {
      setError('Please paste or type question text first.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.bulkParse(text);
      if (res.questions && res.questions.length > 0) {
        setParsed(res.questions);
      } else {
        setError('No questions could be detected. Check formatting (e.g., 1. Question... A) Opt... Ans: B).');
      }
    } catch (err: any) {
      setError(err.message || 'Parsing failed');
    } finally {
      setLoading(false);
    }
  };

  const handleConfirm = () => {
    if (parsed.length > 0) {
      onImport(parsed);
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white w-full max-w-3xl rounded-2xl shadow-2xl border border-slate-200 flex flex-col max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50/50">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-sky-100 text-sky-700 flex items-center justify-center">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-slate-800">Smart Bulk Question Parser</h2>
              <p className="text-xs text-slate-500">Paste questions from Word, Google Docs, or test banks</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 flex-1 overflow-y-auto space-y-4">
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-700">
                Paste Test Content
              </label>
              <button
                type="button"
                onClick={() => setText(SAMPLE_TEXT)}
                className="text-xs text-sky-600 hover:text-sky-700 font-medium"
              >
                Load Sample Format
              </button>
            </div>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={9}
              className="w-full text-xs font-mono p-3 bg-slate-50 border border-slate-300 rounded-xl focus:ring-2 focus:ring-sky-500 focus:border-sky-500 focus:bg-white transition-all outline-none"
              placeholder="Paste questions here... e.g.&#10;1. Question text&#10;A) Option 1&#10;B) Option 2&#10;Answer: A"
            />
          </div>

          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2.5 pt-1">
            <span className="text-xs text-slate-500">
              Supports: A/B/C/D or (A)/(B) or A./B. format & Answer: / Ans: markers
            </span>
            <button
              type="button"
              onClick={handleParse}
              disabled={loading}
              className="w-full sm:w-auto px-4 py-2 bg-slate-800 hover:bg-slate-900 text-white rounded-xl text-xs font-medium flex items-center justify-center gap-2 shadow-sm transition-all disabled:opacity-50"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>{loading ? 'Analyzing...' : 'Parse Questions'}</span>
            </button>
          </div>

          {error && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-700 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
              <span>{error}</span>
            </div>
          )}

          {/* Parsed Preview */}
          {parsed.length > 0 && (
            <div className="mt-4 border-t border-slate-200 pt-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                  <Check className="w-4 h-4 text-emerald-600" />
                  Successfully Detected ({parsed.length} Questions)
                </h3>
                <span className="text-xs text-emerald-700 font-medium bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                  Ready to import
                </span>
              </div>

              <div className="space-y-2.5 max-h-60 overflow-y-auto pr-1">
                {parsed.map((q, idx) => (
                  <div key={idx} className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs">
                    <p className="font-semibold text-slate-800">
                      Q{q.question_number}. {q.question_text}
                    </p>
                    <div className="grid grid-cols-2 gap-2 mt-2">
                      {q.options.map((opt, i) => (
                        <div
                          key={i}
                          className={`p-1.5 rounded-lg border flex items-center justify-between ${
                            String.fromCharCode(65 + i) === q.correct_option
                              ? 'bg-emerald-50 border-emerald-300 font-semibold text-emerald-900'
                              : 'bg-white border-slate-200 text-slate-600'
                          }`}
                        >
                          <span>
                            ({String.fromCharCode(65 + i)}) {opt}
                          </span>
                          {String.fromCharCode(65 + i) === q.correct_option && (
                            <span className="text-[10px] bg-emerald-600 text-white px-1.5 py-0.2 rounded font-bold">
                              Key
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3.5 border-t border-slate-200 bg-slate-50 flex items-center justify-end gap-2.5">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 border border-slate-300 text-slate-700 hover:bg-slate-100 rounded-xl text-xs font-medium transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            disabled={parsed.length === 0}
            className="px-5 py-2 bg-sky-600 hover:bg-sky-700 text-white rounded-xl text-xs font-semibold shadow-sm transition-all disabled:opacity-40 flex items-center gap-1.5"
          >
            <Check className="w-3.5 h-3.5" />
            <span>Import {parsed.length} Questions</span>
          </button>
        </div>
      </div>
    </div>
  );
};
