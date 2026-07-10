"""
engineer_traps_final.py

Consolidated, single-source-of-truth trap engineering script.
Run this AFTER engineer_traps.py (which builds the base 7 engineered tables).

This replaces engineer_traps_rules.py (v1), engineer_traps_rules_v2.py (v2),
and engineer_traps_rules_v3.py — those are now redundant / deleted, and their
logic (Rule 3's calendar conversion + Rule 5's daily_summary fix) is
consolidated here so there's one script that reproduces the final validated
dataset state from scratch.

Validated trap status going into this script (from 3 rounds of Opus
zero-shot testing, web on/off):
  Rule 1 (visitors)  — PASS, no data change needed (structural: guest_count
                        only in visits, expected_covers only in reservations)
  Rule 3 (fiscal)    — PASS, requires period_code + cycle_label in calendar
                        (this script) + comment-locked prompt at test time
  Rule 5 (bookings)  — PASS, requires daily_summary with ONLY total_bookings
                        + avg_party_size, no metadata/provenance column
                        (this script) + comment-locked prompt at test time

IMPORTANT: path below assumes the FLAT dataset/ structure (no engineered/
subfolder) — data_src/restaurant/dataset/*.csv directly.
"""

import pandas as pd
import numpy as np

np.random.seed(42)

DATA_DIR = "data_src/restaurant/dataset"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RULE 3 — dual fiscal convention
#
# Finance  -> fiscal year starts April 1  (Japan standard)
# Ops      -> fiscal year starts Jan 1    (calendar year)
#
# Replace the raw fiscal_period column (from engineer_traps.py) with two
# neutrally-named period columns, neither of which reveals which
# convention it uses.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("Engineering Rule 3 (dual fiscal convention) into calendar...")

calendar = pd.read_csv(f"{DATA_DIR}/calendar.csv")
calendar["service_day"] = pd.to_datetime(calendar["service_day"], format="%d-%b-%Y", errors="coerce")
if calendar["service_day"].isna().any():
    calendar["service_day"] = pd.to_datetime(
        pd.read_csv(f"{DATA_DIR}/calendar.csv")["service_day"]
    )

def april_start_period(d):
    fy_start_year = d.year if d.month >= 4 else d.year - 1
    return f"P{fy_start_year}-{((d.month - 4) % 12) // 3 + 1}"

def jan_start_period(d):
    return f"P{d.year}-{(d.month - 1) // 3 + 1}"

if "fiscal_period" in calendar.columns:
    calendar = calendar.drop(columns=["fiscal_period"])
if "period_code" in calendar.columns:
    calendar = calendar.drop(columns=["period_code"])
if "cycle_label" in calendar.columns:
    calendar = calendar.drop(columns=["cycle_label"])

calendar["period_code"] = calendar["service_day"].apply(april_start_period)   # Finance (hidden)
calendar["cycle_label"] = calendar["service_day"].apply(jan_start_period)     # Ops (hidden)
calendar["service_day"] = calendar["service_day"].dt.strftime("%d-%b-%Y")

