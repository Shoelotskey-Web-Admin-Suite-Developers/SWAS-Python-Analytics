#!/usr/bin/env python3
"""
forecast.py

Reads daily revenue JSON and produces a weekly forecast window for each branch.

Usage:
  python forecast.py server/scripts/output/daily_revenue.json

Output:
  server/scripts/output/forecast_output.json

Behavior:
- Tries to use pandas and statsmodels' ExponentialSmoothing for Holt-Winters.
- If unavailable, falls back to a simple rolling-mean forecast.
 - Aggregates daily revenue into weekly totals (week starting Monday)
 - Produces a 17-week window: ~4 weeks past (last month), current week, ~12 weeks future (3 months)
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List
from statistics import median
import os

from date_utils import get_current_date, get_current_datetime

try:
    from dotenv import load_dotenv
except ImportError:
    print("Warning: python-dotenv not installed. Environment variables from .env file won't be loaded.")
    load_dotenv = None

try:
    import pandas as pd
    HAVE_PANDAS = True
except Exception:
    HAVE_PANDAS = False

try:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    HAVE_HW = True
except Exception:
    HAVE_HW = False

# Try Prophet (two possible package names)
HAVE_PROPHET = False
PROPHET = None
try:
    from prophet import Prophet as _Prophet
    HAVE_PROPHET = True
    PROPHET = _Prophet
except Exception:
    try:
        from fbprophet import Prophet as _Prophet2
        HAVE_PROPHET = True
        PROPHET = _Prophet2
    except Exception:
        HAVE_PROPHET = False


def read_json(path: Path) -> List[Dict]:
    with path.open('r', encoding='utf-8') as f:
        return json.load(f)


def to_date(dstr: str) -> datetime:
    # Accept multiple formats; try ISO first
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%b %d", "%b %d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(dstr, fmt)
        except Exception:
            continue
    # Last resort: try fromisoformat
    try:
        return datetime.fromisoformat(dstr)
    except Exception:
        # If the input date is like 'Aug 16' (no year), assume current year
        try:
            return datetime.strptime(dstr + f" {get_current_datetime().year}", "%b %d %Y")
        except Exception:
            raise


def forecast_series(dates: List[datetime], values: List[float], periods_ahead: int = 7, freq: str = 'D') -> List[float]:
    """Return forecast for periods_ahead into the future.
    If statsmodels Holt-Winters available, use it; otherwise use naive moving average of last 7 days.
    """
    # Prefer Prophet if available
    if HAVE_PROPHET and HAVE_PANDAS:
        try:
            df = pd.DataFrame({'ds': pd.DatetimeIndex(dates), 'y': values})
            m = PROPHET()
            m.fit(df)
            future = m.make_future_dataframe(periods=periods_ahead, freq=freq)
            fcst = m.predict(future)
            preds = fcst['yhat'].iloc[-periods_ahead:].tolist()
            return [float(x) for x in preds]
        except Exception:
            pass

    if HAVE_HW and HAVE_PANDAS:
        s = pd.Series(values, index=pd.DatetimeIndex(dates))
        # fit additive model without seasonality (simple)
        try:
            model = ExponentialSmoothing(s, trend='add', seasonal=None, damped_trend=False)
            fit = model.fit(optimized=True)
            pred = fit.forecast(periods_ahead)
            return [float(x) for x in pred.tolist()]
        except Exception:
            pass

    # fallback: simple average of last 7 values
    if len(values) == 0:
        return [0.0] * periods_ahead
    window = min(7, len(values))
    base = sum(values[-window:]) / window
    return [round(base, 2)] * periods_ahead


def write_forecast_to_mongo(records: List[Dict], collection_name: str = 'forecast'):
    """Write the forecast records (list of dicts) to MongoDB collection `forecast`.

    Replaces the collection's documents each run so the collection contains only
    the latest 17 records.
    Uses MONGO_URI environment variable if set, otherwise connects to
    mongodb://localhost:27017 and database 'swas'.
    """
    try:
        from pymongo import MongoClient
    except Exception:
        raise RuntimeError('pymongo is not installed')

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
    db_name = os.environ.get('MONGO_DB') or os.environ.get('MONGO_DB_NAME') or 'swas'

    client = MongoClient(mongo_uri)
    try:
        # If the connection URI includes a default database (e.g. mongodb+srv://.../swas_database),
        # prefer that database unless MONGO_DB explicit override is provided.
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

        print(f'Connecting to MongoDB database "{db_name}"')

        db = client[db_name]
        coll = db[collection_name]

        # Ensure we only insert the last 17 records
        limited = records[-17:]

        # Replace the collection atomically: delete and insert many
        coll.delete_many({})
        inserted = 0
        if limited:
            # Let pymongo convert date strings if needed
            res = coll.insert_many(limited)
            inserted = len(res.inserted_ids) if res and hasattr(res, 'inserted_ids') else len(limited)

        # feedback
        print(f'Wrote {inserted} forecast records to MongoDB collection "{db_name}.{collection_name}"')
    finally:
        client.close()


def main():
    if len(sys.argv) < 2:
        print('Usage: python forecast.py path/to/daily_revenue.json')
        raise SystemExit(2)

    inp = Path(sys.argv[1])
    if not inp.exists():
        print('Input file not found:', inp)
        raise SystemExit(2)

    data = read_json(inp)
    # try to load promos/unavailability from expected output folder
    base_dir = inp.parent
    promos = []
    unavailability = []
    try:
        ppath = base_dir / 'promos.json'
        if ppath.exists():
            promos = read_json(ppath)
    except Exception:
        promos = []
    try:
        upath = base_dir / 'unavailability.json'
        if upath.exists():
            unavailability = read_json(upath)
    except Exception:
        unavailability = []
    # Build pandas DataFrame if available
    rows = []
    branches = set()
    for r in data:
        date_str = r.get('date')
        try:
            dt = to_date(date_str)
        except Exception:
            # skip bad rows
            continue
        row = {'date': dt}
        for k, v in r.items():
            if k == 'date':
                continue
            row[k] = float(v or 0.0)
            branches.add(k)
        rows.append(row)

    # Debug: show which model packages are available
    print(f"[MODELS] HAVE_PANDAS={HAVE_PANDAS}, HAVE_PROPHET={HAVE_PROPHET}, HAVE_HW={HAVE_HW}")

    rows.sort(key=lambda x: x['date'])
    if not rows:
        print('No data rows found to forecast.')
        return

    branch_list = sorted([b for b in branches if b != 'total'])

    # Determine target window in weeks: ~4 past weeks (approx 1 month), current week, ~12 future weeks (approx 3 months)
    today = get_current_date()
    current_week = today - timedelta(days=today.weekday())
    start_week = current_week - timedelta(weeks=4)
    end_week = current_week + timedelta(weeks=12)
    window_weeks = [start_week + timedelta(weeks=i) for i in range(((end_week - start_week).days // 7) + 1)]

    weekly_actual_map: Dict[datetime.date, Dict[str, float]] = {}
    branch_forecasts: Dict[str, Dict[datetime.date, float]] = {}

    if HAVE_PANDAS:
        import pandas as _pd

        df_all = _pd.DataFrame(rows).set_index('date').sort_index()
        df_all = df_all.fillna(0.0)
        full_index = _pd.date_range(df_all.index.min(), df_all.index.max(), freq='D')
        df_all = df_all.reindex(full_index, fill_value=0.0)

        weekly_actual_df = df_all[branch_list].resample('W-MON', label='left', closed='left').sum()
        for ts, row in weekly_actual_df.iterrows():
            weekly_actual_map[ts.date()] = {b: float(row.get(b, 0.0)) for b in branch_list}
    else:
        weekly_map: Dict[datetime.date, Dict[str, float]] = {}
        for r in rows:
            d = r['date'].date()
            week_start = d - timedelta(days=d.weekday())
            if week_start not in weekly_map:
                weekly_map[week_start] = {}
            for k, v in r.items():
                if k == 'date' or k == 'total':
                    continue
                weekly_map[week_start][k] = weekly_map[week_start].get(k, 0.0) + float(v or 0.0)
        for wk, data in weekly_map.items():
            weekly_actual_map[wk] = data

    if not weekly_actual_map:
        weekly_actual_map = {}

    hist_weeks_sorted = sorted(weekly_actual_map.keys())
    last_actual_week = hist_weeks_sorted[-1] if hist_weeks_sorted else None

    def compute_smooth_forecasts(values: List[float], future_count: int) -> tuple[List[float], List[float]]:
        if not values:
            return [], [0.0] * future_count

        n = len(values)
        branch_median = median(values)
        mean_val = sum(values) / n if n else 0.0
        hist_min = min(values)
        hist_max = max(values)
        lower_bound = max(hist_min * 0.5, 0.0)
        upper_ref = hist_max if hist_max > 0 else max(mean_val, branch_median)
        upper_bound = max(upper_ref * 1.2, lower_bound + 300.0) if upper_ref else lower_bound + 300.0
        if branch_median:
            target_lower = max(hist_min * 0.6, lower_bound)
            target_upper = min(upper_bound, branch_median * 1.3)
        else:
            target_lower = lower_bound
            target_upper = upper_bound

        def robust_baseline(history: List[float]) -> float:
            if not history:
                return branch_median
            recent = history[-4:]
            med_recent = median(recent)
            med_history = median(history)
            if len(history) == 1:
                return 0.5 * branch_median + 0.5 * hist_min
            if len(history) == 2:
                return 0.45 * med_recent + 0.35 * branch_median + 0.2 * hist_min
            return 0.55 * med_recent + 0.25 * med_history + 0.15 * branch_median + 0.05 * hist_min

        def trend_adjust(history: List[float]) -> float:
            if len(history) < 3:
                return 0.0
            span = min(len(history), 5)
            window = history[-span:]
            diffs = [window[i] - window[i - 1] for i in range(1, len(window))]
            avg_diff = sum(diffs) / len(diffs) if diffs else 0.0
            cap = max(branch_median * 0.08, 40.0) if branch_median else 40.0
            return max(min(avg_diff * 0.5, cap), -cap)

        hindcasts: List[float] = []
        for idx in range(n):
            if idx == 0:
                hindcasts.append(max(min(values[0], target_upper), target_lower))
                continue
            history = values[:idx]
            baseline = robust_baseline(history)
            adj = trend_adjust(history)
            candidate = baseline + adj
            if hindcasts:
                candidate = 0.7 * candidate + 0.3 * hindcasts[-1]
            if branch_median:
                shrink = 0.5 if len(history) > 3 else 0.3 if len(history) > 1 else 0.15
                candidate = shrink * candidate + (1 - shrink) * branch_median
            hindcasts.append(max(min(candidate, target_upper), target_lower))

        residuals = [values[i] - hindcasts[i] for i in range(len(hindcasts))]
        seasonal_len = min(4, len(residuals))
        seasonal_pattern: List[float] = residuals[-seasonal_len:] if seasonal_len else []
        local_range = hist_max - hist_min
        base_variation = max(local_range * 0.25, (branch_median or mean_val) * 0.12)
        if seasonal_pattern:
            clipped = []
            for val in seasonal_pattern:
                clipped.append(max(min(val, base_variation), -base_variation))
            seasonal_pattern = clipped
        residual_scale = 0.5 if seasonal_pattern else 0.0

        future: List[float] = []
        history = values[:]
        for _ in range(future_count):
            baseline = robust_baseline(history)
            adj = trend_adjust(history)
            candidate = baseline + adj
            if future:
                candidate = 0.75 * candidate + 0.25 * future[-1]
            if branch_median:
                shrink = 0.55 if len(history) > 5 else 0.35 if len(history) > 2 else 0.2
                candidate = shrink * candidate + (1 - shrink) * branch_median
            if seasonal_pattern:
                idx = len(future)
                seasonal_adj = seasonal_pattern[idx % len(seasonal_pattern)] * residual_scale
            else:
                seasonal_adj = 0.0
            if seasonal_adj == 0.0 and local_range > 0:
                phase = (len(future) % 4)
                wiggle = (phase - 1.5) / 1.5
                seasonal_adj = wiggle * (base_variation * 0.1)
            candidate += seasonal_adj
            candidate = max(min(candidate, target_upper), target_lower)
            future.append(candidate)
            history.append(candidate)

        return hindcasts, future

    future_weeks = [wk for wk in window_weeks if not last_actual_week or wk > last_actual_week]

    for b in branch_list:
        branch_forecasts[b] = {}
        hist_values = [weekly_actual_map[wk].get(b, 0.0) for wk in hist_weeks_sorted]
        hindcasts, future = compute_smooth_forecasts(hist_values, len(future_weeks))

        hist_lookup = {wk: hindcasts[idx] if idx < len(hindcasts) else hist_values[idx]
                       for idx, wk in enumerate(hist_weeks_sorted)}
        for wk in window_weeks:
            if wk in hist_lookup:
                branch_forecasts[b][wk] = hist_lookup[wk]

        for idx, wk in enumerate(future_weeks):
            if idx < len(future):
                branch_forecasts[b][wk] = future[idx]
            elif future:
                branch_forecasts[b][wk] = future[-1]
            else:
                branch_forecasts[b][wk] = 0.0

    # Build output entries for each week in window
    out_list = []
    for wk in window_weeks:
        rec = {'week_start': wk.isoformat(), 'forecast': {}, 'actual': {}}
        total_forecast = 0.0
        total_actual = 0.0
        any_actual = False

        for b in branch_list:
            raw_forecast = branch_forecasts.get(b, {}).get(wk)
            forecast_val = round(raw_forecast, 2) if raw_forecast is not None else None

            actual_val = None
            if wk in weekly_actual_map:
                actual_val = weekly_actual_map[wk].get(b)

            rec['forecast'][b] = forecast_val
            rec['actual'][b] = round(actual_val, 2) if actual_val is not None else None

            if forecast_val is not None:
                rec[b] = forecast_val
                total_forecast += forecast_val
            else:
                rec[b] = round(actual_val, 2) if actual_val is not None else 0.0
                if actual_val is not None:
                    total_forecast += 0.0  # no forecast contribution
            if actual_val is not None:
                total_actual += actual_val
                any_actual = True

        display_total = sum(float(rec[b]) for b in branch_list)
        rec['total'] = round(display_total, 2)

        forecast_values = [val for val in rec['forecast'].values() if isinstance(val, (int, float))]
        if forecast_values:
            rec['forecast']['total'] = round(sum(forecast_values), 2)
        else:
            rec['forecast']['total'] = None
        rec['actual']['total'] = round(total_actual, 2) if any_actual else None
        out_list.append(rec)

    outp = Path('output/weekly_forecast.json')
    outp.parent.mkdir(parents=True, exist_ok=True)
    with outp.open('w', encoding='utf-8') as f:
        json.dump(out_list, f, indent=2)

    print('Wrote weekly forecast to', outp)

    # Also write the forecast to MongoDB (replace the collection each run)
    try:
        write_forecast_to_mongo(out_list)
    except Exception as e:
        print('Warning: failed to write weekly forecast to MongoDB:', e)


if __name__ == '__main__':
    main()
