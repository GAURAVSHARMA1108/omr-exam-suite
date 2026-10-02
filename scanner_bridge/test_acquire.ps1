$cd = New-Object -ComObject WIA.CommonDialog
try {
    Write-Host "Attempting ShowAcquireImage..."
    # 1 = ScannerDeviceType
    # FormatID for JPEG: {B96B3CAE-0728-11D3-9D7B-0000F81EF32E}
    $img = $cd.ShowAcquireImage(1, 2, 131072, "{B96B3CAE-0728-11D3-9D7B-0000F81EF32E}", $false, $false, $false)
    Write-Host "Image acquired! Width: $($img.Width) Height: $($img.Height)"
} catch {
    Write-Host "ShowAcquireImage failed: $($_.Exception.Message)"
}