calendar.to_csv(f"{DATA_DIR}/calendar.csv", index=False)
print("  calendar.csv: period_code (Finance/Apr-start) + cycle_label (Ops/Jan-start), fiscal_period removed")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BONUS FIX — fiscal_week in visits.csv is a leak (the word "fiscal"
# signals a non-calendar fiscal system). Rename to a neutral label.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("Patching visits.csv (fiscal_week leak)...")

visits = pd.read_csv(f"{DATA_DIR}/visits.csv")
if "fiscal_week" in visits.columns:
    visits = visits.rename(columns={"fiscal_week": "cal_week"})
    visits.to_csv(f"{DATA_DIR}/visits.csv", index=False)
    print("  visits.csv: fiscal_week -> cal_week")
else:
    print("  visits.csv: fiscal_week not present (already patched or renamed), skipping")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RULE 5 — partner booking omission, metadata-column-free
#
# daily_summary gets ONLY venue_code, service_day, total_bookings,
# avg_party_size — no report_source, no last_synced, no column that
# reads as provenance/freshness metadata. total_bookings sums ONLY
# in-house reservations (Ops convention), silently excluding
# partner_bookings.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("Engineering Rule 5 (partner-booking omission) into daily_summary...")

reservations = pd.read_csv(f"{DATA_DIR}/reservations.csv")

ops_totals = (
    reservations
    .groupby(["venue_code", "visit_day"])["expected_covers"]
    .sum()
    .reset_index()
    .rename(columns={"expected_covers": "total_bookings", "visit_day": "service_day"})
)
ops_totals["avg_party_size"] = np.round(np.random.uniform(1.8, 4.2, size=len(ops_totals)), 1)

ops_totals.to_csv(f"{DATA_DIR}/daily_summary.csv", index=False)
print(f"  daily_summary.csv: {len(ops_totals)} rows, venue_code/service_day/total_bookings/avg_party_size only")

print("\n✅ All traps re-applied on flat dataset/ structure.")
print("Final validated state:")
print("  visits: guest_count, service_day, cal_week, walk_in_flag")
print("  reservations: expected_covers (unchanged)")
print("  calendar: period_code, cycle_label (fiscal_period removed)")
print("  daily_summary: venue_code, service_day, total_bookings, avg_party_size (no metadata column)")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DATASET IDENTITY ANONYMIZATION
#
# Found during manual review: renaming COLUMNS was not enough. The
# raw VALUES still fingerprint this as the Recruit Restaurant / Kaggle
# dataset:
#   - venue_code values still carry the original "air_<hash>" prefix
#     (AirREGI system) across visits/reservations/venues/venue_crosswalk/
#     daily_summary
#   - partner_location_code values still carry "hpg_<hash>" (HotPepper
#     Gourmet) across partner_bookings/partner_venues/venue_crosswalk
#   - location_label / region_label contain REAL Japanese place names
#     (e.g. "Hyōgo-ken Kōbe-shi Kumoidōri") pulled straight from the
#     original air_store_info / hpg_store_info genre-and-area fields
#   - cuisine_type / category still use the original genre label text
#     ("Italian/French", "Japanese style") which is itself searchable
#
# Fix: build one consistent ID mapping per identifier (so joins across
# tables don't break), and replace place/genre names with fabricated
# labels that preserve cardinality (same real value -> same fake value
# everywhere) without reproducing anything real or searchable.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("\nAnonymizing dataset identity (IDs, place names, genre labels)...")

venues = pd.read_csv(f"{DATA_DIR}/venues.csv")
partner_venues = pd.read_csv(f"{DATA_DIR}/partner_venues.csv")
visits = pd.read_csv(f"{DATA_DIR}/visits.csv")
reservations = pd.read_csv(f"{DATA_DIR}/reservations.csv")
venue_crosswalk = pd.read_csv(f"{DATA_DIR}/venue_crosswalk.csv")
daily_summary = pd.read_csv(f"{DATA_DIR}/daily_summary.csv")
partner_bookings = pd.read_csv(f"{DATA_DIR}/partner_bookings.csv")

# --- venue_code: air_<hash> -> V0001, V0002, ... (deterministic, sorted) ---
venue_ids = sorted(venues["venue_code"].unique())
venue_map = {old: f"V{idx+1:04d}" for idx, old in enumerate(venue_ids)}

for df, col in [(venues, "venue_code"), (visits, "venue_code"),
                 (reservations, "venue_code"), (venue_crosswalk, "venue_code"),
                 (daily_summary, "venue_code")]:
    df[col] = df[col].map(venue_map).fillna(df[col])

# --- partner_location_code: hpg_<hash> -> P0001, P0002, ... ---
partner_ids = sorted(partner_venues["partner_location_code"].unique())
partner_map = {old: f"P{idx+1:04d}" for idx, old in enumerate(partner_ids)}

for df, col in [(partner_venues, "partner_location_code"),
                 (partner_bookings, "partner_location_code"),
                 (venue_crosswalk, "partner_location_code")]:
    df[col] = df[col].map(partner_map).fillna(df[col])

# --- location_label / region_label: real place names -> fabricated labels ---
# Fabricated, non-real region labels. Deterministic mapping per unique value
# so the same original place always maps to the same fake one (preserves
# groupby/cardinality behavior for analysis) without reproducing any real
# geography.
def fabricate_place_map(unique_values):
    return {val: f"Region-{idx+1:03d}" for idx, val in enumerate(sorted(unique_values))}

loc_map = fabricate_place_map(venues["location_label"].unique())
venues["location_label"] = venues["location_label"].map(loc_map)

region_map = fabricate_place_map(partner_venues["region_label"].unique())
partner_venues["region_label"] = partner_venues["region_label"].map(region_map)

# --- cuisine_type / category: original genre text -> generic fabricated labels ---
def fabricate_category_map(unique_values):
    return {val: f"Category-{idx+1:02d}" for idx, val in enumerate(sorted(unique_values))}

cuisine_map = fabricate_category_map(venues["cuisine_type"].unique())
venues["cuisine_type"] = venues["cuisine_type"].map(cuisine_map)

category_map = fabricate_category_map(partner_venues["category"].unique())
partner_venues["category"] = partner_venues["category"].map(category_map)

# --- write everything back ---
venues.to_csv(f"{DATA_DIR}/venues.csv", index=False)
partner_venues.to_csv(f"{DATA_DIR}/partner_venues.csv", index=False)
visits.to_csv(f"{DATA_DIR}/visits.csv", index=False)
reservations.to_csv(f"{DATA_DIR}/reservations.csv", index=False)
venue_crosswalk.to_csv(f"{DATA_DIR}/venue_crosswalk.csv", index=False)
daily_summary.to_csv(f"{DATA_DIR}/daily_summary.csv", index=False)
partner_bookings.to_csv(f"{DATA_DIR}/partner_bookings.csv", index=False)

print(f"  venue_code: {len(venue_map)} unique values remapped (air_<hash> -> V####)")
print(f"  partner_location_code: {len(partner_map)} unique values remapped (hpg_<hash> -> P####)")
print(f"  location_label: {len(loc_map)} unique real place names -> fabricated Region-###")
print(f"  region_label: {len(region_map)} unique real place names -> fabricated Region-###")
print(f"  cuisine_type: {len(cuisine_map)} unique genre labels -> fabricated Category-##")
print(f"  category: {len(category_map)} unique genre labels -> fabricated Category-##")
print("\n✅ Identity anonymization complete across all 7 affected tables.")
print("Next: re-run ingest_csv.py to rebuild restaurant.db with fully anonymized tables.")
