# Daily Analytics Pipeline Scheduling Guide

This document explains how to schedule the daily analytics pipeline to run automatically at 1AM.

## Scripts Overview

The pipeline consists of these scripts in order:
1. `clean_transaction_revenue.py` - Extract completed transactions from database
2. `calc_daily_revenue.py` - Generate daily revenue aggregations
3. `sales_over_time.py` - Update sales over time data in database
4. `monthly_growth.py` - Generate monthly growth analytics
5. `forecast.py` - Generate revenue forecasts

## Master Scripts Created

- `run_daily_analytics.py` - Python master script that runs all scripts in order
- `run_daily_analytics.bat` - Windows batch file
- `run_daily_analytics.sh` - Linux/Unix shell script

## Scheduling Options

### 1. Windows Task Scheduler

**For Windows hosting environments:**

1. Open Task Scheduler (`taskschd.msc`)
2. Create Basic Task:
   - Name: "Daily Analytics Pipeline"
   - Trigger: Daily at 1:00 AM
   - Action: Start a program
   - Program: `C:\path\to\your\project\server\scripts\run_daily_analytics.bat`
   - Start in: `C:\path\to\your\project\server\scripts`

**PowerShell command to create the task:**
```powershell
$TaskName = "Daily Analytics Pipeline"
$ScriptPath = "C:\Users\Lagman\Desktop\Codes\SWAS PWA\SWAS-PWA\server\scripts\run_daily_analytics.bat"
$WorkingDir = "C:\Users\Lagman\Desktop\Codes\SWAS PWA\SWAS-PWA\server\scripts"

$Action = New-ScheduledTaskAction -Execute $ScriptPath -WorkingDirectory $WorkingDir
$Trigger = New-ScheduledTaskTrigger -Daily -At "1:00AM"
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -User "SYSTEM"
```

### 2. Linux Cron Job

**For Linux hosting environments:**

1. Edit crontab: `crontab -e`
2. Add this line:
```bash
0 1 * * * /path/to/your/project/server/scripts/run_daily_analytics.sh >> /path/to/your/project/server/scripts/logs/analytics.log 2>&1
```

**Or using the Python script directly:**
```bash
0 1 * * * cd /path/to/your/project/server/scripts && /path/to/your/project/server/scripts/.venv311/bin/python run_daily_analytics.py >> logs/analytics.log 2>&1
```

### 3. Cloud Hosting Solutions

#### **Heroku Scheduler**
If using Heroku, add to your `Procfile`:
```
worker: cd server/scripts && python run_daily_analytics.py
```

Then use Heroku Scheduler add-on:
```bash
heroku addons:create scheduler:standard
heroku addons:open scheduler
```
Set task: `cd server/scripts && python run_daily_analytics.py`
Schedule: Daily at 1:00 AM

#### **AWS Lambda + CloudWatch Events**
1. Package the scripts as a Lambda function
2. Use CloudWatch Events to trigger at 1 AM daily
3. Cron expression: `0 1 * * ? *`

#### **Google Cloud Functions + Cloud Scheduler**
1. Deploy scripts as Cloud Function
2. Use Cloud Scheduler with cron: `0 1 * * *`

#### **Digital Ocean App Platform**
Add to `.do/app.yaml`:
```yaml
workers:
- name: analytics-pipeline
  source_dir: server/scripts
  run_command: python run_daily_analytics.py
  instance_count: 1
  instance_size_slug: basic-xxs
```

### 4. Docker-based Scheduling

**Create a Dockerfile for the analytics:**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY server/scripts /app
COPY server/.env /app/../.env
RUN pip install -r requirements.txt
CMD ["python", "run_daily_analytics.py"]
```

**Use with cron or Kubernetes CronJob:**
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: daily-analytics
spec:
  schedule: "0 1 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: analytics
            image: your-analytics-image
            command: ["python", "run_daily_analytics.py"]
          restartPolicy: OnFailure
```

### 5. PM2 (Node.js Process Manager)

**Create ecosystem.config.js:**
```javascript
module.exports = {
  apps: [{
    name: 'daily-analytics',
    script: 'run_daily_analytics.py',
    interpreter: 'python3',
    cwd: './server/scripts',
    cron_restart: '0 1 * * *',
    watch: false,
    autorestart: false
  }]
}
```

## Logging and Monitoring

### Enable Logging
Create a logs directory and modify the scripts to write to log files:

```bash
mkdir server/scripts/logs
```

### Log Rotation
For production, consider log rotation to prevent disk space issues.

### Monitoring
- Set up alerts for failed pipeline runs
- Monitor database connection health
- Track execution time trends

## Environment Considerations

### Production Checklist:
- [ ] Environment variables (.env file) properly configured
- [ ] Database connection tested
- [ ] Python virtual environment activated
- [ ] All required packages installed
- [ ] Proper file permissions set
- [ ] Timezone configured correctly for 1AM execution
- [ ] Error handling and logging in place
- [ ] Backup and recovery procedures defined

### Security Notes:
- Store database credentials securely (environment variables, secrets management)
- Run with minimal required permissions
- Regularly update dependencies
- Monitor for suspicious activity

## Testing the Pipeline

Test the complete pipeline manually before scheduling:

```bash
# Windows
run_daily_analytics.bat

# Linux/Mac
./run_daily_analytics.sh

# Direct Python
python run_daily_analytics.py
```

## Troubleshooting

Common issues:
1. **Path issues**: Ensure working directory is correct
2. **Virtual environment**: Verify Python environment activation
3. **Database connectivity**: Check network and credentials
4. **File permissions**: Ensure read/write access to output folder
5. **Dependencies**: Verify all Python packages are installed

For detailed logs, check the script output or system event logs.