Get-Printer | Select-Object Name, PrinterStatus, PortName, DriverName, WorkOffline
Get-WmiObject -Class Win32_Printer | Select-Object Name, PrinterStatus, Availability, DetectedErrorState, ExtendedPrinterStatus, Status
