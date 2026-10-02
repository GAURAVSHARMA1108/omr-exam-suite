$dm = New-Object -ComObject WIA.DeviceManager
Write-Host "Total Devices in WIA Manager: $($dm.DeviceInfos.Count)"
foreach ($info in $dm.DeviceInfos) {
    Write-Host "Device: $($info.Properties['Name'].Value) | ID: $($info.DeviceID) | Type: $($info.Type)"
    foreach ($prop in $info.Properties) {
        Write-Host "   $($prop.Name) ($($prop.PropertyID)) = $($prop.Value)"
    }
    Write-Host "Connecting..."
    try {
        $dev = $info.Connect()
        Write-Host "Connected successfully! Items count: $($dev.Items.Count)"
        foreach ($item in $dev.Items) {
            Write-Host "  Item: $($item.Properties['Item Name'].Value)"
        }
    } catch {
        Write-Host "Connect failed: $($_.Exception.Message)"
    }
}
