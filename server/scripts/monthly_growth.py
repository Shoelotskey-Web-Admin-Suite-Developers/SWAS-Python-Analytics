#!/usr/bin/env python3
"""monthly_growth.py

Read daily_revenue.json (array of per-day objects with branch fields),
group by month (YYYY-MM), sum revenue per branch, compute total, write
monthly_revenue.json and upsert documents into MongoDB collection
`monthly_revenue`.

Usage:
  python monthly_growth.py server/scripts/output/daily_revenue.json
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from date_utils import get_current_datetime

try:
    from dotenv import load_dotenv
except ImportError:
    print("Warning: python-dotenv not installed. Environment variables from .env file won't be loaded.")
    load_dotenv = None


def read_json(path: Path) -> List[Dict[str, Any]]:
    with path.open('r', encoding='utf-8') as f:
        return json.load(f)


def month_key_from_date(date_str: str) -> str:
    # expecting YYYY-MM-DD ... return YYYY-MM
    try:
        return datetime.fromisoformat(date_str).strftime('%Y-%m')
    except Exception:
        # fallback: split
        return date_str[:7]


def aggregate_monthly(daily_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # daily_records: list of dicts where one key is 'date' and other keys are branch codes
    per_month: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
    months_seen = set()

    for r in daily_records:
        date = r.get('date') or r.get('day') or r.get('date_out')
        if not date:
            continue
        month = month_key_from_date(date)
        months_seen.add(month)

        # for each key other than 'date' and 'total' and numeric-ish values, add
        for k, v in r.items():
            if k in ('date', 'day', 'date_out', 'total'):
                continue
            # skip non-branch metadata
            if not isinstance(k, str):
                continue
            # try to treat value as number
            try:
                amt = float(v) if v not in (None, '') else 0.0
            except Exception:
                continue
            per_month[month][k] += amt

    out: List[Dict[str, Any]] = []
    for month in sorted(per_month.keys()):
        obj: Dict[str, Any] = {'month': month}
        total = 0.0
        # sort branch keys for deterministic output
        for branch in sorted(per_month[month].keys()):
            amt = round(per_month[month][branch], 2)
            obj[branch] = amt
            total += amt
        obj['total'] = round(total, 2)
        out.append(obj)

    return out


def write_json(path: Path, data: List[Dict[str, Any]]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def write_to_mongo(monthly_records: List[Dict[str, Any]]):
    try:
        from pymongo import MongoClient
    except Exception:
        raise RuntimeError('pymongo is required; install it in the environment')

    # Load environment variables from .env file
    if load_dotenv:
        # Look for .env file in parent directory (server/)
        env_path = Path(__file__).parent.parent / '.env'
        if env_path.exists():
            load_dotenv(env_path)
            print(f"[ENV] Loaded environment variables from: {env_path}")
        else:
            print("⚠️  No .env file found in server directory")

    mongo_uri = os.environ.get('MONGO_URI') or os.environ.get('MONGODB_URI') or 'mongodb://localhost:27017'

    client = MongoClient(mongo_uri)
    try:
        db_override = os.environ.get('MONGO_DB') or os.environ.get('MONGO_DB_NAME')
        default_db = None
        try:
            default_db = client.get_default_database()
        except Exception:
            default_db = None

        if default_db is not None and not db_override:
            db_name = default_db.name
        else:
            db_name = db_override or (default_db.name if default_db is not None else 'swas')
        db = client[db_name]
        coll = db['monthly_growth']

        # monthly_records expected to be the aggregated form (has key 'month')
        # We will upsert only the most recent 2 months that have non-zero data.
        # Build the 12-record series for completeness (used for year/branches and zero-month placeholders)
        monthly_12 = build_12_series(monthly_records) if monthly_records else []

        # Determine target year from monthly_12 (if present) or from aggregated_monthly
        target_year = None
        if monthly_12:
            # monthly_12 items use 'Year' key
            target_year = monthly_12[0].get('Year')
        else:
            years = [int(r.get('month')[:4]) for r in monthly_records if r.get('month')]
            target_year = max(years) if years else None

        # gather monthly_12 docs that have branch data (non-zero excluding metadata)
        def doc_has_data(doc: Dict[str, Any]) -> bool:
            branch_keys = [k for k in doc.keys() if k not in ('date', 'month_label', 'month_number', 'year', 'Year', 'month')]
            return any((doc.get(k, 0) or 0) != 0 for k in branch_keys)

        docs_with_data = [d for d in monthly_12 if doc_has_data(d)]

        # sort months by their month number within the year to find the most recent ones
        def month_number_from_name(mname: str) -> int:
            try:
                return datetime.strptime(mname, '%b').month
            except Exception:
                # fallback: if mname is like 'YYYY-MM'
                try:
                    return int(mname.split('-')[1])
                except Exception:
                    return 0

        # attach month_number for sorting
        for d in monthly_12:
            if 'month_number' not in d:
                # try to parse if month field is name like 'Jan'
                if isinstance(d.get('month'), str):
                    try:
                        d['month_number'] = month_number_from_name(d['month'])
                    except Exception:
                        d['month_number'] = 0
                else:
                    d['month_number'] = d.get('month_number', 0)

        # sort docs_with_data by month_number desc
        docs_with_data_sorted = sorted([d for d in monthly_12 if doc_has_data(d)], key=lambda x: x.get('month_number', 0), reverse=True)

        # pick only the most recent month with data
        recent_one = docs_with_data_sorted[:1]

        # If this target_year is not yet in DB at all, replace all revenue across branches with zero for that year.
        year_exists = coll.find_one({'Year': target_year}) if target_year is not None else None
        zeroed_replaced = 0
        if target_year is not None and not year_exists:
            # Build a zeroed doc for each month in monthly_12 for the year and replace existing docs for that year
            # Collect branch keys from monthly_12
            branches = set()
            for r in monthly_12:
                for k in r.keys():
                    if k in ('month', 'date', 'total', 'Year', 'year', 'month_number'):
                        continue
                    branches.add(k)

            # For each month in monthly_12, create a zeroed doc and replace existing (or insert)
            for d in monthly_12:
                zero_doc = {'month': d.get('month'), 'Year': d.get('Year')}
                for b in sorted(branches):
                    zero_doc[b] = 0.0
                zero_doc['total'] = 0.0
                # replace existing docs for that month/year
                res = coll.replace_one({'month': d.get('month'), 'Year': d.get('Year')}, zero_doc, upsert=True)
                zeroed_replaced += 1

        # Now upsert only the most recent month that has data (replace by month+Year)
        upserted = 0
        for doc in recent_one:
            # ensure the doc has 'month' and 'Year' keys suitable for query
            query = {'month': doc.get('month'), 'Year': doc.get('Year')}
            # replace the document with the one from monthly_12 (ensure numeric rounding preserved)
            res = coll.replace_one(query, doc, upsert=True)
            upserted += 1

        print(f'Replaced {zeroed_replaced} docs with zeroed revenue for Year={target_year} (if it was new).')
        print(f'Upserted/updated {upserted} most-recent month with data into {db_name}.monthly_growth (year={target_year})')
    finally:
        client.close()


def build_12_series(aggregated_monthly: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # aggregated_monthly: list with {'month': 'YYYY-MM', 'total': ...}
    years = []
    for r in aggregated_monthly:
        m = r.get('month')
        if m and isinstance(m, str) and len(m) >= 7:
            try:
                years.append(int(m[:4]))
            except Exception:
                continue

    target_year = max(years) if years else get_current_datetime().year

    totals_by_month = {r.get('month'): float(r.get('total', 0) or 0) for r in aggregated_monthly}

    latest_month_available = 0
    for mm in range(1, 13):
        key = f"{target_year}-{mm:02d}"
        if key in totals_by_month and totals_by_month[key] != 0:
            latest_month_available = max(latest_month_available, mm)

    if latest_month_available == 0:
        for r in aggregated_monthly:
            m = r.get('month')
            if m and m.startswith(str(target_year)):
                try:
                    latest_month_available = max(latest_month_available, int(m[5:7]))
                except Exception:
                    pass

    # collect branch keys across aggregated_monthly
    branches = set()
    for r in aggregated_monthly:
        for k in r.keys():
            if k in ('month', 'date', 'total'):
                continue
            branches.add(k)

    monthly_12 = []
    for mm in range(1, 13):
        key = f"{target_year}-{mm:02d}"
        month_name = datetime(target_year, mm, 1).strftime('%b')
        row: Dict[str, Any] = {'month': month_name, 'Year': target_year}
        total_val = 0.0
        for b in sorted(branches):
            val = 0.0
            entry = next((x for x in aggregated_monthly if x.get('month') == key), None)
            if entry:
                try:
                    val = float(entry.get(b, 0) or 0)
                except Exception:
                    val = 0.0
            # if month is after latest available, zero it
            if latest_month_available and mm > latest_month_available:
                val = 0.0
            row[b] = round(val, 2)
            total_val += val

        row['total'] = round(total_val, 2)
        monthly_12.append(row)

    return monthly_12


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('output/daily_revenue.json')
    if not path.exists():
        print('Input file not found:', path)
        raise SystemExit(2)

    data = read_json(path)
    monthly = aggregate_monthly(data)

    out_path = Path('output/monthly_growth.json')
    # write 12-record series to JSON
    monthly_12 = build_12_series(monthly)
    write_json(out_path, monthly_12)
    print(f'Wrote {len(monthly_12)} months to {out_path}')

    # write to mongo
    try:
        write_to_mongo(monthly)
    except Exception as e:
        print('Warning: failed to write to MongoDB:', e)

    # summary
    print(f'Processed {len(monthly)} months')


if __name__ == '__main__':
    main()
