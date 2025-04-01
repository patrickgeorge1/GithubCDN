<#
.SYNOPSIS
    Commits files in batches to a specified branch.
.DESCRIPTION
    Requires branch name as parameter. Example:
    .\BatchGitCommit.ps1 -Branch master
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$Branch,
    
    [int]$BatchSize = 10,
    [int]$RetryCount = 3
)

$ErrorActionPreference = "Stop"
$startTimestamp = "p" + [DateTimeOffset]::Now.ToUnixTimeSeconds()
$logFile = "git_batch_commit.log"

function Write-Log {
    param([string]$message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] $message"
    Write-Host $logMessage
    Add-Content -Path $logFile -Value $logMessage
}

try {
    # Verify branch exists or create it
    if (-not (git rev-parse --verify $Branch 2>$null)) {
        git checkout -b $Branch 2>$null
        Write-Log "Created new branch: $Branch"
    }
    else {
        git checkout $Branch
        Write-Log "Using existing branch: $Branch"
    }

    $allFiles = @(Get-ChildItem -File -Recurse -Exclude ".git*" | 
                 Select-Object -ExpandProperty FullName)
    
    $totalFiles = $allFiles.Count
    $totalBatches = [Math]::Ceiling($totalFiles / $BatchSize)
    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

    Write-Log "Starting push to '$Branch' ($totalBatches batches)"

    for ($batchNum = 1; $batchNum -le $totalBatches; $batchNum++) {
        $currentBatch = $allFiles[(($batchNum - 1) * $BatchSize)..(($batchNum * $BatchSize) - 1)]
        $commitMessage = "$startTimestamp $batchNum/$totalBatches"

        $retry = 0
        while ($retry -lt $RetryCount) {
            try {
                Write-Log "Adding $($currentBatch.Count) files (Batch $batchNum/$totalBatches)"
                git add $currentBatch

                git commit -m $commitMessage
                Write-Log "Committed: $commitMessage"

                git push origin $Branch
                Write-Log "Pushed successfully"
                break
            }
            catch {
                $retry++
                Write-Log "Attempt $retry failed: $($_.Exception.Message)"
                if ($retry -ge $RetryCount) {
                    Write-Log "MAX RETRIES REACHED FOR BATCH $batchNum"
                    break
                }
                Start-Sleep -Seconds (2 * $retry)
                git reset --soft HEAD~1  # Undo failed commit
            }
        }
    }

    $elapsed = [math]::Round($stopwatch.Elapsed.TotalSeconds, 2)
    Write-Log "FINISHED in ${elapsed}s (Branch: $Branch)"
}
catch {
    Write-Log "FATAL ERROR: $_"
    exit 1
}