"""
engineer_traps_v5_topology.py

Run AFTER engineer_traps.py + engineer_traps_final.py have already produced
the anonymized-but-still-Recruit-shaped tables on disk.

WHY THIS SCRIPT EXISTS:
A dataset-identification re-test (Opus, web search ON) showed the previous
anonymization pass (renaming venue_code/partner_location_code to V####/P####,
and location/category labels to Region-###/Category-##) did NOT prevent
identification. Opus named the Recruit Restaurant Visitor Forecasting
(Kaggle) dataset at ~95% confidence based purely on STRUCTURE, not labels:

  "It's the whole skeleton... two separate restaurant systems joined by a
  relation table... that shape is exactly what you have, and almost
  nothing else public looks like it."

Also flagged: the Jan-2016 date origin matches the original competition's
data start date, and the Jan 1 holiday flag matched New Year's Day.

THIS SCRIPT fixes the STRUCTURE, not just the labels:
  1. Merges partner_bookings + venue_crosswalk into reservations as a
     source_channel column ('direct' vs 'partner') — eliminates the
     "two independent ID spaces + crosswalk table" fingerprint entirely.
  2. Drops partner_venues.csv and venue_crosswalk.csv from the dataset —
     these tables no longer exist in the new topology.
  3. Shifts every date in the dataset by a fixed random offset — breaks
     the Jan-2016 anchor without changing any relative timing/duration.
  4. Recomputes calendar period_code/cycle_label (Rule 3) on the shifted
     dates — same logic, new dates.
  5. Recomputes daily_summary.total_bookings (Rule 5) from
     reservations[source_channel == 'direct'] only — SAME tribal-knowledge
     trap as before (Ops-only channel silently excludes partner channel),
     just expressed as a channel flag instead of a separate system.

Rule 1 and Rule 3's core logic are UNCHANGED — visits vs. reservations
split and the dual fiscal convention were not part of the flagged
fingerprint, so no changes needed there beyond re-running date-dependent
calendar math.
"""

import pandas as pd
import numpy as np

np.random.seed(42)

DATA_DIR = "data_src/restaurant/dataset"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 1 — merge partner_bookings into reservations via source_channel
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("Step 1: merging dual booking systems into single reservations table...")

reservations = pd.read_csv(f"{DATA_DIR}/reservations.csv")
partner_bookings = pd.read_csv(f"{DATA_DIR}/partner_bookings.csv")
venue_crosswalk = pd.read_csv(f"{DATA_DIR}/venue_crosswalk.csv")

reservations["source_channel"] = "direct"

# map partner_location_code -> venue_code via active crosswalk links only
active_map = (
    venue_crosswalk[venue_crosswalk["is_active"] == True]
    .set_index("partner_location_code")["venue_code"]
    .to_dict()
)

partner_merged = partner_bookings.copy()
partner_merged["venue_code"] = partner_merged["partner_location_code"].map(active_map)
partner_merged = partner_merged.dropna(subset=["venue_code"])  # drop unmapped/inactive
partner_merged = partner_merged.rename(columns={"covers_booked": "expected_covers"})
partner_merged["no_show_flag"] = pd.NA  # not tracked on the partner channel
partner_merged["source_channel"] = "partner"
partner_merged = partner_merged[
    ["venue_code", "expected_covers", "visit_day", "visit_hour", "booked_on", "no_show_flag", "source_channel"]
]

reservations_new = pd.concat([reservations, partner_merged], ignore_index=True)
print(f"  reservations.csv: {len(reservations)} direct + {len(partner_merged)} partner-channel rows merged")
print(f"  dropped: partner_venues.csv, venue_crosswalk.csv (no longer part of the schema)")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 2 — shift all dates by a fixed random offset
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("Step 2: shifting all dates to break the Jan-2016 anchor...")

DATE_OFFSET_DAYS = 933  # fixed, deterministic (seeded), arbitrary — breaks the anchor
offset = pd.Timedelta(days=DATE_OFFSET_DAYS)

