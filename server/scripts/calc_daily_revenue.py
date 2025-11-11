#!/usr/bin/env python3
"""
calc_daily_revenue.py

Reads transactions, line_items, payments, and customers files (CSV or JSON),
computes daily revenue for completed transactions (date_out not null), and
writes `daily_revenue.csv` with columns: date, branch_id, total_transactions,
total_revenue, average_revenue_per_transaction

Usage:
  python calc_daily_revenue.py --transactions transactions.csv --line-items line_items.csv --payments payments.csv --customers customers.csv --out daily_revenue.csv

If JSON files from the generator exist (test_transactions.json etc.), they will be accepted too.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Any


def read_json_or_csv(path: str) -> List[Dict[str, Any]]:
    if path.lower().endswith('.json'):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        rows = []
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows.append(r)
        return rows


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--transactions', required=False)
    p.add_argument('--line-items', required=False)
    p.add_argument('--payments', required=False)
    p.add_argument('--customers', required=False)
    p.add_argument('--cleaned', required=False, default='output/cleaned_transactions_revenue.csv', help='Path to cleaned_transactions_revenue.csv (date_time,transaction_id,revenue,branch_id)')
    p.add_argument('--out', default='output/daily_revenue.json')
    return p.parse_args()


def to_float(v):
    try:
        return float(v)
    except Exception:
        return 0.0


def parse_date(v: str):
    if v is None:
        return None
    if isinstance(v, datetime):
        return v
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S.%f"):
        try:
            return datetime.strptime(v, fmt)
        except Exception:
            continue
    try:
        # last resort: parse date portion only
        return datetime.fromisoformat(v)
    except Exception:
        return None


def main():
    args = parse_args()

    # If cleaned CSV is provided, we don't need to read the other files
    if args.cleaned:
        tx_rows = []
        li_rows = []
        pay_rows = []
        cu_rows = []
    else:
        if not (args.transactions and args.line_items and args.payments and args.customers):
            raise SystemExit('When --cleaned is not provided, --transactions, --line-items, --payments and --customers are required')
        tx_rows = read_json_or_csv(args.transactions)
        li_rows = read_json_or_csv(args.line_items)
        pay_rows = read_json_or_csv(args.payments)
        cu_rows = read_json_or_csv(args.customers)

    # Build lookup for line items
    li_by_id: Dict[str, Dict[str, Any]] = {}
    for r in li_rows:
        lid = r.get('line_item_id') or r.get('lineItemId') or r.get('id')
        if lid is None:
            continue
        # Normalize numeric fields
        qty = to_float(r.get('quantity') or r.get('qty') or 0)
        price = to_float(r.get('price_per_unit') or r.get('price') or r.get('unit_price') or 0)
        li_by_id[str(lid)] = {**r, 'quantity': qty, 'price_per_unit': price}

    # Build payments sum per transaction
    payments_by_tx: Dict[str, float] = defaultdict(float)
    for r in pay_rows:
        txid = r.get('transaction_id') or r.get('transactionId')
        if not txid:
            continue
        amt = to_float(r.get('amount') or r.get('payment_amount') or r.get('payment') or 0)
        payments_by_tx[str(txid)] += amt

    # For each completed transaction (date_out not null), compute computed_line_total and use payments total
    # Transactions may store line_item_id as list or as string representation
    trx_list = []
    for r in tx_rows:
        date_out_raw = r.get('date_out')
        date_out_dt = parse_date(date_out_raw) if date_out_raw not in (None, '', 'null') else None
        if date_out_dt is None:
            continue

        txid = r.get('transaction_id') or r.get('transactionId')
        branch_id = r.get('branch_id') or r.get('branchId') or r.get('branch')

        # line items
        li_field = r.get('line_item_id')
        li_list = []
        if isinstance(li_field, list):
            li_list = li_field
        elif isinstance(li_field, str):
            # try to parse JSON list
            if li_field.startswith('['):
                try:
                    li_list = json.loads(li_field)
                except Exception:
                    li_list = [li_field]
            else:
                li_list = [li_field]
        elif li_field is None:
            li_list = []
        else:
            li_list = [li_field]

        computed_total = 0.0
        for lid in li_list:
            lid_str = str(lid)
            item = li_by_id.get(lid_str)
            if item:
                computed_total += item.get('quantity', 0) * item.get('price_per_unit', 0)

        payments_total = payments_by_tx.get(str(txid), 0.0)

        trx_list.append({
            'transaction_id': str(txid),
            'branch_id': branch_id,
            'date_out': date_out_dt.date().isoformat(),
            'computed_line_total': round(computed_total, 2),
            'payments_total': round(payments_total, 2),
        })

    # Aggregate per date & branch
    daily: Dict[str, Dict[str, Any]] = {}
    for t in trx_list:
        key = (t['date_out'], t['branch_id'])
        if key not in daily:
            daily[key] = {'date': t['date_out'], 'branch_id': t['branch_id'], 'total_transactions': 0, 'total_revenue': 0.0}
        daily[key]['total_transactions'] += 1
        daily[key]['total_revenue'] += t['payments_total']

    out_path = args.out
    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)

    # If user provided a cleaned CSV, prefer that for a faster path
    if args.cleaned:
        # cleaned CSV expected columns: date_time,transaction_id,revenue,branch_id
        per_date_branch: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        all_branches = set()
        with open(args.cleaned, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for r in reader:
                dt = r.get('date_time') or r.get('date')
                if not dt:
                    continue
                # extract date portion
                try:
                    date_only = parse_date(dt).date().isoformat()
                except Exception:
                    date_only = dt.split('T')[0]
                branch = r.get('branch_id') or r.get('branch') or r.get('branchId')
                if branch is None:
                    branch = 'UNKNOWN'
                all_branches.add(branch)
                revenue = to_float(r.get('revenue') or r.get('amount') or 0)
                per_date_branch[date_only][branch] += revenue

        # Write JSON array if out_path ends with .json, otherwise CSV (fallback)
        if out_path.lower().endswith('.json'):
            json_arr = []
            for date in sorted(per_date_branch.keys()):
                obj = {'date': date}
                total = 0.0
                # include all branches with 0.0 if missing for the date
                for branch in sorted(all_branches):
                    amt = per_date_branch[date].get(branch, 0.0)
                    obj[str(branch)] = round(amt, 2)
                    total += amt
                obj['total'] = round(total, 2)
                json_arr.append(obj)
            with open(out_path, 'w', encoding='utf-8') as f:
                json.dump(json_arr, f, indent=2)
            print(f'Wrote daily revenue JSON to {out_path}')
            return
        else:
            # fallback: write CSV with columns date, branch_id, total_transactions=NA, total_revenue
            with open(out_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['date', 'branch_id', 'total_revenue'])
                for date in sorted(per_date_branch.keys()):
                    for branch in sorted(per_date_branch[date].keys()):
                        writer.writerow([date, branch, f"{per_date_branch[date][branch]:.2f}"])
            print(f'Wrote daily revenue CSV to {out_path} (from cleaned input)')
            return

    # If user requested JSON output, write an array of objects per date/branch
    if out_path.lower().endswith('.json'):
        json_arr = []
        for key in sorted(daily.keys()):
            rec = daily[key]
            total = rec['total_transactions']
            revenue = round(rec['total_revenue'], 2)
            avg = round(revenue / total, 2) if total > 0 else 0.0
            json_arr.append({
                'date': rec['date'],
                'branch_id': rec['branch_id'],
                'total_transactions': total,
                'total_revenue': revenue,
                'average_revenue_per_transaction': avg,
            })
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(json_arr, f, indent=2)
        print(f'Wrote daily revenue JSON to {out_path}')
    else:
        # fallback: write CSV for non-JSON output paths
        with open(out_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['date', 'branch_id', 'total_transactions', 'total_revenue', 'average_revenue_per_transaction'])
            for key in sorted(daily.keys()):
                rec = daily[key]
                total = rec['total_transactions']
                revenue = round(rec['total_revenue'], 2)
                avg = round(revenue / total, 2) if total > 0 else 0.0
                writer.writerow([rec['date'], rec['branch_id'], total, f"{revenue:.2f}", f"{avg:.2f}"])

        print(f'Wrote daily revenue to {out_path}')


if __name__ == '__main__':
    main()
