# Backup Verification Guide

**Purpose**: Verify all Cloud SQL databases have proper backup and disaster recovery configuration.

> ⚠️ **Non-negotiable**: No database goes to production without verified backups.

---

## Quick Check: All Instances

Run this to verify backup status across all Cloud SQL instances:

```powershell
# List all instances with backup status
gcloud sql instances list --format="table(name,state,settings.backupConfiguration.enabled,settings.backupConfiguration.pointInTimeRecoveryEnabled)"
```

Expected output:
```
NAME           STATE   ENABLED  POINT_IN_TIME_RECOVERY_ENABLED
flashcards-db  RUNNABLE  True     True
```

If any instance shows `False` for ENABLED, backups are NOT configured.

---

## Automated Backup Verification Script

Save this as `verify-backups.ps1` and run periodically or before releases:

```powershell
# verify-backups.ps1
# Verifies backup configuration and status for all Cloud SQL instances
# Per project-methodology v3.8

param(
    [string]$ProjectId = "super-flashcards-475210"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Cloud SQL Backup Verification" -ForegroundColor Cyan
Write-Host "  Project: $ProjectId" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Set project
gcloud config set project $ProjectId 2>$null

# Get all instances
$instances = gcloud sql instances list --format="value(name)" 2>$null
if (-not $instances) {
    Write-Host "`n✗ No Cloud SQL instances found in project $ProjectId" -ForegroundColor Red
    exit 1
}

$allPassed = $true
$results = @()

foreach ($instance in $instances) {
    Write-Host "`n----------------------------------------" -ForegroundColor Gray
    Write-Host "Instance: $instance" -ForegroundColor Yellow
    Write-Host "----------------------------------------" -ForegroundColor Gray
    
    # Get backup configuration
    $backupConfig = gcloud sql instances describe $instance --format="json(settings.backupConfiguration)" 2>$null | ConvertFrom-Json
    $config = $backupConfig.settings.backupConfiguration
    
    $instanceResult = @{
        Instance = $instance
        BackupsEnabled = $false
        PITREnabled = $false
        RetentionDays = 0
        LastBackup = "None"
        LastBackupStatus = "Unknown"
        Issues = @()
    }
    
    # Check if backups enabled
    if ($config.enabled -eq $true) {
        Write-Host "  ✓ Automated backups: Enabled" -ForegroundColor Green
        $instanceResult.BackupsEnabled = $true
    } else {
        Write-Host "  ✗ Automated backups: DISABLED" -ForegroundColor Red
        $instanceResult.Issues += "Backups not enabled"
        $allPassed = $false
    }
    
    # Check PITR
    if ($config.pointInTimeRecoveryEnabled -eq $true) {
        Write-Host "  ✓ Point-in-time recovery: Enabled" -ForegroundColor Green
        $instanceResult.PITREnabled = $true
    } else {
        Write-Host "  ⚠ Point-in-time recovery: Disabled" -ForegroundColor Yellow
        $instanceResult.Issues += "PITR not enabled (recommended)"
    }
    
    # Check retention
    $retention = $config.backupRetentionSettings.retainedBackups
    if ($retention) {
        $instanceResult.RetentionDays = $retention
        if ($retention -ge 7) {
            Write-Host "  ✓ Retention: $retention backups" -ForegroundColor Green
        } else {
            Write-Host "  ⚠ Retention: $retention backups (recommend 7+)" -ForegroundColor Yellow
            $instanceResult.Issues += "Low retention ($retention)"
        }
    }
    
    # Check backup window
    if ($config.startTime) {
        Write-Host "  ✓ Backup window: $($config.startTime) UTC" -ForegroundColor Green
    }
    
    # Get recent backups
    Write-Host "`n  Recent Backups:" -ForegroundColor Cyan
    $backups = gcloud sql backups list --instance=$instance --limit=3 --format="json" 2>$null | ConvertFrom-Json
    
    if ($backups -and $backups.Count -gt 0) {
        $latestBackup = $backups[0]
        $instanceResult.LastBackup = $latestBackup.endTime
        $instanceResult.LastBackupStatus = $latestBackup.status
        
        foreach ($backup in $backups) {
            $status = $backup.status
            $endTime = $backup.endTime
            $type = $backup.type
            
            if ($status -eq "SUCCESSFUL") {
                Write-Host "    ✓ $endTime - $type - $status" -ForegroundColor Green
            } else {
                Write-Host "    ✗ $endTime - $type - $status" -ForegroundColor Red
                $allPassed = $false
            }
        }
        
        # Check if latest backup is within 24 hours
        $latestTime = [DateTime]::Parse($latestBackup.endTime)
        $hoursSinceBackup = (Get-Date).ToUniversalTime().Subtract($latestTime).TotalHours
        
        if ($hoursSinceBackup -gt 24) {
            Write-Host "    ⚠ Latest backup is $([math]::Round($hoursSinceBackup)) hours old" -ForegroundColor Yellow
            $instanceResult.Issues += "Backup older than 24 hours"
        }
    } else {
        Write-Host "    ✗ No backups found!" -ForegroundColor Red
        $instanceResult.Issues += "No backups exist"
        $allPassed = $false
    }
    
    $results += $instanceResult
}

