#!/usr/bin/env python3
"""
weekly_revenue.py

Aggregate daily revenue JSON into weekly revenue and optionally post to MongoDB.

Usage:
  python weekly_revenue.py path/to/daily_revenue.json

Output:
  output/weekly_revenue.json

Behavior:
- Reads daily records with shape [{date: YYYY-MM-DD, branch1: value, branch2: value, ..., total: value}, ...]
- Aggregates sums by ISO week (Monday-start) for each branch and total.
- Writes `output/weekly_revenue.json` with entries: {"week_start": "YYYY-MM-DD", "branch_id": value, ..., "total": value}
- Posts the weekly collection to MongoDB `weekly_revenue` (replaces contents).
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List
import os

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None


def read_json(path: Path) -> List[Dict]:
    with path.open('r', encoding='utf-8') as f:
        return json.load(f)


def write_weekly_to_mongo(records: List[Dict]):
    try:
        from pymongo import MongoClient
    except Exception:
        raise RuntimeError('pymongo is not installed')

    if load_dotenv:
        env_path = Path(__file__).parent.parent / '.env'
        if env_path.exists():
            load_dotenv(env_path)

    mongo_uri = os.environ.get('MONGO_URI') or os.environ.get('MONGODB_URI') or 'mongodb://localhost:27017'
    db_name = os.environ.get('MONGO_DB') or os.environ.get('MONGO_DB_NAME') or 'swas'

    client = MongoClient(mongo_uri)
    try:
        db_name_env = os.environ.get('MONGO_DB') or os.environ.get('MONGO_DB_NAME')
        default_db = None
        try:
            default_db = client.get_default_database()
        except Exception:
            default_db = None

        if default_db is not None and not db_name_env:
            db_name = default_db.name
        else:
            db_name = db_name_env or (default_db.name if default_db is not None else 'swas')

        db = client[db_name]
        coll = db['weekly_revenue']

        coll.delete_many({})
        inserted = 0
        if records:
            res = coll.insert_many(records)
            inserted = len(res.inserted_ids) if res and hasattr(res, 'inserted_ids') else len(records)
        print(f'Wrote {inserted} weekly records to MongoDB collection "{db_name}.weekly_revenue"')
    finally:
        client.close()


def aggregate_weekly(data: List[Dict]) -> List[Dict]:
    # data items expected to have 'date' key and branch columns
    rows = []
    for r in data:
        dstr = r.get('date')
        try:
            d = datetime.fromisoformat(dstr)
        except Exception:
            try:
                d = datetime.strptime(dstr, '%Y-%m-%d')
            except Exception:
                continue
        rows.append((d.date(), r))

    # group by ISO week starting Monday -> compute week_start date
    weeks: Dict[datetime.date, Dict[str, float]] = {}
    for ddate, row in rows:
        # find monday of this week
        monday = ddate - timedelta(days=ddate.weekday())
        if monday not in weeks:
            weeks[monday] = {}
        for k, v in row.items():
            if k == 'date':
                continue
            try:
                val = float(v or 0.0)
            except Exception:
                val = 0.0
            weeks[monday][k] = weeks[monday].get(k, 0.0) + val

    # convert to list sorted by week_start
    out = []
    for wk in sorted(weeks.keys()):
        rec = {'week_start': wk.isoformat()}
        rec.update({k: round(v, 2) for k, v in weeks[wk].items()})
        out.append(rec)
    return out


def main():
    if len(sys.argv) < 2:
        print('Usage: python weekly_revenue.py path/to/daily_revenue.json')
        raise SystemExit(2)

    inp = Path(sys.argv[1])
    if not inp.exists():
        print('Input file not found:', inp)
        raise SystemExit(2)

    data = read_json(inp)
    # If a weekly forecast exists, use its earliest week_start as the minimum week to include
    forecast_path = Path('output/weekly_forecast.json')
    min_week = None
    if forecast_path.exists():
        try:
            fc = read_json(forecast_path)
            # fc is expected to be list of dicts with 'week_start'
            wk_dates = []
            for item in fc:
                ws = item.get('week_start') or item.get('date')
                if not ws:
                    continue
                try:
                    d = datetime.fromisoformat(ws)
                except Exception:
                    try:
                        d = datetime.strptime(ws, '%Y-%m-%d')
                    except Exception:
                        continue
                wk_dates.append(d.date())
            if wk_dates:
                min_week = min(wk_dates)
        except Exception:
            min_week = None

    weekly = aggregate_weekly(data)

    if min_week is not None:
        # filter to weeks >= min_week
        weekly = [w for w in weekly if datetime.fromisoformat(w['week_start']).date() >= min_week]

    outp = Path('output/weekly_revenue.json')
    outp.parent.mkdir(parents=True, exist_ok=True)
    with outp.open('w', encoding='utf-8') as f:
        json.dump(weekly, f, indent=2)
    print('Wrote weekly revenue to', outp)

    try:
        write_weekly_to_mongo(weekly)
    except Exception as e:
        print('Warning: failed to write weekly revenue to MongoDB:', e)


if __name__ == '__main__':
    main()
