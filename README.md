# 📄 OMR Exam Suite

An intelligent, full-stack, Progressive Web App (PWA) for educators to design print-ready OMR test sheets with integrated questions, and automatically grade them in real-time using connected hardware scanners (flatbed/ADF) or smartphone cameras.

---

## ✨ Features

- 📑 **Print-Ready OMR Generation (ReportLab)**:
  - Generates high-precision A4 test sheets with custom questions and matching bubble grids.
  - Side-by-side split layout (questions on left, OMR grid on right) or duplex multi-page format.
  - Corner fiducial markers for sub-millimeter geometric alignment and perspective deskewing.
  - Dynamic QR codes encoding unique exam metadata and layout configuration for zero-setup grading.

- 🤖 **Computer Vision Grading Pipeline (OpenCV & NumPy)**:
  - Automatic perspective transformation and contour detection based on fiducial markers.
  - Adaptive thresholding and Otsu binarization to handle uneven shadows, lighting gradients, and pencil/pen fills.
  - Roll number bubble decoding and answer key matching.
  - Visual overlay generation highlighting correct answers in green, incorrect in red, and unanswered in grey.

- 🖨️ **Hardware Document Scanner Integration (WIA / TWAIN)**:
  - Local Python daemon bridge on port `8765` communicating directly with flatbed and automatic document feeder (ADF) scanners (tested on HP LaserJet M1005 MFP).
  - Single-click **"Fetch & Grade from Scanner"** with zero driver dialog popups.

- 🛡️ **Duplicate Sheet Protection**:
  - Deterministic content hashing (`sheet_hash`) and roll number validation prevents accidental double-scanning from creating duplicate student records or corrupting class averages.
  - Safe mode blocks duplicates; optional overwrite mode updates grades in-place on re-scan.

- 📱 **Progressive Web App (PWA) & Mobile Friendly**:
  - Fully installable on Android, iOS, Windows, and macOS with native app experience and offline shell caching.
  - Native smartphone camera integration (`capture="environment"`) for direct high-resolution grading from phone.
  - Responsive bottom navigation and mobile-optimized inspection modal with sheet zoom and answer overrides.

- 📊 **Analytics & Gradebook Export**:
  - Detailed class statistics: average score, highest score, pass rate, and question-by-question breakdown.
  - One-click export to Excel (`.xlsx`) with score formulas and CSV (`.csv`).

---

## 🏗️ Project Architecture

```
omr-exam-suite/
├── backend/
│   ├── app/
│   │   ├── api/             # FastAPI REST endpoints (exams, grading, submissions)
│   │   ├── services/        # CV pipeline (omr_processor.py), PDF generator (pdf_generator.py), bulk parser
│   │   ├── models.py        # SQLAlchemy database models
│   │   ├── schemas.py       # Pydantic request/response schemas
│   │   └── database.py      # SQLite / PostgreSQL async engine
│   └── storage/             # Generated PDFs, uploaded scans, visual overlays, SQLite DB
├── frontend/
│   ├── public/              # PWA manifest, service worker, app icons
│   ├── src/
│   │   ├── components/      # VisualOverlayModal, BulkPasteModal, Navbar
│   │   ├── pages/           # Dashboard, ExamCreate, GradeSheets, ResultsReport
│   │   └── api/             # Frontend API client
│   └── vite.config.ts
└── scanner_bridge/
    └── bridge.py            # Local WIA/TWAIN scanner hardware bridge daemon
```

---

## 🚀 Quick Start

### 1. Prerequisites
- **Python 3.10+**
- **Node.js 18+** & **npm**

### 2. Backend Setup
```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
# source .venv/bin/activate

pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run build
```
The FastAPI backend automatically serves the compiled frontend at `http://127.0.0.1:8000`.

### 4. Scanner Bridge (For Desktop Hardware Scanners)
```bash
cd scanner_bridge
python bridge.py
```
Runs on `http://127.0.0.1:8765` and connects automatically to the frontend.

---

## 📱 Mobile & PWA Usage
- Open `http://<your-pc-ip>:8000` on your smartphone browser.
- Tap **"Add to Home Screen"** or **"Install App"**.
- Grade tests on the go by snapping photos with your phone camera!

---

## 📄 License
MIT License
