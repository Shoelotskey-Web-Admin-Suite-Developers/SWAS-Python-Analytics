#!/usr/bin/env python3
"""
generate_test_data.py

Generate synthetic test data for transactions, line_items, customers, and payments.

Usage:
    python generate_test_data.py --count 500 --out-dir ./output --seed 42

Requires:
    pip install faker

This script mirrors the project's ID formats and field shapes based on the
server/src models and controllers. It does NOT insert into MongoDB; it only
writes JSON files.
"""
from __future__ import annotations

import argparse
import json
import random
import uuid
from collections import defaultdict
import statistics
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from faker import Faker
from typing import Dict, List, Optional

from date_utils import get_current_date, get_current_datetime

fake = Faker()


def pad(n: int, width: int = 5) -> str:
    return str(n).zfill(width)


def format_datetime_iso(dt: datetime) -> str:
    """Convert datetime to ISO 8601 format with timezone: YYYY-MM-DDTHH:MM:SS.sss+00:00"""
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+00:00"


@dataclass
class Customer:
    cust_id: str
    cust_name: str
    cust_bdate: Optional[str]
    cust_address: Optional[str]
    cust_email: Optional[str]
    cust_contact: Optional[str]
    total_services: int = 0
    total_expenditure: float = 0.0


@dataclass
class LineItemService:
    service_id: str
    quantity: int


@dataclass
class LineItem:
    line_item_id: str
    transaction_id: str
    priority: str
    cust_id: str
    services: List[LineItemService]
    storage_fee: float
    branch_id: str
    shoes: str
    current_location: str
    current_status: str
    due_date: Optional[str]
    latest_update: str
    before_img: Optional[str]
    after_img: Optional[str]
    # New field: pickUpNotice (ISO datetime string) only set when status == "Ready for Pickup" else None
    pickUpNotice: Optional[str] = None


@dataclass
class Transaction:
    transaction_id: str
    line_item_id: List[str]
    branch_id: str
    date_in: str
    received_by: str
    date_out: Optional[str]
    cust_id: str
    no_pairs: int
    no_released: int
    total_amount: float
    discount_amount: float
    amount_paid: float
    payment_status: str
    payments: List[str]
    payment_mode: Optional[str]


@dataclass
class Payment:
    payment_id: str
    transaction_id: str
    payment_amount: float
    payment_mode: str
    payment_date: str


@dataclass
class Appointment:
    appointment_id: str
    cust_id: str
    branch_id: str
    date_for_inquiry: str
    time_start: str
    time_end: str
    status: str


