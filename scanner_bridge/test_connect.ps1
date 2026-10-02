$dm = New-Object -ComObject WIA.DeviceManager
$info = $dm.DeviceInfos | Where-Object { $_.Type -eq 1 } | Select-Object -First 1

if ($info -ne $null) {
    Write-Host "Device Name: $($info.Properties['Name'].Value)"
    Write-Host "Device ID: $($info.DeviceID)"
    
    # Try direct connect
    try {
        $dev = $info.Connect()
        Write-Host "Connected successfully! Items: $($dev.Items.Count)"
    } catch {
        Write-Host "Direct Connect failed: $($_.Exception.Message)"
    }

    # Try CommonDialog ShowSelectDevice
    try {
        $cd = New-Object -ComObject WIA.CommonDialog
        Write-Host "CommonDialog instantiated"
    } catch {
        Write-Host "CommonDialog failed: $($_.Exception.Message)"
    }
} else {
    Write-Host "No WIA scanner found"
}
