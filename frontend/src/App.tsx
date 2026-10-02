import React, { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { Dashboard } from './pages/Dashboard';
import { ExamCreate } from './pages/ExamCreate';
import { GradeSheets } from './pages/GradeSheets';
import { ResultsReport } from './pages/ResultsReport';
import { apiClient } from './api/client';
import { ScannerStatus } from './types';

export function App() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'create' | 'grade' | 'results'>('dashboard');
  const [selectedExamId, setSelectedExamId] = useState<string | null>(null);
  const [scannerStatus, setScannerStatus] = useState<ScannerStatus | null>(null);

  const refreshScanner = async () => {
    try {
      const status = await apiClient.checkScannerBridge();
      setScannerStatus(status);
    } catch {
      setScannerStatus(null);
    }
  };

  useEffect(() => {
    refreshScanner();
    const interval = setInterval(refreshScanner, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleSelectExam = (examId: string, action: 'grade' | 'results') => {
    setSelectedExamId(examId);
    setActiveTab(action);
  };

  const handleExamCreated = (examId: string) => {
    setSelectedExamId(examId);
    setActiveTab('grade');
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        selectedExamId={selectedExamId}
        scannerStatus={scannerStatus}
        onRefreshScanner={refreshScanner}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-3 sm:px-6 lg:px-8 pt-4 pb-24 md:py-6">
        {activeTab === 'dashboard' && (
          <Dashboard
            onSelectExam={handleSelectExam}
            onNavigateCreate={() => setActiveTab('create')}
          />
        )}

        {activeTab === 'create' && (
          <ExamCreate
            onCreated={handleExamCreated}
            onCancel={() => setActiveTab('dashboard')}
          />
        )}

        {activeTab === 'grade' && (
          <GradeSheets
            initialExamId={selectedExamId}
            scannerStatus={scannerStatus}
            onRefreshScanner={refreshScanner}
            onNavigateResults={(examId) => {
              setSelectedExamId(examId);
              setActiveTab('results');
            }}
          />
        )}

        {activeTab === 'results' && selectedExamId && (
          <ResultsReport
            examId={selectedExamId}
            onBack={() => setActiveTab('dashboard')}
          />
        )}
      </main>

      <footer className="hidden md:block bg-white border-t border-slate-200 py-4 text-center text-xs text-slate-400">
        OMR Exam Suite Pro • Optical Mark Recognition & Assessment System
      </footer>
    </div>
  );
}

export default App;
