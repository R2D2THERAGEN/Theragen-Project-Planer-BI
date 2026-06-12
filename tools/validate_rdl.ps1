# Validate the paginated report through Report Builder's own RDL object model.
# A clean Deserialize here means Report Builder can open the file; an exception
# pinpoints the exact element that would surface as a designer error
# ("Object reference not set to an instance of an object").
# Run with Windows PowerShell 5.1 (net48): powershell.exe -File tools\validate_rdl.ps1
param(
    [string]$RdlPath = (Join-Path (Split-Path $PSScriptRoot -Parent) "paginated\Theragen Status Report.rdl")
)
$dll = "C:\Program Files\Power BI Report Builder\Microsoft.ReportingServices.RdlObjectModel.dll"
Add-Type -Path $dll
$serializer = New-Object Microsoft.ReportingServices.RdlObjectModel.Serialization.RdlSerializer
$fs = [System.IO.File]::OpenRead($RdlPath)
try {
    $report = $serializer.Deserialize($fs)
    Write-Output ("OK: deserialized. DataSets={0} ReportItems={1} Params={2}" -f `
        $report.DataSets.Count, $report.ReportSections[0].Body.ReportItems.Count, `
        $report.ReportParameters.Count)
    # Every data region must name its dataset or the service rejects the
    # upload (rsMissingDataSetName, e.g. a designer-inserted GaugePanel1).
    $bad = @()
    foreach ($item in $report.ReportSections[0].Body.ReportItems) {
        $prop = $item.GetType().GetProperty("DataSetName")
        if ($prop -and [string]::IsNullOrEmpty($prop.GetValue($item))) {
            $bad += "$($item.GetType().Name) '$($item.Name)'"
        }
    }
    if ($bad.Count -gt 0) {
        Write-Output ("ERR: data regions missing DataSetName -> {0}" -f ($bad -join ", "))
        exit 1
    }
    Write-Output "OK: all data regions have DataSetName"
    # Round-trip: serialize back to catch null-init gaps the designer would hit.
    $ms = New-Object System.IO.MemoryStream
    $serializer.Serialize($ms, $report)
    Write-Output ("OK: round-trip serialize ({0} bytes)" -f $ms.Length)
    exit 0
} catch {
    $e = $_.Exception
    while ($e) { Write-Output ("ERR: [{0}] {1}" -f $e.GetType().Name, $e.Message); $e = $e.InnerException }
    exit 1
} finally { $fs.Dispose() }