class Generator:
    def __init__(self, count: int = 500, seed: Optional[int] = None, out_dir: str = "./", end_date: Optional[datetime] = None, last_day_boost: bool = True):
        self.count = count
        self.out_dir = out_dir
        if seed is not None:
            random.seed(seed)
            Faker.seed(seed)

        # mimic branches present in the app
        self.branches = [
            {"branch_id": "SMVAL-B-NCR", "branch_code": "SMVAL", "branch_number": 2},
            {"branch_id": "SMBAL-B-NCR", "branch_code": "SMBAL", "branch_number": 3},
            {"branch_id": "SMGRA-B-NCR", "branch_code": "SMGRA", "branch_number": 4},
        ]

        # simple service catalog fallback (service_id -> base_price)
        self.services_catalog = {
            "SERVICE-1": 325.0,
            "SERVICE-2": 450.0,
            "SERVICE-3": 575.0,
            "SERVICE-4": 125.0,
            "SERVICE-5": 125.0,
            "SERVICE-6": 225.0,
            "SERVICE-7": 150.0,
            "SERVICE-8": 275.0,
            "SERVICE-9": 375.0,
        }

        # shoe models list
        self.shoe_models = [
            "Air Jordan 1", "Nike Air Force 1", "Adidas Superstar", "Converse Chuck Taylor All Star", 
            "Vans Old Skool", "Puma Suede Classic", "Reebok Club C 85", "New Balance 550", 
            "Yeezy Boost 350", "Nike Dunk Low", "Adidas Stan Smith", "Saucony Jazz Original", 
            "Asics Gel-Lyte III", "Fila Disruptor II", "Balenciaga Triple S", 
            "Alexander McQueen Oversized Sneaker", "Gucci Ace", "Onitsuka Tiger Mexico 66", 
            "Hoka Clifton 9", "Salomon XT-6", "Nike Blazer Mid", "Adidas Gazelle", 
            "Vans Sk8-Hi", "Nike Cortez", "Reebok Classic Leather", "Puma RS-X", 
            "Adidas NMD R1", "Nike Air Max 1", "New Balance 990", "Yeezy 700 Wave Runner", 
            "Asics Gel-Kayano 14", "Saucony Shadow 6000", "Nike Air Max 97", "Adidas UltraBoost", 
            "Vans Authentic", "Converse One Star", "Nike Air Max 90", "Puma Clyde", 
            "Reebok Question Mid", "New Balance 327", "Jordan 4 Retro", "Nike Air Max Plus (TN)", 
            "Adidas Forum Low", "Nike SB Dunk High", "Vans Slip-On", "Salomon Speedcross 5", 
            "Hoka Bondi 8", "Nike LeBron 20", "Under Armour Curry Flow", "Mizuno Wave Rider 27"
        ]

        # status options list
        self.status_options = [
            "Queued", "Ready for Delivery", "Incoming Branch Delivery", "In Process", 
            "Returning to Branch", "To Pack", "Ready for Pickup", "Picked Up"
        ]

        # in-memory counters to simulate generator behavior in controllers
        self.trx_counters_by_ym_branch: Dict[str, int] = defaultdict(int)
        self.payment_counters_by_branch: Dict[str, int] = defaultdict(int)
        self.customer_counters_by_branch: Dict[int, int] = defaultdict(int)
        self.appointment_counter: int = 0

        # storage for output
        self.customers: Dict[str, Customer] = {}
        self.transactions: List[Transaction] = []
        self.line_items: List[LineItem] = []
        self.payments: List[Payment] = []
        # new datasets
        self.promos: List[dict] = []
        self.unavailability: List[dict] = []
        self.appointments: List[Appointment] = []
        # Date window: last 3 months up to yesterday (inclusive). Default end_date is yesterday.
        # We'll compute start_date as end_date - 90 days to approximate 3 months.
        if end_date is None:
            # Set end_date to yesterday (effective current date minus 1 day)
            current_now = get_current_datetime().replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = current_now - timedelta(days=1)
            # Set time to end of day for yesterday
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        self.end_date: datetime = end_date

        # Start date is 90 days before end_date, at beginning of that day
        self.start_date: datetime = (self.end_date - timedelta(days=90)).replace(hour=0, minute=0, second=0, microsecond=0)

        # Whether to artificially guarantee a minimum number of transactions on the final day.
        # NOTE: Enabling this (original behavior) creates a visually large spike on the last day in
        # daily revenue analytics, because average per-day count is ~count/num_days but last day is forced.
        self.last_day_boost = last_day_boost

    # mirror generateTransactionId from controller
    def generate_transaction_id(self, branch_code: str, now: datetime) -> str:
        yearMonth = f"{now.year}-{str(now.month).zfill(2)}"
        key = f"{yearMonth}-{branch_code}"
        self.trx_counters_by_ym_branch[key] += 1
        return f"{yearMonth}-{pad(self.trx_counters_by_ym_branch[key])}-{branch_code}"

    # mirror generateLineItemId
    def generate_line_item_id(self, transaction_id: str, line_index: int) -> str:
        parts = transaction_id.split("-")
        year = parts[0]
        month = parts[1]
        trxIncrement = parts[2]
        branchCode = "-".join(parts[3:])
        return f"{year}-{month}-{trxIncrement}-{str(line_index+1).zfill(3)}-{branchCode}"

    # mirror generatePaymentId style: PAY-<increment>-<branch_code>
    def generate_payment_id(self, branch_code: str) -> str:
        self.payment_counters_by_branch[branch_code] += 1
        return f"PAY-{self.payment_counters_by_branch[branch_code]}-{branch_code}"

    def generate_customer_id(self, branch_number: int) -> str:
        self.customer_counters_by_branch[branch_number] += 1
        return f"CUST-{branch_number}-{self.customer_counters_by_branch[branch_number]}"

    def pick_branch(self) -> dict:
        return random.choice(self.branches)

    # promo id: PROMO-<3 digit>
    def generate_promo_id(self, idx: int) -> str:
        return f"PROMO-{str(idx).zfill(3)}"

    # unavailability id: UNAV-<3 digit>
    def generate_unavailability_id(self, idx: int) -> str:
        return f"UNAV-{str(idx).zfill(3)}"

    # appointment id: APPT-<5 digit>
    def generate_appointment_id(self) -> str:
        self.appointment_counter += 1
        return f"APPT-{str(self.appointment_counter).zfill(5)}"

    def maybe_reuse_customer(self, branch_number: int) -> Customer:
        # 50% chance to reuse an existing customer (reduced from 70%)
        if self.customers and random.random() < 0.5:
            return random.choice(list(self.customers.values()))
        # otherwise create new
        cid = self.generate_customer_id(branch_number)
        name = fake.name()
        # Generate birthdate in ISO format with timezone (YYYY-MM-DDTHH:MM:SS.sss+00:00)
        # Use default time values (00:00:00.000) - only date varies
        birth_date = fake.date_of_birth(minimum_age=18, maximum_age=80)
        birth_datetime = datetime.combine(birth_date, datetime.min.time())
        cust_bdate = birth_datetime.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+00:00"
        
        cust = Customer(
            cust_id=cid,
            cust_name=name,
            cust_bdate=cust_bdate,
            cust_address=fake.address(),
            cust_email=fake.unique.email(),
            cust_contact=fake.phone_number(),
        )
        self.customers[cid] = cust
        return cust

    def generate_one(self, now: datetime) -> None:
        branch = self.pick_branch()
        branch_code = branch["branch_code"]
        branch_id = branch["branch_id"]
        branch_number = branch["branch_number"]

        # check unavailability for this branch on this date
        date_str = str(now.date())
        # find unavailability entries matching branch and date (extract date from ISO format)
        u_list = []
        for u in self.unavailability:
            if u["branch_id"] == branch_id:
                # Extract date part from ISO datetime string for comparison
                unavail_date = u["date_unavailable"].split('T')[0]
                unavail_date_obj = datetime.strptime(unavail_date, "%Y-%m-%d").date()
                if str(unavail_date_obj) == date_str:
                    u_list.append(u)
        if u_list:
            # if any full day unavailability -> skip creating transactions
            if any(u.get("type") == "Full Day" for u in u_list):
                return
            # partial day -> reduce chance of transaction for this timestamp
            # we'll skip about 40-70% depending on partial duration
            if any(u.get("type") == "Partial Day" for u in u_list):
                if random.random() < 0.6:
                    return

        # customer (reuse or new)
        customer = self.maybe_reuse_customer(branch_number)

        # transaction id
        trx_id = self.generate_transaction_id(branch_code, now)

        # number of line items 1..3
        # promos on this branch/date increase likelihood of more line items and higher amounts
        # Convert promo dates from ISO format to date strings for comparison
        promo_list = []
        for p in self.promos:
            if p["branch_id"] == branch_id:
                # Extract date parts from ISO datetime strings for comparison
                promo_dates = [pd.split('T')[0] for pd in p["promo_dates"]]
                if date_str in promo_dates:
                    promo_list.append(p)
        promo_boost = 1.0
        if promo_list:
            # each promo increases transaction size and frequency modestly
            promo_boost = 1.3 + 0.2 * (len(promo_list) - 1)

        num_line_items = random.randint(1, 3)
        if random.random() < 0.25 * promo_boost:
            num_line_items += 1
        created_line_ids: List[str] = []
        no_pairs = 0
        total_amount = 0.0

        for li_idx in range(num_line_items):
            line_id = self.generate_line_item_id(trx_id, li_idx)
            created_line_ids.append(line_id)

            # services: pick 1 service per line item, quantity 1..5
            svc_id = random.choice(list(self.services_catalog.keys()))
            qty = random.randint(1, 5)
            # promo increases quantity occasionally
            if promo_list and random.random() < 0.3:
                qty = min(8, int(qty * promo_boost))
            unit_price = self.services_catalog[svc_id]
            total_price = round(unit_price * qty, 2)

            # pick a status from the list
            status = random.choice(self.status_options)

            # deterministic location mapping
            branch_statuses = {"Queued", "Ready for Delivery", "To Pack", "Ready for Pickup", "Picked Up"}
            hub_statuses = {"Incoming Branch Delivery", "In Process", "Returning to Branch"}
            if status in hub_statuses:
                current_location = "Hub"
            elif status in branch_statuses:
                current_location = "Branch"
            else:
                # fallback (shouldn't occur with current lists)
                current_location = "Branch"
            
            # calculate due_date as 10-25 days ahead from date_in
            date_in_dt = now - timedelta(days=random.randint(0, 30))
            due_date_offset = random.randint(10, 25)
            due_date_dt = date_in_dt + timedelta(days=due_date_offset)
            # Set due date to a random time during business hours (9 AM - 5 PM)
            due_date_dt = due_date_dt.replace(
                hour=random.randint(9, 17),
                minute=random.randint(0, 59),
                second=random.randint(0, 59),
                microsecond=random.randint(0, 999) * 1000
            )
            due_date = format_datetime_iso(due_date_dt)

            # Make latest_update relatively close to current date
            # Items created today should go back max 2 days, older items can be more spread out
            current_time = get_current_datetime()
            if now.date() >= (current_time - timedelta(days=1)).date():
                # For recent transactions (today/yesterday), latest_update within last 2 days
                days_back = random.uniform(0, 2)
            else:
                # For older transactions, latest_update can be between transaction date and up to 7 days ago
                max_days_back = min(7, (current_time - now).days)
                days_back = random.uniform(0, max_days_back)
            
            latest_update_dt = current_time - timedelta(days=days_back)
            # Add some random hours/minutes to make it more realistic
            latest_update_dt = latest_update_dt.replace(
                hour=random.randint(8, 18),  # Business hours
                minute=random.randint(0, 59),
                second=random.randint(0, 59),
                microsecond=random.randint(0, 999) * 1000
            )

            line = LineItem(
                line_item_id=line_id,
                transaction_id=trx_id,
                priority=random.choice(["Normal", "Rush"]),
                cust_id=customer.cust_id,
                services=[LineItemService(service_id=svc_id, quantity=qty)],
                storage_fee=0.0,
                branch_id=branch_id,
                shoes=random.choice(self.shoe_models),
                current_location=current_location,
                current_status=status,
                due_date=due_date,
                latest_update=format_datetime_iso(latest_update_dt),
                before_img=None,
                after_img=None,
                # Assumption: "today until 20 days past" interpreted as a random timestamp
                # between now and 20 days ago. If you intended 20 days in the future,
                # adjust the timedelta range accordingly.
                # pickUpNotice: random timestamp (ISO 8601 like other fields) between now and 20 days in the past
                pickUpNotice=(
                    format_datetime_iso(
                        get_current_datetime() - timedelta(
                            days=random.uniform(0, 20),
                        )
                    ) if status == "Ready for Pickup" else None
                ),
            )

            self.line_items.append(line)
            no_pairs += 1  # Count the number of shoes/line items, not service quantities
            total_amount += total_price

        # apply promo multiplier to total_amount
        total_amount = round(total_amount * promo_boost, 2)

        # decide status
        status = random.choices(["PAID", "PARTIAL", "NP"], weights=[0.6, 0.2, 0.2])[0]
        # map to Transaction.payment_status enum and our textual status
        payment_status = status

        amount_paid = total_amount if payment_status == "PAID" else (round(total_amount * random.uniform(0.2, 0.8), 2) if payment_status == "PARTIAL" else 0.0)

        # pick payment mode
        payment_mode = random.choice(["Cash", "GCash", "Bank", "Other"]) if amount_paid > 0 else None

        payments_list: List[str] = []
        if amount_paid > 0:
            payment_id = self.generate_payment_id(branch_code)
            payments_list.append(payment_id)
            payment = Payment(
                payment_id=payment_id,
                transaction_id=trx_id,
                payment_amount=amount_paid,
                payment_mode=payment_mode or "Cash",
                payment_date=format_datetime_iso(now),
            )
            self.payments.append(payment)

        # For transactions on the last few days, use minimal date_in offset to ensure recent data
        if now.date() >= (self.end_date - timedelta(days=2)).date():
            # For transactions in the last 2 days, use 0-2 days back for date_in
            days_back = random.randint(0, 2)
        else:
            # For older transactions, use normal range
            days_back = random.randint(0, min(30, (now.date() - self.start_date.date()).days))
        date_in_dt = now - timedelta(days=days_back)
        date_in = format_datetime_iso(date_in_dt)
        date_out = format_datetime_iso(now) if payment_status == "PAID" else None

        trx = Transaction(
            transaction_id=trx_id,
            line_item_id=created_line_ids,
            branch_id=branch_id,
            date_in=date_in,
            received_by=fake.name(),
            date_out=date_out,
            cust_id=customer.cust_id,
            no_pairs=no_pairs,
            no_released=0,
            total_amount=total_amount,
            discount_amount=0.0,
            amount_paid=amount_paid,
            payment_status=payment_status,
            payments=payments_list,
            payment_mode=payment_mode,
        )

        # update customer totals
        customer.total_services += no_pairs
        customer.total_expenditure = round(customer.total_expenditure + total_amount, 2)

        self.transactions.append(trx)

    def generate(self):
        """Generate synthetic records across the date window.

        Previous behavior (now optional via last_day_boost flag) forced a relatively large
        minimum number of transactions on the final day (yesterday). That made the last
        day a pronounced outlier in the daily revenue chart because:
          * Average expected per-day count ~ count / num_days (≈1–20 typically), but
          * Final day was forced to at least max(15, count//50), often >> average.
          * Daily revenue sums only PAID transactions (date_out != None), so clustering
            more transactions (60% PAID) on the last day inflates its revenue.
        Disabling the boost yields a more naturally noisy but not systematically spiking last day.
        """
        total_seconds = int((self.end_date - self.start_date).total_seconds())
        self._generate_promos_and_unavailability()
        self._generate_appointments()

        last_day_start = self.end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        last_day_seconds_total = int((self.end_date - last_day_start).total_seconds())

        if self.last_day_boost:
            # Original (spiky) behavior preserved when flag True
            last_day_transactions = max(15, self.count // 50)
            for i in range(self.count):
                if i < last_day_transactions:
                    rand_s = random.randint(0, last_day_seconds_total)
                    dt = last_day_start + timedelta(seconds=rand_s)
                else:
                    rand_s = random.randint(0, total_seconds - 1)
                    dt = self.start_date + timedelta(seconds=rand_s)
                self.generate_one(dt)
        else:
            # Uniform distribution across full window with bounded variability per day
            day_count = (self.end_date.date() - self.start_date.date()).days + 1
            base_per_day = self.count / day_count if day_count > 0 else self.count
            max_per_day = max(1, int(round(base_per_day * 1.5)))

            raw_targets = []
            for _ in range(day_count):
                noise = random.uniform(0.7, 1.3)
                raw_targets.append(max(0.1, base_per_day * noise))

            weight_sum = sum(raw_targets) or 1.0
            per_day_counts = [int(round((w / weight_sum) * self.count)) for w in raw_targets]

            # Adjust rounding differences while respecting per-day cap
            diff = self.count - sum(per_day_counts)
            indices = list(range(day_count))
            random.shuffle(indices)
            while diff != 0 and indices:
                idx = indices.pop()
                if diff > 0:
                    if per_day_counts[idx] < max_per_day:
                        per_day_counts[idx] += 1
                        diff -= 1
                else:  # diff < 0
                    if per_day_counts[idx] > 0:
                        per_day_counts[idx] -= 1
                        diff += 1
                if not indices and diff != 0:
                    indices = list(range(day_count))
                    random.shuffle(indices)

            # Ensure no single day exceeds the cap; redistribute excess
            redistribution_pool = 0
            for idx in range(day_count):
                if per_day_counts[idx] > max_per_day:
                    redistribution_pool += per_day_counts[idx] - max_per_day
                    per_day_counts[idx] = max_per_day

            idx_cycle = list(range(day_count))
            random.shuffle(idx_cycle)
            while redistribution_pool > 0 and idx_cycle:
                idx = idx_cycle.pop()
                if per_day_counts[idx] < max_per_day:
                    per_day_counts[idx] += 1
                    redistribution_pool -= 1
                if not idx_cycle and redistribution_pool > 0:
                    idx_cycle = [i for i in range(day_count) if per_day_counts[i] < max_per_day]
                    random.shuffle(idx_cycle)

            for offset, n in enumerate(per_day_counts):
                if n <= 0:
                    continue
                date_obj = self.start_date.date() + timedelta(days=offset)
                day_start_dt = datetime.combine(date_obj, datetime.min.time())
                day_end_dt = day_start_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
                if day_end_dt > self.end_date:
                    day_end_dt = self.end_date
                span_seconds = int((day_end_dt - day_start_dt).total_seconds()) or 1
                for _ in range(n):
                    rand_s = random.randint(0, span_seconds)
                    dt = day_start_dt + timedelta(seconds=rand_s)
                    self.generate_one(dt)

            # If last day still ends up extreme due to random noise, optionally thin paid transactions
            # (post-processing) to keep it within 2x median of previous 7 days.
            last_day_str = last_day_start.date().isoformat()
            last_day_trx = [t for t in self.transactions if (t.date_out and t.date_out.startswith(last_day_str))]
            # compute med of previous 7 days paid totals
            prev_dates = [(last_day_start.date() - timedelta(days=i)).isoformat() for i in range(1, 8)]
            paid_by_date = defaultdict(float)
            for t in self.transactions:
                if t.date_out:
                    d = t.date_out.split('T')[0]
                    paid_by_date[d] += t.amount_paid
            prev_values = [paid_by_date[d] for d in prev_dates if d in paid_by_date]
            med = None
            if prev_values:
                nonzero_prev = [v for v in prev_values if v > 0]
                if nonzero_prev:
                    med = statistics.median(nonzero_prev)
                else:
                    med = statistics.median(prev_values)
            if (med is None or med == 0) and paid_by_date:
                historical = [v for date_key, v in paid_by_date.items() if date_key != last_day_str and v > 0]
                if historical:
                    med = statistics.median(historical)
                else:
                    historical_all = [v for date_key, v in paid_by_date.items() if date_key != last_day_str]
                    if historical_all:
                        med = sum(historical_all) / len(historical_all)
            if med and last_day_trx:
                last_day_total = sum(t.amount_paid for t in last_day_trx)
                cap = med * 2.0 if med > 0 else None
                if cap and last_day_total > cap:
                    # randomly drop paid status from some transactions to cap revenue
                    excess = last_day_total - cap
                    # sort largest first
                    last_day_trx_sorted = sorted(last_day_trx, key=lambda t: t.amount_paid, reverse=True)
                    for t in last_day_trx_sorted:
                        if excess <= 0:
                            break
                        # convert to PARTIAL with 40% of original to preserve some value
                        new_paid = round(t.amount_paid * 0.4, 2)
                        reduction = t.amount_paid - new_paid
                        t.amount_paid = new_paid
                        t.payment_status = "PARTIAL" if new_paid > 0 else "NP"
                        if new_paid == 0:
                            t.date_out = None  # not counted as revenue anymore
                        excess -= reduction

    def _generate_promos_and_unavailability(self):
        # Create a few promos per branch (more frequent than unavailability)
        date_cursor = self.start_date
        all_dates = [(self.start_date + timedelta(days=i)) for i in range((self.end_date - self.start_date).days + 1)]

        promo_idx = 1
        unav_idx = 1

        # frequency: promos roughly every ~10-20 days per branch
        for branch in self.branches:
            # generate 3-6 promo windows per branch in the date range
            num_promos = random.randint(3, 6)
            for _ in range(num_promos):
                # pick start day and length (1-7 days)
                start = random.choice(all_dates)
                length = random.randint(1, 7)
                dates = [start + timedelta(days=d) for d in range(length) if start + timedelta(days=d) <= self.end_date]
                if not dates:
                    continue
                # Convert dates to ISO format with random times
                promo_dates_iso = []
                for d in dates:
                    dt_with_time = d.replace(
                        hour=random.randint(0, 23),
                        minute=random.randint(0, 59),
                        second=random.randint(0, 59),
                        microsecond=random.randint(0, 999) * 1000
                    )
                    promo_dates_iso.append(format_datetime_iso(dt_with_time))
                promo = {
                    "promo_id": self.generate_promo_id(promo_idx),
                    "promo_title": f"{branch['branch_code']} Promo {promo_idx}",
                    "promo_description": random.choice(["Rainy season promo", "Weekend special", "Back-to-school"]),
                    "promo_dates": promo_dates_iso,
                    "promo_duration": f"{dates[0].date()} - {dates[-1].date()}",
                    "branch_id": branch["branch_id"],
                }
                self.promos.append(promo)
                promo_idx += 1

            # generate unavailability events at a monthly rate: 0-2 per month per branch
            # build list of months in the date range
            import calendar

            month_cursor = self.start_date.replace(day=1)
            months = []
            while month_cursor <= self.end_date:
                months.append((month_cursor.year, month_cursor.month))
                # advance month
                if month_cursor.month == 12:
                    month_cursor = month_cursor.replace(year=month_cursor.year + 1, month=1)
                else:
                    month_cursor = month_cursor.replace(month=month_cursor.month + 1)

            for (y, m) in months:
                # pick 0-2 unavailability events for this branch in this month
                num_unav_month = random.choices([0, 1, 2], weights=[0.6, 0.3, 0.1])[0]
                if num_unav_month == 0:
                    continue

                # determine bounds for days in this month clipped to start_date/end_date
                first_day = max(self.start_date.date(), datetime(y, m, 1).date())
                last_day_of_month = calendar.monthrange(y, m)[1]
                last_day = min(self.end_date.date(), datetime(y, m, last_day_of_month).date())
                if first_day > last_day:
                    continue

                for _ in range(num_unav_month):
                    day = first_day + timedelta(days=random.randint(0, (last_day - first_day).days))
                    # Convert to datetime with random time for ISO format
                    day_datetime = datetime.combine(day, datetime.min.time().replace(
                        hour=random.randint(0, 23),
                        minute=random.randint(0, 59),
                        second=random.randint(0, 59),
                        microsecond=random.randint(0, 999) * 1000
                    ))
                    typ = random.choices(["Full Day", "Partial Day"], weights=[0.3, 0.7])[0]
                    if typ == "Full Day":
                        ua = {
                            "unavailability_id": self.generate_unavailability_id(unav_idx),
                            "branch_id": branch["branch_id"],
                            "date_unavailable": format_datetime_iso(day_datetime),
                            "type": typ,
                            "time_start": None,
                            "time_end": None,
                            "note": random.choice(["Holiday", "Maintenance", "Inventory"]),
                        }
                    else:
                        start_hour = random.randint(8, 14)
                        dur = random.randint(2, 6)
                        end_hour = min(18, start_hour + dur)
                        ua = {
                            "unavailability_id": self.generate_unavailability_id(unav_idx),
                            "branch_id": branch["branch_id"],
                            "date_unavailable": format_datetime_iso(day_datetime),
                            "type": typ,
                            "time_start": f"{str(start_hour).zfill(2)}:00",
                            "time_end": f"{str(end_hour).zfill(2)}:00",
                            "note": random.choice(["Partial maintenance", "Team meeting", "Short holiday"]),
                        }
                    self.unavailability.append(ua)
                    unav_idx += 1

    def _generate_appointments(self):
        """Generate 0-6 appointments per day, with proper time slots and status based on date"""
        # Get all dates in our range - extend to include future appointments
        current_date = self.start_date.date()
        today = get_current_date()
        # Extend end_date to include 20 days in the future for pending appointments
        future_end_date = today + timedelta(days=20)
        end_date = max(self.end_date.date(), future_end_date)
        
        # Time slots: 30-minute increments from 9:00 to 17:30
        time_slots = []
        for hour in range(9, 18):
            for minute in [0, 30]:
                start_time = f"{hour:02d}:{minute:02d}"
                if minute == 0:
                    end_time = f"{hour:02d}:30"
                else:
                    end_time = f"{hour+1:02d}:00" if hour < 17 else "18:00"
                time_slots.append((start_time, end_time))
        
        # Service types are not needed in the simplified appointment schema
        
        while current_date <= end_date:
            for branch in self.branches:
                branch_id = branch["branch_id"]
                date_str = str(current_date)
                
                # Check if this branch has unavailability on this date
                unavailable = False
                for u in self.unavailability:
                    if u["branch_id"] == branch_id and u["type"] == "Full Day":
                        # Extract date part from ISO datetime string
                        unavail_date = u["date_unavailable"].split('T')[0]
                        if unavail_date == date_str:
                            unavailable = True
                            break
                
                if unavailable:
                    # Skip appointments for unavailable days
                    continue
                
                # Generate appointments based on date
                if current_date > today:
                    # Future appointments (next 20 days) - higher chance of appointments
                    if random.random() < 0.3:
                        num_appointments = 0
                    else:
                        num_appointments = random.randint(1, 4)  # Slightly fewer than historical
                else:
                    # Historical appointments - original logic
                    if random.random() < 0.5:
                        num_appointments = 0
                    else:
                        num_appointments = random.randint(1, 6)
                
                # Get partial unavailability times for this branch/date
                partial_unavail = []
                for u in self.unavailability:
                    if u["branch_id"] == branch_id and u["type"] == "Partial Day":
                        # Extract date part from ISO datetime string
                        unavail_date = u["date_unavailable"].split('T')[0]
                        if unavail_date == date_str:
                            partial_unavail.append(u)
                
                # Filter available time slots
                available_slots = time_slots.copy()
                for u in partial_unavail:
                    if u.get("time_start") and u.get("time_end"):
                        # Remove slots that overlap with unavailable times
                        unavail_start = u["time_start"]
                        unavail_end = u["time_end"]
                        available_slots = [
                            slot for slot in available_slots
                            if not (slot[0] >= unavail_start and slot[1] <= unavail_end)
                        ]
                
                if not available_slots:
                    continue
                
                # Select random time slots for appointments
                selected_slots = random.sample(
                    available_slots, 
                    min(num_appointments, len(available_slots))
                )
                
                for time_start, time_end in selected_slots:
                    # Determine status based on date
                    if current_date < today:
                        # Past appointments are "Approved"
                        status = "Approved"
                    else:
                        # Future appointments are "Pending"
                        status = "Pending"
                    
                    # Get a different customer for each appointment
                    # 70% chance to use existing customer, 30% chance to create new one
                    if self.customers and random.random() < 0.7:
                        customer = random.choice(list(self.customers.values()))
                    else:
                        # Create a new customer
                        customer = self.maybe_reuse_customer(branch["branch_number"])
                    
                    # Create datetime object for the appointment date with random time
                    appointment_datetime = datetime.combine(current_date, datetime.min.time().replace(
                        hour=random.randint(0, 23),
                        minute=random.randint(0, 59),
                        second=random.randint(0, 59),
                        microsecond=random.randint(0, 999) * 1000
                    ))
                    
                    appointment = Appointment(
                        appointment_id=self.generate_appointment_id(),
                        cust_id=customer.cust_id,
                        branch_id=branch_id,
                        date_for_inquiry=format_datetime_iso(appointment_datetime),
                        time_start=time_start,
                        time_end=time_end,
                        status=status
                    )
                    
                    self.appointments.append(appointment)
            
            current_date += timedelta(days=1)

    def dump(self):
        out = self.out_dir.rstrip("/\\")
        # ensure path exists
        import os

        os.makedirs(out, exist_ok=True)

        tx_path = os.path.join(out, "transactions.json")
        li_path = os.path.join(out, "line_items.json")
        cu_path = os.path.join(out, "customers.json")
        pay_path = os.path.join(out, "payments.json")
        promos_path = os.path.join(out, "promos.json")
        unav_path = os.path.join(out, "unavailability.json")
        appt_path = os.path.join(out, "appointments.json")

        with open(tx_path, "w", encoding="utf-8") as f:
            json.dump([asdict(t) for t in self.transactions], f, indent=2, ensure_ascii=False)

        with open(li_path, "w", encoding="utf-8") as f:
            json.dump([asdict(li) for li in self.line_items], f, indent=2, ensure_ascii=False)

        with open(cu_path, "w", encoding="utf-8") as f:
            json.dump([asdict(c) for c in self.customers.values()], f, indent=2, ensure_ascii=False)

        with open(pay_path, "w", encoding="utf-8") as f:
            json.dump([asdict(p) for p in self.payments], f, indent=2, ensure_ascii=False)

        # dump promos and unavailability as JSON with model-like shapes
        with open(promos_path, "w", encoding="utf-8") as f:
            json.dump(self.promos, f, indent=2, ensure_ascii=False)

        with open(unav_path, "w", encoding="utf-8") as f:
            json.dump(self.unavailability, f, indent=2, ensure_ascii=False)

        with open(appt_path, "w", encoding="utf-8") as f:
            json.dump([asdict(a) for a in self.appointments], f, indent=2, ensure_ascii=False)

        return tx_path, li_path, cu_path, pay_path, appt_path


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--count", type=int, default=500)
    p.add_argument("--out-dir", type=str, default="./output")
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--end-date", type=str, default=None, help="End date (YYYY-MM-DD) for generated transactions; defaults to yesterday; start is 3 months before this date")
    p.add_argument("--no-last-day-boost", action="store_true", help="Disable artificial concentration of transactions on the final day (removes end-of-series revenue spike)")
    return p.parse_args()


def main():
    args = parse_args()
    # parse end date
    try:
        if args.end_date:
            end_date = datetime.strptime(args.end_date, "%Y-%m-%d")
        else:
            # Default to yesterday
            end_date = None
    except Exception:
        print(f"Invalid end-date format: {args.end_date}. Use YYYY-MM-DD")
        return

    gen = Generator(count=args.count, seed=args.seed, out_dir=args.out_dir, end_date=end_date, last_day_boost=not args.no_last_day_boost)
    print(f"Generating {args.count} transactions...")
    gen.generate()
    tx_path, li_path, cu_path, pay_path, appt_path = gen.dump()
    print("Done. Files written:")
    print(tx_path)
    print(li_path)
    print(cu_path)
    print(pay_path)
    print(appt_path)


if __name__ == "__main__":
    main()
