import uvicorn
import cv2
import numpy as np
import base64
import io
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from scanner_wia import list_wia_scanners, acquire_wia_scan

app = FastAPI(title="OMR Local Scanner Bridge", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ScanRequest(BaseModel):
    device_id: Optional[str] = None
    source: str = "flatbed" # "flatbed" or "feeder"
    dpi: int = 200
    color: str = "gray"
    use_emulated: bool = False

@app.get("/health")
def health():
    return {"status": "ok", "service": "omr-scanner-bridge"}

def generate_mock_scanned_sheet() -> str:
    """Generates an emulated scanned OMR sheet for testing when physical scanner is disconnected."""
    img = np.ones((1600, 1200, 3), dtype=np.uint8) * 255
    # Outer margin fiducials (canonical: 60x60 square at offset 30)
    m, sz = 30, 60
    cv2.rectangle(img, (m, m), (m + sz, m + sz), (0, 0, 0), -1)
    cv2.rectangle(img, (1200 - m - sz, m), (1200 - m, m + sz), (0, 0, 0), -1)
    cv2.rectangle(img, (m, 1600 - m - sz), (m + sz, 1600 - m), (0, 0, 0), -1)
    cv2.rectangle(img, (1200 - m - sz, 1600 - m - sz), (1200 - m, 1600 - m), (0, 0, 0), -1)

    # Header
    cv2.putText(img, "OMR TEST - DEMO SCAN", (120, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (30, 30, 30), 2)
    cv2.putText(img, "Emulated Scanner Output (Bridge Test Mode)", (120, 115), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 100), 1)

    # Roll bubbles (Roll: 104258)
    roll_digits = [1, 0, 4, 2, 5, 8]
    roll_x_start = 120
    roll_y_start = 220
    roll_col_w = 38
    roll_row_h = 30
    b_r = 11

    cv2.putText(img, "ROLL NO:", (60, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    for c_idx, target_digit in enumerate(roll_digits):
        cx = roll_x_start + c_idx * roll_col_w
        for d in range(10):
            cy = roll_y_start + d * roll_row_h
            if d == target_digit:
                # Filled bubble
                cv2.circle(img, (cx, cy), b_r, (20, 20, 20), -1)
            else:
                cv2.circle(img, (cx, cy), b_r, (50, 50, 50), 1)
                cv2.putText(img, str(d), (cx - 4, cy + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (70, 70, 70), 1)

    # Questions 1 to 20 bubbles
    q_start_y = 560
    row_h = 36
    opt_spacing = 34
    
    # Answers pattern: [A, B, C, D, A, B, C, D...]
    for q_idx in range(1, 21):
        col_idx = 0 if q_idx <= 10 else 1
        row_idx = (q_idx - 1) % 10
        base_x = 90 + col_idx * 500
        base_y = q_start_y + row_idx * row_h

        cv2.putText(img, f"Q{q_idx:02d}", (base_x, base_y + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        target_opt_idx = (q_idx - 1) % 4

        for opt_i in range(4):
            bx = base_x + 65 + opt_i * opt_spacing
            by = base_y
            if opt_i == target_opt_idx:
                cv2.circle(img, (bx, by), b_r, (25, 25, 25), -1)
            else:
                cv2.circle(img, (bx, by), b_r, (60, 60, 60), 1)
                cv2.putText(img, chr(65 + opt_i), (bx - 4, by + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (70, 70, 70), 1)

    # Add slight realistic scan noise
    noise = np.random.normal(0, 3, img.shape).astype(np.uint8)
    noisy_img = cv2.add(img, noise)

    _, buffer = cv2.imencode(".jpg", noisy_img, [cv2.IMWRITE_JPEG_QUALITY, 90])
    b64 = base64.b64encode(buffer).decode("utf-8")
    return f"data:image/jpeg;base64,{b64}"

@app.get("/status")
def get_scanner_status():
    """Lists available physical scanners, plus virtual test option."""
    scanners = list_wia_scanners()
    has_physical = len(scanners) > 0

    # Include explicit Virtual Test Scanner option so testing without hardware is transparent
    scanners.append({
        "id": "EMULATED_SCANNER",
        "name": "Virtual Test Scanner (Emulated for Testing)",
        "type": "virtual"
    })

    return {
        "online": True,
        "physical_scanner_connected": has_physical,
        "scanners": scanners,
        "supported_sources": ["flatbed", "feeder"],
        "supported_dpis": [150, 200, 300]
    }

@app.post("/scan")
def trigger_scan(req: ScanRequest):
    """Executes a scan from physical device or returns emulated scan."""
    # Only return simulated scan if explicitly chosen
    if req.use_emulated or req.device_id == "EMULATED_SCANNER":
        page_b64 = generate_mock_scanned_sheet()
        return {
            "success": True,
            "device": "Virtual Test Scanner",
            "pages": [page_b64]
        }

    # Attempt physical WIA scan
    pages, error_msg = acquire_wia_scan(
        device_id=req.device_id,
        source=req.source,
        dpi=req.dpi,
        color_mode=req.color
    )

    if not pages:
        detail_msg = error_msg or "Failed to communicate with scanner."
        if "not online" in detail_msg.lower():
            detail_msg = (
                "HP LaserJet M1005 MFP reported 'The WIA device is not online'. "
                "Please verify that the scanner is powered ON, the USB cable is firmly connected, "
                "and the scanner is not in sleep/standby mode (try opening and closing the scanner lid, "
                "or test scanning once using Microsoft Paint or Windows Fax and Scan to wake it up)."
            )
        raise HTTPException(
            status_code=502,
            detail=detail_msg
        )

    return {
        "success": True,
        "device": req.device_id or "HP LaserJet M1005 MFP",
        "pages": pages
    }

if __name__ == "__main__":
    print("Starting OMR Scanner Bridge on http://127.0.0.1:8765 ...")
    uvicorn.run(app, host="127.0.0.1", port=8765)