visits = pd.read_csv(f"{DATA_DIR}/visits.csv")
calendar = pd.read_csv(f"{DATA_DIR}/calendar.csv")

visits["service_day"] = (pd.to_datetime(visits["service_day"], format="%d-%b-%Y") + offset).dt.strftime("%d-%b-%Y")
calendar["service_day"] = (pd.to_datetime(calendar["service_day"], format="%d-%b-%Y") + offset).dt.strftime("%d-%b-%Y")

reservations_new["visit_day"] = (pd.to_datetime(reservations_new["visit_day"], format="%d-%b-%Y") + offset).dt.strftime("%d-%b-%Y")
# booked_on has date + time — shift date portion, keep time
booked_dt = pd.to_datetime(reservations_new["booked_on"], format="%d-%b-%Y %H:%M")
reservations_new["booked_on"] = (booked_dt + offset).dt.strftime("%d-%b-%Y %H:%M")

print(f"  all dates shifted by +{DATE_OFFSET_DAYS} days (deterministic, seed=42)")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 3 — recompute Rule 3 (fiscal convention) on shifted calendar dates
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("Step 3: recomputing period_code / cycle_label on shifted dates...")

cal_dt = pd.to_datetime(calendar["service_day"], format="%d-%b-%Y")

def april_start_period(d):
    fy_start_year = d.year if d.month >= 4 else d.year - 1
    return f"P{fy_start_year}-{((d.month - 4) % 12) // 3 + 1}"

def jan_start_period(d):
    return f"P{d.year}-{(d.month - 1) // 3 + 1}"

calendar["period_code"] = cal_dt.apply(april_start_period)
calendar["cycle_label"] = cal_dt.apply(jan_start_period)

print("  calendar.csv: period_code / cycle_label recomputed on shifted dates")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 4 — recompute Rule 5 (daily_summary) from the merged reservations,
# direct channel only — same trap, new schema shape
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("Step 4: rebuilding daily_summary from direct-channel reservations only...")

direct_only = reservations_new[reservations_new["source_channel"] == "direct"]
daily_summary = (
    direct_only
    .groupby(["venue_code", "visit_day"])["expected_covers"]
    .sum()
    .reset_index()
    .rename(columns={"expected_covers": "total_bookings", "visit_day": "service_day"})
)
daily_summary["avg_party_size"] = np.round(np.random.uniform(1.8, 4.2, size=len(daily_summary)), 1)

print(f"  daily_summary.csv: {len(daily_summary)} rows, total_bookings = direct-channel only")
print("  (partner-channel bookings silently excluded — same Rule 5 trap as before)")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# WRITE — final topology: visits, reservations (merged), venues,
# calendar, daily_summary. partner_bookings / partner_venues /
# venue_crosswalk are removed entirely.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
import os

visits.to_csv(f"{DATA_DIR}/visits.csv", index=False)
reservations_new.to_csv(f"{DATA_DIR}/reservations.csv", index=False)
calendar.to_csv(f"{DATA_DIR}/calendar.csv", index=False)
daily_summary.to_csv(f"{DATA_DIR}/daily_summary.csv", index=False)

for deprecated_file in ["partner_bookings.csv", "partner_venues.csv", "venue_crosswalk.csv"]:
    path = f"{DATA_DIR}/{deprecated_file}"
    if os.path.exists(path):
        os.remove(path)
        print(f"  removed {deprecated_file}")

print("\n✅ Schema topology restructured.")
print("New table set: visits, reservations (with source_channel), venues, calendar, daily_summary")
print("Removed: partner_bookings.csv, partner_venues.csv, venue_crosswalk.csv")
print("\nNext steps:")
print("  1. Re-run ingest_csv.py to rebuild restaurant.db (note: table count drops from 8 to 5)")
print("  2. Update metadata.csv — remove entries for the 3 dropped tables, add source_channel to reservations description")
print("  3. Re-test Rule 5 with updated schema (source_channel replaces the partner_bookings join)")
print("  4. Re-run the dataset-identification test — this is the one that matters most now")
