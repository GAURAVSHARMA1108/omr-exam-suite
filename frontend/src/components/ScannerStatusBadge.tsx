import React, { useState, useEffect } from 'react';
import { Printer, CheckCircle, AlertCircle, RefreshCw } from 'lucide-react';
import { apiClient } from '../api/client';
import { ScannerStatus } from '../types';

interface Props {
  status?: ScannerStatus | null;
  onRefresh?: () => void;
  onStatusChange?: (status: ScannerStatus | null) => void;
}

export const ScannerStatusBadge: React.FC<Props> = ({ status: controlledStatus, onRefresh, onStatusChange }) => {
  const [internalStatus, setInternalStatus] = useState<ScannerStatus | null>(null);
  const [checking, setChecking] = useState<boolean>(false);
  const [showHelp, setShowHelp] = useState<boolean>(false);

  const status = controlledStatus !== undefined ? controlledStatus : internalStatus;

  const checkStatus = async () => {
    if (onRefresh) {
      onRefresh();
      return;
    }
    setChecking(true);
    const res = await apiClient.checkScannerBridge();
    setInternalStatus(res);
    if (onStatusChange) onStatusChange(res);
    setChecking(false);
  };

  useEffect(() => {
    if (controlledStatus === undefined) {
      checkStatus();
      const interval = setInterval(checkStatus, 4000);
      return () => clearInterval(interval);
    }
  }, [controlledStatus]);

  return (
    <div className="relative">
      <button
        onClick={() => setShowHelp(!showHelp)}
        className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
          status?.online
            ? 'bg-emerald-50 border-emerald-300 text-emerald-800 hover:bg-emerald-100'
            : 'bg-slate-100 border-slate-300 text-slate-600 hover:bg-slate-200'
        }`}
        title="Click for Scanner Bridge setup info"
      >
        <span className="relative flex h-2 w-2">
          {status?.online && (
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
          )}
          <span
            className={`relative inline-flex rounded-full h-2 w-2 ${
              status?.online ? 'bg-emerald-500' : 'bg-slate-400'
            }`}
          ></span>
        </span>
        <Printer className="w-3.5 h-3.5" />
        <span>
          {status?.online
            ? status.physical_scanner_connected
              ? `Scanner Ready (${status.scanners.length})`
              : 'Virtual Scanner Ready'
            : 'Scanner Bridge Offline'}
        </span>
      </button>

      {showHelp && (
        <div className="absolute right-0 mt-2 w-80 bg-white rounded-xl shadow-xl border border-slate-200 p-4 z-50 text-xs">
          <div className="flex items-center justify-between pb-2 border-b border-slate-100">
            <span className="font-semibold text-slate-800">Local Scanner Bridge</span>
            <button
              onClick={checkStatus}
              disabled={checking}
              className="p-1 hover:bg-slate-100 rounded text-slate-500"
              title="Refresh status"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${checking ? 'animate-spin' : ''}`} />
            </button>
          </div>

          <div className="mt-3 space-y-2 text-slate-600">
            <p>
              The scanner bridge connects web browsers to local Windows USB & network scanners
              (WIA/TWAIN) with zero browser plugins.
            </p>
            {status?.online ? (
              <div className="bg-emerald-50 border border-emerald-200 p-2.5 rounded-lg text-emerald-800">
                <p className="font-semibold flex items-center gap-1.5">
                  <CheckCircle className="w-4 h-4 text-emerald-600" />
                  Bridge is running on port 8765
                </p>
                <p className="mt-1 text-[11px]">
                  Detected Devices: {status.scanners.map((s) => s.name).join(', ')}
                </p>
              </div>
            ) : (
              <div className="bg-amber-50 border border-amber-200 p-2.5 rounded-lg text-amber-800">
                <p className="font-semibold flex items-center gap-1.5">
                  <AlertCircle className="w-4 h-4 text-amber-600" />
                  Bridge not running
                </p>
                <p className="mt-1 text-[11px]">
                  To use your physical scanner, run{' '}
                  <code className="bg-amber-100 px-1 py-0.5 rounded font-mono text-[10px]">
                    scanner_bridge\run_bridge.bat
                  </code>{' '}
                  on this computer.
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
