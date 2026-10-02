import React, { useState, useEffect, useRef } from 'react';
import { 
  Printer, Upload, Camera, CheckCircle, AlertTriangle, 
  RefreshCw, Eye, Sparkles, FileImage, ShieldCheck, ShieldAlert, ChevronRight 
} from 'lucide-react';
import { Exam, Submission, ScannerStatus } from '../types';
import { apiClient } from '../api/client';
import { VisualOverlayModal } from '../components/VisualOverlayModal';

interface Props {
  initialExamId?: string | null;
  scannerStatus?: ScannerStatus | null;
  onRefreshScanner?: () => void;
  onNavigateResults: (examId: string) => void;
}

export const GradeSheets: React.FC<Props> = ({ 
  initialExamId, 
  scannerStatus: propScannerStatus, 
  onRefreshScanner, 
  onNavigateResults 
}) => {
  const [exams, setExams] = useState<Exam[]>([]);
  const [selectedExamId, setSelectedExamId] = useState<string>(initialExamId || '');
  const [internalScannerStatus, setInternalScannerStatus] = useState<ScannerStatus | null>(null);

  const scannerStatus = propScannerStatus !== undefined ? propScannerStatus : internalScannerStatus;

  // Scanner form state
  const [selectedDevice, setSelectedDevice] = useState<string>('');
  const [scanSource, setScanSource] = useState<'flatbed' | 'feeder'>('flatbed');
  const [scanDpi, setScanDpi] = useState<number>(200);
  const [isScanning, setIsScanning] = useState<boolean>(false);

  // Upload state
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadProgress, setUploadProgress] = useState<string>('');
  const [submissions, setSubmissions] = useState<Submission[]>([]);

  // Duplicate Protection state
  const [allowOverwrite, setAllowOverwrite] = useState<boolean>(false);
  const [duplicateWarning, setDuplicateWarning] = useState<string | null>(null);

  // Camera state
  const [cameraActive, setCameraActive] = useState<boolean>(false);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [cameraStream, setCameraStream] = useState<MediaStream | null>(null);

  // Modal inspection
  const [inspectedSub, setInspectedSub] = useState<Submission | null>(null);

  // Mobile channel toggle ('camera' by default on phone)
  const [mobileChannel, setMobileChannel] = useState<'camera' | 'scanner'>('camera');
  const cameraInputRef = useRef<HTMLInputElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Error message
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Auto-select valid device whenever scanner status updates
  useEffect(() => {
    if (scannerStatus?.online && scannerStatus?.scanners && scannerStatus.scanners.length > 0) {
      setSelectedDevice((prev) => {
        const match = scannerStatus.scanners.find((s) => s.id === prev);
        return match ? prev : scannerStatus.scanners[0].id;
      });
    }
  }, [scannerStatus]);

  useEffect(() => {
    loadExams();
    checkBridge();
    const interval = setInterval(checkBridge, 3000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (selectedExamId) {
      loadSubmissions(selectedExamId);
    }
  }, [selectedExamId]);

  const loadExams = async () => {
    try {
      const data = await apiClient.listExams();
      setExams(data);
      if (!selectedExamId && data.length > 0) {
        setSelectedExamId(data[0].id);
      }
    } catch (e: any) {
      setErrorMsg(e.message);
    }
  };

  const checkBridge = async () => {
    if (onRefreshScanner) {
      onRefreshScanner();
      return;
    }
    const status = await apiClient.checkScannerBridge();
    setInternalScannerStatus(status);
  };

  const loadSubmissions = async (examId: string) => {
    try {
      const subs = await apiClient.listSubmissions(examId);
      setSubmissions(subs);
    } catch (e) {
      console.error(e);
    }
  };

  const handleProcessedSubmission = (sub: Submission) => {
    if (sub.is_duplicate) {
      setDuplicateWarning(
        sub.duplicate_message ||
        `Duplicate sheet detected for Roll '${sub.student_roll}'. Duplicate entry was skipped.`
      );
      setSubmissions((prev) => {
        const idx = prev.findIndex((p) => p.id === sub.id || (p.student_roll === sub.student_roll && p.student_roll !== 'UNKNOWN'));
        if (idx !== -1) {
          const updated = [...prev];
          updated[idx] = sub;
          return updated;
        }
        return [sub, ...prev];
      });
    } else {
      setDuplicateWarning(null);
      setSubmissions((prev) => {
        const filtered = prev.filter((p) => p.id !== sub.id);
        return [sub, ...filtered];
      });
    }
  };

  // 1. Direct Scanner Execution
  const handleTriggerScanner = async () => {
    setIsScanning(true);
    setErrorMsg(null);
    setUploadProgress('Acquiring pages from scanner...');
    try {
      const pages = await apiClient.triggerScannerScan({
        deviceId: selectedDevice,
        source: scanSource,
        dpi: scanDpi,
      });

      if (pages.length === 0) {
        throw new Error('Scanner returned no pages.');
      }

      setUploadProgress(`Processing ${pages.length} scanned page(s)...`);
      for (const pageB64 of pages) {
        const sub = await apiClient.gradeBase64(pageB64, selectedExamId || undefined, undefined, allowOverwrite);
        handleProcessedSubmission(sub);
        setInspectedSub(sub); // Auto open visual review for latest scan
      }
      setUploadProgress('Grading complete!');
    } catch (err: any) {
      setErrorMsg(`Scanner Error: ${err.message}`);
    } finally {
      setIsScanning(false);
      setTimeout(() => setUploadProgress(''), 3000);
    }
  };

  // 2. File Upload Dropzone
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setIsUploading(true);
    setErrorMsg(null);
    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        setUploadProgress(`Evaluating sheet ${i + 1} of ${files.length}...`);
        const sub = await apiClient.uploadSheet(file, selectedExamId || undefined, undefined, allowOverwrite);
        handleProcessedSubmission(sub);
        if (i === 0) setInspectedSub(sub);
      }
      setUploadProgress('All sheets evaluated!');
    } catch (err: any) {
      setErrorMsg(`Grading Error: ${err.message}`);
    } finally {
      setIsUploading(false);
      setTimeout(() => setUploadProgress(''), 3000);
      e.target.value = '';
    }
  };

  // 3. Live Camera
  const toggleCamera = async () => {
    if (cameraActive) {
      if (cameraStream) {
        cameraStream.getTracks().forEach((track) => track.stop());
        setCameraStream(null);
      }
      setCameraActive(false);
    } else {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: 'environment', width: { ideal: 1920 }, height: { ideal: 1080 } },
        });
        setCameraStream(stream);
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
        setCameraActive(true);
      } catch (err: any) {
        alert('Could not access camera: ' + err.message);
      }
    }
  };

  const handleCaptureFromCamera = async () => {
    if (!videoRef.current) return;
    const canvas = document.createElement('canvas');
    canvas.width = videoRef.current.videoWidth || 1280;
    canvas.height = videoRef.current.videoHeight || 720;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);
    const dataUrl = canvas.toDataURL('image/jpeg', 0.92);

    setIsUploading(true);
    setUploadProgress('Evaluating camera snap...');
    try {
      const sub = await apiClient.gradeBase64(dataUrl, selectedExamId || undefined, undefined, allowOverwrite);
      handleProcessedSubmission(sub);
      setInspectedSub(sub);
      toggleCamera(); // turn off camera after snap
    } catch (err: any) {
      setErrorMsg(`Evaluation Error: ${err.message}`);
    } finally {
      setIsUploading(false);
      setUploadProgress('');
    }
  };

  const currentExam = exams.find((e) => e.id === selectedExamId);

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-12">
      {/* Top Header & Exam Selector */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <CheckCircle className="w-5 h-5 text-emerald-600" />
            OMR Evaluation & Scanning Hub
          </h2>
          <p className="text-xs text-slate-500">
            Fetch directly from physical scanners, upload photos, or capture with camera
          </p>
        </div>

        <div className="flex items-center gap-3 w-full md:w-auto">
          <label className="text-xs font-semibold text-slate-700 whitespace-nowrap">
            Selected Test:
          </label>
          <select
            value={selectedExamId}
            onChange={(e) => setSelectedExamId(e.target.value)}
            className="flex-1 md:w-64 px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl text-xs font-medium outline-none focus:ring-2 focus:ring-sky-500"
          >
            {exams.map((ex) => (
              <option key={ex.id} value={ex.id}>
                {ex.title} ({ex.questions.length} Qs)
              </option>
            ))}
          </select>

          {selectedExamId && (
            <button
              onClick={() => onNavigateResults(selectedExamId)}
              className="px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-semibold whitespace-nowrap transition-colors"
            >
              View Gradebook
            </button>
          )}
        </div>
      </div>

      {/* Duplicate Protection Warning Banner */}
      {duplicateWarning && (
        <div className="p-4 bg-amber-50 border border-amber-300 text-amber-900 rounded-2xl text-xs flex items-center justify-between shadow-sm animate-in fade-in">
          <div className="flex items-center gap-2.5">
            <ShieldAlert className="w-5 h-5 text-amber-600 shrink-0" />
            <div>
              <p className="font-bold text-amber-950">Duplicate Sheet Protected</p>
              <p className="text-amber-800 text-[11px] mt-0.5">{duplicateWarning}</p>
            </div>
          </div>
          <button
            onClick={() => setDuplicateWarning(null)}
            className="px-3 py-1.5 bg-amber-200/80 hover:bg-amber-300 text-amber-900 rounded-xl font-bold text-xs transition-colors shrink-0"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Duplicate Protection Controls */}
      <div className="bg-white border border-slate-200 rounded-2xl px-4 py-2.5 flex flex-wrap items-center justify-between gap-3 text-xs shadow-sm">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-emerald-600" />
          <span className="font-semibold text-slate-800">Duplicate Sheet Protection:</span>
          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
            Active
          </span>
          <span className="text-[11px] text-slate-500 hidden sm:inline">
            Prevents double-counting if the same sheet is scanned again.
          </span>
        </div>

        <label className="flex items-center gap-2 cursor-pointer select-none text-slate-600 hover:text-slate-900">
          <input
            type="checkbox"
            checked={allowOverwrite}
            onChange={(e) => setAllowOverwrite(e.target.checked)}
            className="rounded border-slate-300 text-sky-600 focus:ring-sky-500 w-4 h-4"
          />
          <span className="text-xs font-medium">
            Overwrite existing grade on re-scan
          </span>
        </label>
      </div>

      {errorMsg && (
        <div className="p-4 bg-rose-50 border border-rose-200 text-rose-700 rounded-2xl text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{errorMsg}</span>
          </div>
          <button onClick={() => setErrorMsg(null)} className="text-xs font-bold text-rose-800">
            Dismiss
          </button>
        </div>
      )}

      {/* Mobile Channel Segmented Toggle (Visible only on mobile screens < 768px) */}
      <div className="md:hidden flex bg-slate-200/80 p-1 rounded-xl text-xs font-semibold">
        <button
          onClick={() => setMobileChannel('camera')}
          className={`flex-1 py-2 rounded-lg flex items-center justify-center gap-1.5 transition-all ${
            mobileChannel === 'camera'
              ? 'bg-white text-slate-900 shadow-sm'
              : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          <Camera className="w-4 h-4 text-sky-600" />
          <span>Camera & Upload</span>
        </button>
        <button
          onClick={() => setMobileChannel('scanner')}
          className={`flex-1 py-2 rounded-lg flex items-center justify-center gap-1.5 transition-all ${
            mobileChannel === 'scanner'
              ? 'bg-white text-slate-900 shadow-sm'
              : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          <Printer className="w-4 h-4 text-emerald-600" />
          <span>Hardware Scanner</span>
        </button>
      </div>

      {/* Main Ingestion Channels: Scanner vs Upload vs Camera */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Channel 1: Physical / Virtual Scanner Integration */}
        <div className={`bg-white rounded-2xl border border-slate-200 shadow-sm p-5 sm:p-6 flex flex-col justify-between space-y-5 relative overflow-hidden ${mobileChannel === 'scanner' ? 'flex' : 'hidden md:flex'}`}>
          <div className="absolute top-0 right-0 transform translate-x-4 -translate-y-4 w-28 h-28 bg-emerald-50 rounded-full pointer-events-none" />

          <div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-xl bg-emerald-100 text-emerald-800 flex items-center justify-center">
                  <Printer className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-800">Direct Hardware Scanner</h3>
                  <p className="text-[11px] text-slate-500">
                    Windows WIA / TWAIN connected document scanner
                  </p>
                </div>
              </div>

              <button
                onClick={checkBridge}
                className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg text-xs"
                title="Refresh scanner connection"
              >
                <RefreshCw className="w-3.5 h-3.5" />
              </button>
            </div>

            <div className="mt-4 space-y-3 text-xs">
              <div>
                <label className="font-semibold text-slate-700 block mb-1">Scanner Device</label>
                <select
                  value={selectedDevice}
                  onChange={(e) => setSelectedDevice(e.target.value)}
                  disabled={!scannerStatus?.online}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl outline-none focus:ring-2 focus:ring-emerald-500 disabled:opacity-50"
                >
                  {scannerStatus?.scanners?.map((sc) => (
                    <option key={sc.id} value={sc.id}>
                      {sc.name}
                    </option>
                  )) || <option>No Scanner Connected</option>}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Source Feed</label>
                  <select
                    value={scanSource}
                    onChange={(e: any) => setScanSource(e.target.value)}
                    disabled={!scannerStatus?.online}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl outline-none focus:ring-2 focus:ring-emerald-500 disabled:opacity-50"
                  >
                    <option value="flatbed">Flatbed (Single Sheet)</option>
                    <option value="feeder">Document Feeder (ADF Batch)</option>
                  </select>
                </div>

                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Resolution</label>
                  <select
                    value={scanDpi}
                    onChange={(e) => setScanDpi(Number(e.target.value))}
                    disabled={!scannerStatus?.online}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl outline-none focus:ring-2 focus:ring-emerald-500 disabled:opacity-50"
                  >
                    <option value={150}>150 DPI (Fast)</option>
                    <option value={200}>200 DPI (Recommended)</option>
                    <option value={300}>300 DPI (High Quality)</option>
                  </select>
                </div>
              </div>
            </div>
          </div>

          <div className="pt-2">
            <button
              onClick={handleTriggerScanner}
              disabled={isScanning || !scannerStatus?.online}
              className="w-full py-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold shadow-md hover:shadow-lg transition-all flex items-center justify-center gap-2 disabled:opacity-40"
            >
              <Printer className="w-4 h-4" />
              <span>
                {isScanning
                  ? 'Acquiring Scan...'
                  : scannerStatus?.online
                  ? 'Fetch & Grade from Scanner'
                  : 'Scanner Bridge Offline (Run run_bridge.bat)'}
              </span>
            </button>
            <p className="text-[10px] text-slate-400 text-center mt-2">
              Batch scanning in ADF mode pulls all sheets from tray automatically.
            </p>
          </div>
        </div>

        {/* Channel 2: Photo / Document File Upload Dropzone */}
        <div className={`bg-white rounded-2xl border border-slate-200 shadow-sm p-5 sm:p-6 flex flex-col justify-between space-y-4 ${mobileChannel === 'camera' ? 'flex' : 'hidden md:flex'}`}>
          <div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-xl bg-sky-100 text-sky-800 flex items-center justify-center">
                  <Upload className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-800">Upload Photos & Scans</h3>
                  <p className="text-[11px] text-slate-500">
                    Phone camera pictures, JPG, PNG, PDF files
                  </p>
                </div>
              </div>

              <button
                onClick={toggleCamera}
                className="px-2.5 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors"
              >
                <Camera className="w-3.5 h-3.5 text-slate-600" />
                <span>{cameraActive ? 'Close' : 'Webcam'}</span>
              </button>
            </div>

            {/* Live Camera Viewfinder (if enabled) */}
            {cameraActive ? (
              <div className="mt-3 relative rounded-xl overflow-hidden bg-black aspect-video flex flex-col items-center justify-center">
                <video
                  ref={videoRef}
                  autoPlay
                  playsInline
                  className="w-full h-full object-cover"
                />
                <button
                  onClick={handleCaptureFromCamera}
                  disabled={isUploading}
                  className="absolute bottom-3 px-4 py-2 bg-sky-600 hover:bg-sky-700 text-white rounded-xl text-xs font-bold shadow-lg flex items-center gap-1.5"
                >
                  <Camera className="w-4 h-4" />
                  <span>Snap & Grade Now</span>
                </button>
              </div>
            ) : (
              /* Dropzone + Mobile Buttons */
              <div>
                <label className="mt-3 border-2 border-dashed border-slate-300 hover:border-sky-500 rounded-xl p-6 sm:p-8 flex flex-col items-center justify-center cursor-pointer bg-slate-50/50 hover:bg-sky-50/30 transition-all group">
                  <FileImage className="w-8 h-8 text-slate-400 group-hover:text-sky-600 transition-colors mb-2" />
                  <span className="text-xs font-semibold text-slate-800 group-hover:text-sky-700 text-center">
                    Drop OMR sheet photos or click to browse
                  </span>
                  <span className="text-[11px] text-slate-400 mt-1 text-center">
                    Batch selection supported • Auto-perspective deskew
                  </span>
                  <input
                    type="file"
                    multiple
                    accept="image/jpeg,image/png,image/jpg"
                    onChange={handleFileUpload}
                    disabled={isUploading}
                    className="hidden"
                  />
                </label>

                {/* Hidden native mobile inputs */}
                <input
                  ref={cameraInputRef}
                  type="file"
                  accept="image/*"
                  capture="environment"
                  onChange={handleFileUpload}
                  className="hidden"
                />
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept="image/jpeg,image/png,image/jpg"
                  onChange={handleFileUpload}
                  className="hidden"
                />

                {/* Quick action buttons for touch & mobile devices */}
                <div className="mt-3 grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => cameraInputRef.current?.click()}
                    disabled={isUploading}
                    className="py-2.5 px-3 bg-sky-600 hover:bg-sky-700 text-white rounded-xl text-xs font-bold shadow-sm flex items-center justify-center gap-1.5 active:scale-95 transition-all disabled:opacity-50"
                  >
                    <Camera className="w-4 h-4" />
                    <span>Snap with Camera</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={isUploading}
                    className="py-2.5 px-3 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 active:scale-95 transition-all disabled:opacity-50"
                  >
                    <FileImage className="w-4 h-4 text-slate-500" />
                    <span>Browse Files</span>
                  </button>
                </div>
              </div>
            )}
          </div>

          {uploadProgress && (
            <div className="p-2.5 bg-sky-50 border border-sky-200 rounded-xl text-xs text-sky-800 flex items-center gap-2 animate-pulse">
              <Sparkles className="w-4 h-4 text-sky-600" />
              <span>{uploadProgress}</span>
            </div>
          )}
        </div>
      </div>

      {/* Graded Submissions Queue / Live Feed */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div>
            <h3 className="text-base font-bold text-slate-900">
              Evaluated Sheets ({submissions.length})
            </h3>
            <p className="text-xs text-slate-500">
              Click on any row to open the visual overlay inspector and review answers
            </p>
          </div>

          {submissions.length > 0 && selectedExamId && (
            <button
              onClick={() => onNavigateResults(selectedExamId)}
              className="text-xs font-bold text-sky-600 hover:text-sky-700 flex items-center gap-1"
            >
              <span>Full Analytics Gradebook</span>
              <ChevronRight className="w-4 h-4" />
            </button>
          )}
        </div>

        {submissions.length === 0 ? (
          <div className="py-12 text-center text-slate-400 text-xs">
            No sheets evaluated yet in this session. Start scanning or upload photos above.
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
            {submissions.map((sub) => {
              const overlayThumbnail = sub.overlay_image_path
                ? `/static/overlays/${sub.overlay_image_path.split(/[\\/]/).pop()}`
                : '';
              return (
                <div
                  key={sub.id}
                  onClick={() => setInspectedSub(sub)}
                  className="p-3.5 bg-slate-50 hover:bg-slate-100/80 rounded-xl border border-slate-200 cursor-pointer transition-all hover:shadow-md flex items-center gap-3 group"
                >
                  {/* Thumbnail */}
                  <div className="w-14 h-16 bg-slate-200 rounded-lg overflow-hidden shrink-0 border border-slate-300 relative">
                    {overlayThumbnail ? (
                      <img
                        src={overlayThumbnail}
                        alt="Sheet"
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-slate-400">
                        <FileImage className="w-6 h-6" />
                      </div>
                    )}
                    <div className="absolute inset-0 bg-sky-900/0 group-hover:bg-sky-900/30 transition-colors flex items-center justify-center opacity-0 group-hover:opacity-100">
                      <Eye className="w-4 h-4 text-white" />
                    </div>
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <span className="font-mono font-bold text-xs text-slate-900 truncate">
                        Roll: {sub.student_roll}
                      </span>
                    <div className="flex items-center gap-1">
                      {sub.is_duplicate && (
                        <span
                          className="text-[9px] font-bold uppercase px-1.5 py-0.2 rounded-full bg-amber-100 text-amber-800 border border-amber-300"
                          title={sub.duplicate_message || 'Duplicate sheet protected'}
                        >
                          Duplicate
                        </span>
                      )}
                      <span
                        className={`text-[9px] font-bold uppercase px-1.5 py-0.2 rounded-full border ${
                          sub.status === 'graded'
                            ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                            : 'bg-amber-50 text-amber-700 border-amber-200'
                        }`}
                      >
                        {sub.status === 'graded' ? 'Pass' : 'Review'}
                      </span>
                    </div>
                    </div>

                    <div className="mt-1 flex items-baseline gap-1.5">
                      <span className="text-base font-extrabold text-slate-800">
                        {sub.total_score}
                      </span>
                      <span className="text-[11px] text-slate-500">/ {sub.max_score}</span>
                      <span className="text-[11px] font-semibold text-emerald-600 ml-auto">
                        {sub.percentage}%
                      </span>
                    </div>

                    <div className="mt-2 pt-2 border-t border-slate-100 flex items-center justify-between text-[11px]">
                      <span className="text-slate-400 group-hover:text-sky-600 transition-colors">Click to inspect</span>
                      <span className="font-semibold text-sky-600 group-hover:underline flex items-center gap-0.5">
                        <Eye className="w-3 h-3" /> Inspect ↗
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Visual Overlay Inspection Modal */}
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
