# Migrate ai0522 from Windows MySQL to Docker MySQL
# Usage:
#   .\scripts\migrate_to_docker.ps1
#   .\scripts\migrate_to_docker.ps1 -SourcePassword "win_mysql_pwd"

param(
    [string]$SourceHost = "127.0.0.1",
    [int]$SourcePort = 3306,
    [string]$TargetHost = "127.0.0.1",
    [int]$TargetPort = 3307,
    [string]$User = "root",
    [string]$SourcePassword = "",
    [string]$TargetPassword = "123456",
    [string]$Database = "ai0522"
)

$mysqlBin = "C:\Program Files\MySQL\MySQL Server 8.0\bin"
$dumpFile = Join-Path (Split-Path $PSScriptRoot -Parent) "ai0522_backup.sql"

if (-not (Test-Path "$mysqlBin\mysqldump.exe")) {
    Write-Error "mysqldump not found. Check MySQL installation or update mysqlBin in this script."
    exit 1
}

if (-not $SourcePassword) {
    $secure = Read-Host "Enter Windows MySQL root password (source ${SourceHost}:${SourcePort})" -AsSecureString
    $SourcePassword = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    )
}

function Test-MySqlConnection {
    param([string]$HostName, [int]$Port, [string]$Pwd, [string]$Label)
    & "$mysqlBin\mysql.exe" `
        -h $HostName -P $Port -u $User "--password=$Pwd" `
        --default-character-set=utf8mb4 -e "SELECT 1;" 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Cannot connect to $Label (${HostName}:${Port}). Check service and password."
        exit 1
    }
}

Write-Host "==> Step 1/4: Check connections..."
$dockerDb = docker ps --filter "name=wolin-mysql" --format "{{.Names}}"
if (-not $dockerDb) {
    Write-Error "Docker MySQL is not running. Run: docker compose up -d db"
    exit 1
}

Test-MySqlConnection -HostName $SourceHost -Port $SourcePort -Pwd $SourcePassword -Label "Windows MySQL"
Test-MySqlConnection -HostName $TargetHost -Port $TargetPort -Pwd $TargetPassword -Label "Docker MySQL"
Write-Host "    Both databases are reachable."

$sourceAddr = "${SourceHost}:${SourcePort}/${Database}"
$targetAddr = "${TargetHost}:${TargetPort}/${Database}"

Write-Host "==> Step 2/4: Export from Windows MySQL ($sourceAddr) ..."
# Use --result-file to write binary-safe UTF-8; avoid PowerShell Out-File encoding corruption
if (Test-Path $dumpFile) { Remove-Item $dumpFile -Force }

& "$mysqlBin\mysqldump.exe" `
    -h $SourceHost -P $SourcePort -u $User "--password=$SourcePassword" `
    --default-character-set=utf8mb4 `
    --single-transaction --routines --triggers --set-gtid-purged=OFF `
    --result-file=$dumpFile $Database

if ($LASTEXITCODE -ne 0) {
    Write-Error "Export failed."
    exit 1
}

$dumpSize = (Get-Item $dumpFile).Length
if ($dumpSize -lt 100) {
    Write-Error "Dump file is too small ($dumpSize bytes). Export may have failed."
    exit 1
}
Write-Host "    Exported to: $dumpFile ($dumpSize bytes)"

Write-Host "==> Step 3/4: Import into Docker MySQL ($targetAddr) ..."
# Use cmd input redirect to avoid PowerShell re-encoding the SQL file
$importCmd = "`"$mysqlBin\mysql.exe`" -h $TargetHost -P $TargetPort -u $User --password=$TargetPassword --default-character-set=utf8mb4 $Database < `"$dumpFile`""
cmd /c $importCmd

if ($LASTEXITCODE -ne 0) {
    Write-Error "Import failed."
    exit 1
}

Write-Host "==> Step 4/4: Verify data:"
& "$mysqlBin\mysql.exe" `
    -h $TargetHost -P $TargetPort -u $User "--password=$TargetPassword" `
    --default-character-set=utf8mb4 `
    -e "SHOW TABLES FROM $Database; SELECT COUNT(*) AS consultant_count FROM $Database.consultant WHERE is_deleted=0;"

Write-Host ""
Write-Host "Done. Open app: http://127.0.0.1:8800/pages/consultants"
