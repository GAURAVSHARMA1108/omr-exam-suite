import subprocess
import json
import base64
import os
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional

def list_wia_scanners() -> List[Dict[str, Any]]:
    """
    Queries Windows WIA (Windows Image Acquisition) to list connected physical scanners.
    """
    ps_script = """
    $ErrorActionPreference = 'SilentlyContinue'
    $dm = New-Object -ComObject WIA.DeviceManager
    $scanners = @()
    if ($dm -ne $null) {
        foreach ($info in $dm.DeviceInfos) {
            if ($info.Type -eq 1) { # 1 = ScannerDeviceType
                $name = $info.Properties["Name"].Value
                $id = $info.DeviceID
                $scanners += [PSCustomObject]@{
                    id = $id
                    name = $name
                    type = "scanner"
                }
            }
        }
    }
    $scanners | ConvertTo-Json -Compress
    """
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=10
        )
        out = proc.stdout.strip()
        if out:
            data = json.loads(out)
            if isinstance(data, dict):
                return [data]
            elif isinstance(data, list):
                return data
    except Exception as e:
        print(f"Error enumerating WIA scanners: {e}")

    return []

def acquire_wia_scan(
    device_id: Optional[str] = None,
    source: str = "flatbed", # "flatbed" or "feeder"
    dpi: int = 200,
    color_mode: str = "gray" # "gray" or "color"
) -> tuple[List[str], Optional[str]]:
    """
    Acquires scanned pages from the selected WIA device.
    Returns tuple of (list of base64-encoded JPEG image strings, optional error string).
    """
    temp_dir = tempfile.mkdtemp(prefix="wia_scan_")
    output_pattern = os.path.join(temp_dir, "scan_%d.jpg")

    # WIA Color Intent: 1 = Color, 2 = Grayscale, 4 = B&W
    wia_intent = 2 if color_mode.lower() == "gray" else 1

    clean_device_id = (device_id or "").replace('"', '`"')

    ps_script = f"""
    $ErrorActionPreference = 'Stop'
    try {{
        $dialog = New-Object -ComObject WIA.CommonDialog
        $deviceManager = New-Object -ComObject WIA.DeviceManager
        
        $targetId = "{clean_device_id}"
        $deviceInfo = $null
        foreach ($info in $deviceManager.DeviceInfos) {{
            if ($info.Type -eq 1) {{
                if ($targetId -and $info.DeviceID -eq $targetId) {{
                    $deviceInfo = $info
                    break
                }} elseif (-not $targetId) {{
                    $deviceInfo = $info
                    break
                }}
            }}
        }}

        if ($deviceInfo -eq $null) {{
            Write-Output "ERROR:Scanner device not found or disconnected from USB."
            exit 1
        }}

        $device = $deviceInfo.Connect()
        $item = $device.Items[1]

        # Configure DPI & Intent
        try {{
            $item.Properties["6146"].Value = {wia_intent} # WIA_IPS_CUR_INTENT
            $item.Properties["6147"].Value = {dpi}        # WIA_IPS_XRES
            $item.Properties["6148"].Value = {dpi}        # WIA_IPS_YRES
        }} catch {{}}

        # Transfer image to file (FormatID for JPEG: {{B96B3CAE-0728-11D3-9D7B-0000F81EF32E}})
        $imageFile = $dialog.ShowTransfer($item, "{{B96B3CAE-0728-11D3-9D7B-0000F81EF32E}}", $false)
        $targetFile = "{temp_dir}\\scanned_sheet.jpg"
        if (Test-Path $targetFile) {{ Remove-Item $targetFile }}
        $imageFile.SaveFile($targetFile)
        Write-Output "SUCCESS:$targetFile"
    }} catch {{
        Write-Output "ERROR:$($_.Exception.Message)"
        exit 1
    }}
    """

    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=45
        )
        out = proc.stdout.strip()
        if "SUCCESS:" in out:
            saved_file = out.split("SUCCESS:")[1].strip()
            if os.path.exists(saved_file):
                with open(saved_file, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                return [f"data:image/jpeg;base64,{b64}"], None

        err_msg = out.split("ERROR:")[1].strip() if "ERROR:" in out else out
        if not err_msg and proc.stderr:
            err_msg = proc.stderr.strip()
        return [], err_msg or "Unknown scanner communication error"
    except subprocess.TimeoutExpired:
        return [], "Scanner acquisition timed out (device may be busy or waiting for input)."
    except Exception as e:
        return [], f"Scan acquisition failed: {str(e)}"
