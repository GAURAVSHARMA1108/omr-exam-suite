import React, { useState } from 'react';
import { Plus, Trash2, Sparkles, FileDown, CheckCircle, ArrowLeft, Layers, ShieldAlert } from 'lucide-react';
import { Question } from '../types';
import { apiClient } from '../api/client';
import { BulkPasteModal } from '../components/BulkPasteModal';

interface Props {
  onCreated: (examId: string) => void;
  onCancel: () => void;
}

export const ExamCreate: React.FC<Props> = ({ onCreated, onCancel }) => {
  const [title, setTitle] = useState<string>('Physics Periodic Assessment');
  const [subject, setSubject] = useState<string>('Physics');
  const [dateStr, setDateStr] = useState<string>(new Date().toISOString().split('T')[0]);
  const [rollLength, setRollLength] = useState<number>(6);
  const [optionsCount, setOptionsCount] = useState<number>(4);
  const [layoutType, setLayoutType] = useState<'split' | 'duplex'>('split');
  const [positiveMarks, setPositiveMarks] = useState<number>(1.0);
  const [negativeMarks, setNegativeMarks] = useState<number>(0.25);
  const [instructions, setInstructions] = useState<string>('Fill circles completely using dark blue/black ballpoint pen.');

  const [questions, setQuestions] = useState<Question[]>([
    {
      question_number: 1,
      question_text: 'What is the SI unit of electric current?',
      options: ['Volt', 'Ampere', 'Ohm', 'Watt'],
      correct_option: 'B',
      marks: 1.0,
      negative_marks: 0.25,
    },
    {
      question_number: 2,
      question_text: 'Which law states that for every action, there is an equal and opposite reaction?',
      options: ['Newton First Law', 'Newton Second Law', 'Newton Third Law', 'Law of Gravitation'],
      correct_option: 'C',
      marks: 1.0,
      negative_marks: 0.25,
    },
    {
      question_number: 3,
      question_text: 'What is the acceleration due to gravity on the Earth surface approximately?',
      options: ['8.9 m/s²', '9.8 m/s²', '10.8 m/s²', '12.0 m/s²'],
      correct_option: 'B',
      marks: 1.0,
      negative_marks: 0.25,
    },
  ]);

  const [isBulkModalOpen, setIsBulkModalOpen] = useState<boolean>(false);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleAddQuestion = () => {
    const nextNum = questions.length + 1;
    setQuestions([
      ...questions,
      {
        question_number: nextNum,
        question_text: `Question ${nextNum}`,
        options: ['Option A', 'Option B', 'Option C', 'Option D'],
        correct_option: 'A',
        marks: positiveMarks,
        negative_marks: negativeMarks,
      },
    ]);
  };

  const handleRemoveQuestion = (idx: number) => {
    const filtered = questions.filter((_, i) => i !== idx);
    const renumbered = filtered.map((q, i) => ({ ...q, question_number: i + 1 }));
    setQuestions(renumbered);
  };

  const handleUpdateQuestion = (idx: number, field: keyof Question, value: any) => {
    const updated = [...questions];
    updated[idx] = { ...updated[idx], [field]: value };
    setQuestions(updated);
  };

  const handleUpdateOption = (qIdx: number, optIdx: number, text: string) => {
    const updated = [...questions];
    const newOptions = [...updated[qIdx].options];
    newOptions[optIdx] = text;
    updated[qIdx].options = newOptions;
    setQuestions(updated);
  };

  const handleImportBulk = (imported: Question[]) => {
    const remapped = imported.map((q, i) => ({
      ...q,
      question_number: i + 1,
      marks: positiveMarks,
      negative_marks: negativeMarks,
    }));
    setQuestions(remapped);
    // If > 25 questions, suggest duplex layout
    if (remapped.length > 25) {
      setLayoutType('duplex');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (questions.length === 0) {
      setError('Please add at least 1 question.');
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const payload = {
        title,
        subject,
        date_str: dateStr,
        instructions,
        roll_length: rollLength,
        options_per_question: optionsCount,
        layout_type: layoutType,
        positive_marks: positiveMarks,
        negative_marks: negativeMarks,
        questions,
      };
      const created = await apiClient.createExam(payload);
      onCreated(created.id);
    } catch (err: any) {
      setError(err.message || 'Failed to save exam');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6 pb-12">
      {/* Top action bar */}
      <div className="flex items-center justify-between">
        <button
          onClick={onCancel}
          className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-800 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Exams</span>
        </button>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setIsBulkModalOpen(true)}
            className="px-3.5 py-2 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 text-indigo-700 rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-sm transition-all"
          >
            <Sparkles className="w-4 h-4 text-indigo-600" />
            <span>Paste from Word / Text</span>
          </button>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Exam Metadata Card */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4">
          <div className="border-b border-slate-100 pb-3">
            <h3 className="text-base font-bold text-slate-900">Exam Details & Printing Settings</h3>
            <p className="text-xs text-slate-500">Configure layout, question paper metadata, and scoring marks</p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 text-xs">
            <div>
              <label className="font-semibold text-slate-700 block mb-1">Exam Title *</label>
              <input
                type="text"
                required
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl outline-none focus:ring-2 focus:ring-sky-500 focus:bg-white"
                placeholder="e.g. Grade 10 Science Quiz"
              />
            </div>

            <div>
              <label className="font-semibold text-slate-700 block mb-1">Subject *</label>
              <input
                type="text"
                required
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl outline-none focus:ring-2 focus:ring-sky-500 focus:bg-white"
                placeholder="e.g. Physics, Chemistry..."
              />
            </div>

            <div>
              <label className="font-semibold text-slate-700 block mb-1">Exam Date</label>
              <input
                type="date"
                value={dateStr}
                onChange={(e) => setDateStr(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl outline-none focus:ring-2 focus:ring-sky-500 focus:bg-white"
              />
            </div>

            <div>
              <label className="font-semibold text-slate-700 block mb-1">Print Layout Format</label>
              <select
                value={layoutType}
                onChange={(e: any) => setLayoutType(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl outline-none focus:ring-2 focus:ring-sky-500 focus:bg-white"
              >
                <option value="split">Side-by-Side Split (Left: Questions, Right: OMR)</option>
                <option value="duplex">Duplex / Multi-Page (Page 1: Questions, Page 2: OMR)</option>
              </select>
            </div>

            <div>
              <label className="font-semibold text-slate-700 block mb-1">Student Roll No. Digits</label>
              <select
                value={rollLength}
                onChange={(e) => setRollLength(Number(e.target.value))}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl outline-none focus:ring-2 focus:ring-sky-500 focus:bg-white"
              >
                <option value={4}>4 Digits</option>
                <option value={5}>5 Digits</option>
                <option value={6}>6 Digits (Standard)</option>
                <option value={8}>8 Digits</option>
              </select>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="font-semibold text-slate-700 block mb-1">Correct Mark (+)</label>
                <input
                  type="number"
                  step="0.25"
                  value={positiveMarks}
                  onChange={(e) => setPositiveMarks(Number(e.target.value))}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl outline-none focus:ring-2 focus:ring-sky-500 focus:bg-white font-mono"
                />
              </div>
              <div>
                <label className="font-semibold text-slate-700 block mb-1">Negative Mark (-)</label>
                <input
                  type="number"
                  step="0.25"
                  value={negativeMarks}
                  onChange={(e) => setNegativeMarks(Number(e.target.value))}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl outline-none focus:ring-2 focus:ring-sky-500 focus:bg-white font-mono"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Questions Header */}
        <div className="flex items-center justify-between pt-2">
          <div>
            <h3 className="text-base font-bold text-slate-900">
              Questions & Answer Keys ({questions.length})
            </h3>
            <p className="text-xs text-slate-500">
              Set question prompt, 4 choices, and select the radio button for the correct answer
            </p>
          </div>

          <button
            type="button"
            onClick={handleAddQuestion}
            className="px-3 py-1.5 bg-sky-50 hover:bg-sky-100 border border-sky-200 text-sky-700 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add Question</span>
          </button>
        </div>

        {/* Question Cards */}
        <div className="space-y-3">
          {questions.map((q, idx) => (
            <div
              key={idx}
              className="bg-white rounded-2xl border border-slate-200 shadow-sm p-4 text-xs space-y-3 relative group"
            >
              <div className="flex items-start justify-between gap-3">
                <span className="w-8 h-8 rounded-xl bg-slate-100 text-slate-800 font-bold flex items-center justify-center font-mono shrink-0">
                  {q.question_number}
                </span>
                <input
                  type="text"
                  required
                  value={q.question_text}
                  onChange={(e) => handleUpdateQuestion(idx, 'question_text', e.target.value)}
                  placeholder="Enter question text..."
                  className="flex-1 px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl font-medium outline-none focus:ring-2 focus:ring-sky-500 focus:bg-white"
                />
                <button
                  type="button"
                  onClick={() => handleRemoveQuestion(idx)}
                  className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
                  title="Delete question"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>

              {/* Options Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pl-11">
                {['A', 'B', 'C', 'D'].map((letter, optIdx) => {
                  const isKey = q.correct_option === letter;
                  return (
                    <div
                      key={letter}
                      className={`flex items-center gap-2 p-1.5 rounded-xl border transition-all ${
                        isKey ? 'bg-emerald-50/70 border-emerald-300' : 'bg-slate-50 border-slate-200'
                      }`}
                    >
                      <button
                        type="button"
                        onClick={() => handleUpdateQuestion(idx, 'correct_option', letter)}
                        className={`w-6 h-6 rounded-lg text-xs font-bold flex items-center justify-center shrink-0 transition-all ${
                          isKey
                            ? 'bg-emerald-600 text-white shadow-sm'
                            : 'bg-white border border-slate-300 text-slate-600 hover:bg-slate-200'
                        }`}
                        title="Click to set as correct answer"
                      >
                        {letter}
                      </button>
                      <input
                        type="text"
                        required
                        value={q.options[optIdx] || ''}
                        onChange={(e) => handleUpdateOption(idx, optIdx, e.target.value)}
                        placeholder={`Option ${letter}`}
                        className="flex-1 bg-transparent border-0 outline-none text-xs font-normal text-slate-800"
                      />
                      {isKey && (
                        <span className="text-[10px] font-bold text-emerald-700 uppercase pr-1.5">
                          Key
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>

        {error && (
          <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-700 flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-rose-600" />
            <span>{error}</span>
          </div>
        )}

        {/* Submit Bar */}
        <div className="sticky bottom-20 md:bottom-4 z-20 bg-white/95 backdrop-blur-md p-4 rounded-2xl border border-slate-200 shadow-xl flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
          <div className="text-xs text-slate-600">
            Total: <strong>{questions.length}</strong> questions • Max Score:{' '}
            <strong>{(questions.length * positiveMarks).toFixed(1)}</strong>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onCancel}
              className="flex-1 sm:flex-initial px-4 py-2.5 text-xs font-semibold text-slate-600 hover:text-slate-800 border border-slate-200 sm:border-transparent rounded-xl"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="flex-1 sm:flex-initial px-6 py-2.5 bg-gradient-to-r from-sky-600 to-indigo-600 hover:from-sky-700 hover:to-indigo-700 text-white rounded-xl text-xs font-bold shadow-md hover:shadow-lg transition-all flex items-center justify-center gap-2 disabled:opacity-50"
            >
              <FileDown className="w-4 h-4 shrink-0" />
              <span>
                {submitting ? 'Generating PDF...' : 'Save & Generate PDF'}
              </span>
            </button>
          </div>
        </div>
      </form>

      {/* Bulk Paste Modal */}
      <BulkPasteModal
        isOpen={isBulkModalOpen}
        onClose={() => setIsBulkModalOpen(false)}
        onImport={handleImportBulk}
      />
    </div>
  );
};
