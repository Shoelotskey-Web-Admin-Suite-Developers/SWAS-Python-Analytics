#!/usr/bin/env python3
"""
run_daily_analytics.py

Master script to run the complete analytics pipeline in the correct order.
This script should be scheduled to run daily at 1AM.

Usage:
  python run_daily_analytics.py

The script will:
1. Clean transaction revenue from database
2. Calculate daily revenue
3. Generate sales over time data
4. Generate monthly growth analytics
5. Generate revenue forecasts

All outputs go to the output/ folder and database collections are updated.
"""

import sys
import subprocess
import time
from pathlib import Path

from date_utils import get_current_datetime

def log_message(message: str):
    """Log message with timestamp"""
    timestamp = get_current_datetime().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def run_script(script_name: str, args: list = None) -> bool:
    """Run a Python script and return success status"""
    try:
        cmd = [sys.executable, script_name]
        if args:
            cmd.extend(args)
        
        log_message(f"🚀 Starting {script_name}...")
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent)
        
        if result.returncode == 0:
            log_message(f"✅ {script_name} completed successfully")
            if result.stdout.strip():
                print(result.stdout)
            return True
        else:
            log_message(f"❌ {script_name} failed with return code {result.returncode}")
            if result.stderr.strip():
                print("STDERR:", result.stderr)
            if result.stdout.strip():
                print("STDOUT:", result.stdout)
            return False
            
    except Exception as e:
        log_message(f"❌ Error running {script_name}: {e}")
        return False

def main():
    """Run the complete analytics pipeline"""
    log_message("🏁 Starting Daily Analytics Pipeline")
    log_message("=" * 60)
    
    # Define the scripts in execution order
    scripts = [
        ("clean_transaction_revenue.py", []),
        ("calc_daily_revenue.py", []),
        ("forecast.py", ["output/daily_revenue.json"]),
        ("weekly_revenue.py", ["output/daily_revenue.json"]),
        ("sales_over_time.py", []),
        ("monthly_growth.py", [])
    ]
    
    success_count = 0
    total_scripts = len(scripts)
    
    start_time = time.time()
    
    for script_name, args in scripts:
        if run_script(script_name, args):
            success_count += 1
        else:
            log_message(f"⚠️  Pipeline continuing despite {script_name} failure...")
        
        # Add small delay between scripts
        time.sleep(1)
    
    end_time = time.time()
    duration = end_time - start_time
    
    log_message("=" * 60)
    log_message(f"📊 Pipeline Summary:")
    log_message(f"   ✅ Successful: {success_count}/{total_scripts}")
    log_message(f"   ⏱️  Duration: {duration:.2f} seconds")
    
    if success_count == total_scripts:
        log_message("🎉 Daily Analytics Pipeline completed successfully!")
        return 0
    else:
        log_message(f"⚠️  Pipeline completed with {total_scripts - success_count} failures")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)