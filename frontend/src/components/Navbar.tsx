import React from 'react';
import { FileText, PlusCircle, CheckSquare, BarChart3 } from 'lucide-react';
import { ScannerStatusBadge } from './ScannerStatusBadge';

import { ScannerStatus } from '../types';

interface Props {
  activeTab: 'dashboard' | 'create' | 'grade' | 'results';
  setActiveTab: (tab: 'dashboard' | 'create' | 'grade' | 'results') => void;
  selectedExamId?: string | null;
  scannerStatus?: ScannerStatus | null;
  onRefreshScanner?: () => void;
}

export const Navbar: React.FC<Props> = ({ 
  activeTab, 
  setActiveTab, 
  selectedExamId, 
  scannerStatus, 
  onRefreshScanner 
}) => {
  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <div 
          onClick={() => setActiveTab('dashboard')}
          className="flex items-center gap-3 cursor-pointer group"
        >
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-sky-600 to-indigo-600 flex items-center justify-center text-white shadow-sm shadow-sky-500/20 group-hover:scale-105 transition-transform">
            <CheckSquare className="w-6 h-6 stroke-[2.2]" />
          </div>
          <div>
            <h1 className="text-base font-bold text-slate-900 leading-tight flex items-center gap-1.5">
              OMR Suite <span className="text-[10px] font-semibold uppercase px-1.5 py-0.5 bg-sky-100 text-sky-800 rounded">Pro</span>
            </h1>
            <p className="text-xs text-slate-500">Test Creator & Optical Mark Grader</p>
          </div>
        </div>

        {/* Desktop navigation tabs */}
        <nav className="hidden md:flex items-center gap-1 bg-slate-100/80 p-1 rounded-xl border border-slate-200/60">
          <button
            onClick={() => setActiveTab('dashboard')}
            className={`flex items-center gap-2 px-3.5 py-1.5 text-xs font-medium rounded-lg transition-all ${
              activeTab === 'dashboard'
                ? 'bg-white text-slate-900 shadow-sm'
                : 'text-slate-600 hover:text-slate-900 hover:bg-white/50'
            }`}
          >
            <FileText className="w-4 h-4 text-sky-600" />
            <span>Exams</span>
          </button>

          <button
            onClick={() => setActiveTab('create')}
            className={`flex items-center gap-2 px-3.5 py-1.5 text-xs font-medium rounded-lg transition-all ${
              activeTab === 'create'
                ? 'bg-white text-slate-900 shadow-sm'
                : 'text-slate-600 hover:text-slate-900 hover:bg-white/50'
            }`}
          >
            <PlusCircle className="w-4 h-4 text-indigo-600" />
            <span>New Test</span>
          </button>

          <button
            onClick={() => setActiveTab('grade')}
            className={`flex items-center gap-2 px-3.5 py-1.5 text-xs font-medium rounded-lg transition-all ${
              activeTab === 'grade'
                ? 'bg-white text-slate-900 shadow-sm'
                : 'text-slate-600 hover:text-slate-900 hover:bg-white/50'
            }`}
          >
            <CheckSquare className="w-4 h-4 text-emerald-600" />
            <span>Grade & Scan</span>
          </button>

          {selectedExamId && (
            <button
              onClick={() => setActiveTab('results')}
              className={`flex items-center gap-2 px-3.5 py-1.5 text-xs font-medium rounded-lg transition-all ${
                activeTab === 'results'
                  ? 'bg-white text-slate-900 shadow-sm'
                : 'text-slate-600 hover:text-slate-900 hover:bg-white/50'
              }`}
            >
              <BarChart3 className="w-4 h-4 text-violet-600" />
              <span>Results</span>
            </button>
          )}
        </nav>

        {/* Right action area: Scanner bridge badge */}
        <div className="flex items-center gap-2 sm:gap-3">
          <ScannerStatusBadge status={scannerStatus} onRefresh={onRefreshScanner} />
        </div>
      </div>

      {/* Mobile Bottom Navigation Bar (Touch-optimized for smartphones) */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-white/95 backdrop-blur-md border-t border-slate-200/80 px-2 py-1.5 flex items-center justify-around shadow-[0_-4px_20px_rgba(0,0,0,0.06)]">
        <button
          onClick={() => setActiveTab('dashboard')}
          className={`flex flex-col items-center justify-center py-1 px-3 rounded-xl transition-all ${
            activeTab === 'dashboard'
              ? 'text-sky-600 font-bold'
              : 'text-slate-500 hover:text-slate-800'
          }`}
        >
          <FileText className="w-5 h-5 mb-0.5" />
          <span className="text-[10px]">Exams</span>
        </button>

        <button
          onClick={() => setActiveTab('create')}
          className={`flex flex-col items-center justify-center py-1 px-3 rounded-xl transition-all ${
            activeTab === 'create'
              ? 'text-indigo-600 font-bold'
              : 'text-slate-500 hover:text-slate-800'
          }`}
        >
          <PlusCircle className="w-5 h-5 mb-0.5" />
          <span className="text-[10px]">New Test</span>
        </button>

        <button
          onClick={() => setActiveTab('grade')}
          className={`flex flex-col items-center justify-center py-1 px-3.5 rounded-xl transition-all ${
            activeTab === 'grade'
              ? 'text-emerald-700 bg-emerald-50 font-bold shadow-sm'
              : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          <CheckSquare className="w-5 h-5 mb-0.5 text-emerald-600" />
          <span className="text-[10px]">Grade & Scan</span>
        </button>

        {selectedExamId && (
          <button
            onClick={() => setActiveTab('results')}
            className={`flex flex-col items-center justify-center py-1 px-3 rounded-xl transition-all ${
              activeTab === 'results'
                ? 'text-violet-600 font-bold'
                : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            <BarChart3 className="w-5 h-5 mb-0.5" />
            <span className="text-[10px]">Results</span>
          </button>
        )}
      </nav>
    </header>
  );
};