# Summary
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

Write-Host "`nInstances checked: $($results.Count)" -ForegroundColor White

$issueCount = ($results | Where-Object { $_.Issues.Count -gt 0 }).Count
if ($issueCount -gt 0) {
    Write-Host "Instances with issues: $issueCount" -ForegroundColor Yellow
    
    foreach ($result in $results | Where-Object { $_.Issues.Count -gt 0 }) {
        Write-Host "`n  $($result.Instance):" -ForegroundColor Yellow
        foreach ($issue in $result.Issues) {
            Write-Host "    - $issue" -ForegroundColor Red
        }
    }
}

if ($allPassed) {
    Write-Host "`n✓ All backup checks passed!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "`n✗ Some backup checks failed. Review issues above." -ForegroundColor Red
    exit 1
}
```

---

## Running the Verification

### One-Time Check
```powershell
.\verify-backups.ps1 -ProjectId "super-flashcards-475210"
```

### Scheduled Check (Windows Task Scheduler)
Create a scheduled task to run weekly:
```powershell
# Create scheduled task (run as admin)
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-File C:\Scripts\verify-backups.ps1"
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 9am
Register-ScheduledTask -TaskName "CloudSQL-Backup-Verification" -Action $action -Trigger $trigger
```

---

## Manual Verification Commands

### Check Specific Instance
```powershell
# Full backup configuration
gcloud sql instances describe [INSTANCE_NAME] --format="yaml(settings.backupConfiguration)"

# List all backups
gcloud sql backups list --instance=[INSTANCE_NAME]

# Get specific backup details
gcloud sql backups describe [BACKUP_ID] --instance=[INSTANCE_NAME]
```

### Enable Backups (if missing)
```powershell
# Enable automated backups with PITR
gcloud sql instances patch [INSTANCE_NAME] \
    --backup-start-time=03:00 \
    --enable-point-in-time-recovery \
    --retained-backups-count=7

# For production, use 30-day retention:
gcloud sql instances patch [INSTANCE_NAME] \
    --backup-start-time=03:00 \
    --enable-point-in-time-recovery \
    --retained-backups-count=30
```

### Trigger Manual Backup
```powershell
# Create on-demand backup
gcloud sql backups create --instance=[INSTANCE_NAME]

# Verify it completed
gcloud sql backups list --instance=[INSTANCE_NAME] --limit=1
```

---

## Backup Configuration Standards

| Setting | Development | Production |
|---------|-------------|------------|
| Automated Backups | ✅ Required | ✅ Required |
| Point-in-Time Recovery | Recommended | ✅ Required |
| Retention Period | 7 days | 30 days |
| Backup Window | Any off-peak | 02:00-04:00 UTC |

---

## Disaster Recovery Scenarios

### Scenario 1: Restore to Point in Time
```powershell
# Restore to specific time (requires PITR enabled)
gcloud sql instances clone [SOURCE_INSTANCE] [NEW_INSTANCE] \
    --point-in-time="2025-12-30T10:00:00Z"
```

### Scenario 2: Restore from Backup
```powershell
# List available backups
gcloud sql backups list --instance=[INSTANCE_NAME]

# Restore specific backup to new instance
gcloud sql backups restore [BACKUP_ID] \
    --restore-instance=[NEW_INSTANCE] \
    --backup-instance=[SOURCE_INSTANCE]
```

### Scenario 3: Export Database
```powershell
# Export to GCS (additional protection)
gcloud sql export sql [INSTANCE_NAME] gs://[BUCKET]/backup.sql \
    --database=[DATABASE_NAME]
```

---

## Verification Checklist

Use this checklist before any production release:

- [ ] All Cloud SQL instances have automated backups enabled
- [ ] Point-in-time recovery enabled for production databases
- [ ] Retention period meets requirements (7+ dev, 30+ prod)
- [ ] At least one successful backup exists
- [ ] Most recent backup completed within 24 hours
- [ ] Backup verification script runs without errors
- [ ] DR procedure documented and tested

---

## Integration with CI/CD

Add backup verification to your release checklist:

```yaml
# In GitHub Actions (optional pre-release check)
- name: Verify Backups
  run: |
    # Quick backup status check
    BACKUP_ENABLED=$(gcloud sql instances describe flashcards-db \
      --format="value(settings.backupConfiguration.enabled)")
    
    if [ "$BACKUP_ENABLED" != "True" ]; then
      echo "ERROR: Backups not enabled on flashcards-db"
      exit 1
    fi
    
    echo "✓ Backups verified"
```

---

## Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| "Backups not enabled" | Never configured | Run `gcloud sql instances patch` command |
| "No backups found" | Just enabled, hasn't run | Wait for backup window or trigger manual backup |
| "Backup failed" | Storage or permission issue | Check Cloud SQL logs in console |
| "PITR not available" | Not enabled at creation | Enable with `--enable-point-in-time-recovery` |
| "Old backup" | Backup job not running | Check instance status, backup window |

---

**Template Version**: 3.8  
**Last Updated**: December 2025  
**Methodology**: [coreyprator/project-methodology](https://github.com/coreyprator/project-methodology)
