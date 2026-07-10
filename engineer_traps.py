import pandas as pd
import numpy as np
import os
import random

random.seed(42)
np.random.seed(42)

INPUT_DIR = "data_src/restaurant/dataset/recruit-restaurant-visitor-forecasting"
OUTPUT_DIR = "data_src/restaurant/dataset/engineered"
os.makedirs(OUTPUT_DIR, exist_ok=True)

print("Loading original data...")

# ── LOAD ORIGINALS ────────────────────────────────────────────────────────────
air_visit     = pd.read_csv(f"{INPUT_DIR}/air_visit_data.csv")
air_reserve   = pd.read_csv(f"{INPUT_DIR}/air_reserve.csv")
air_store     = pd.read_csv(f"{INPUT_DIR}/air_store_info.csv")
hpg_reserve   = pd.read_csv(f"{INPUT_DIR}/hpg_reserve.csv")
hpg_store     = pd.read_csv(f"{INPUT_DIR}/hpg_store_info.csv")
store_rel     = pd.read_csv(f"{INPUT_DIR}/store_id_relation.csv")
date_info     = pd.read_csv(f"{INPUT_DIR}/date_info.csv")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TABLE 1: visits  (was air_visit_data)
# TRAPS:
#   - rename table + columns (Opus knows air_visit_data / visitors)
#   - split visit_date into service_day + fiscal_week (date trap)
#   - add walk_in_flag column (distractor)
#   - delete air_store_id → replace with venue_code (ID trap)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("Engineering visits table...")

visits = air_visit.copy()
visits = visits.rename(columns={
    "air_store_id": "venue_code",
    "visitors":     "guest_count",        # ⚠️ trap: Opus knows "visitors"
})

# split visit_date → service_day (str) + fiscal_week (int)  ⚠️ date trap
visits["visit_date"] = pd.to_datetime(visits["visit_date"])
visits["service_day"] = visits["visit_date"].dt.strftime("%d-%b-%Y")   # "16-Jan-2016"
# fiscal week: Japan fiscal year starts April 1
visits["fiscal_week"] = visits["visit_date"].apply(
    lambda d: int((d - pd.Timestamp(d.year if d.month >= 4 else d.year - 1, 4, 1)).days / 7) + 1
)
visits = visits.drop(columns=["visit_date"])   # ⚠️ remove original date

# add distractor column
visits["walk_in_flag"] = np.random.choice([True, False], size=len(visits), p=[0.72, 0.28])

visits.to_csv(f"{OUTPUT_DIR}/visits.csv", index=False)
print(f"  visits.csv: {len(visits)} rows, cols: {list(visits.columns)}")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TABLE 2: reservations  (was air_reserve)
# TRAPS:
#   - rename to reservations
#   - reserve_visitors → expected_covers  ⚠️
#   - venue_code instead of air_store_id
#   - split visit_datetime → visit_day + visit_hour  ⚠️ leakage trap
#   - add no_show_flag distractor
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("Engineering reservations table...")

reservations = air_reserve.copy()
reservations = reservations.rename(columns={
    "air_store_id":     "venue_code",
    "reserve_visitors": "expected_covers",   # ⚠️ trap
})

reservations["visit_datetime"]   = pd.to_datetime(reservations["visit_datetime"])
reservations["reserve_datetime"] = pd.to_datetime(reservations["reserve_datetime"])
reservations["visit_day"]  = reservations["visit_datetime"].dt.strftime("%d-%b-%Y")
reservations["visit_hour"] = reservations["visit_datetime"].dt.hour
reservations["booked_on"]  = reservations["reserve_datetime"].dt.strftime("%d-%b-%Y %H:%M")
reservations = reservations.drop(columns=["visit_datetime", "reserve_datetime"])

reservations["no_show_flag"] = np.random.choice([True, False], size=len(reservations), p=[0.08, 0.92])

reservations.to_csv(f"{OUTPUT_DIR}/reservations.csv", index=False)
print(f"  reservations.csv: {len(reservations)} rows, cols: {list(reservations.columns)}")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TABLE 3: venues  (was air_store_info)
# TRAPS:
#   - venue_code instead of air_store_id
#   - cuisine_type instead of air_genre_name
#   - drop latitude/longitude → replace with district_code  ⚠️
#   - add seating_capacity distractor
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("Engineering venues table...")

venues = air_store.copy()
venues = venues.rename(columns={
    "air_store_id":   "venue_code",
    "air_genre_name": "cuisine_type",
    "air_area_name":  "location_label",
})
venues = venues.drop(columns=["latitude", "longitude"])
venues["district_code"] = ["D" + str(random.randint(100, 999)) for _ in range(len(venues))]
venues["seating_capacity"] = np.random.randint(10, 120, size=len(venues))

venues.to_csv(f"{OUTPUT_DIR}/venues.csv", index=False)
print(f"  venues.csv: {len(venues)} rows, cols: {list(venues.columns)}")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TABLE 4: partner_bookings  (was hpg_reserve)
# TRAPS:
#   - completely rename to hide HPG origin
#   - partner_location_code instead of hpg_store_id  ⚠️ ID trap
#   - covers_booked instead of reserve_visitors
#   - same datetime split trick
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("Engineering partner_bookings table...")

partner_bookings = hpg_reserve.copy()
partner_bookings = partner_bookings.rename(columns={
    "hpg_store_id":     "partner_location_code",   # ⚠️ ID trap
    "reserve_visitors": "covers_booked",
})
partner_bookings["visit_datetime"]   = pd.to_datetime(partner_bookings["visit_datetime"])
partner_bookings["reserve_datetime"] = pd.to_datetime(partner_bookings["reserve_datetime"])
partner_bookings["visit_day"]  = partner_bookings["visit_datetime"].dt.strftime("%d-%b-%Y")
partner_bookings["visit_hour"] = partner_bookings["visit_datetime"].dt.hour
partner_bookings["booked_on"]  = partner_bookings["reserve_datetime"].dt.strftime("%d-%b-%Y %H:%M")
partner_bookings = partner_bookings.drop(columns=["visit_datetime", "reserve_datetime"])

partner_bookings.to_csv(f"{OUTPUT_DIR}/partner_bookings.csv", index=False)
print(f"  partner_bookings.csv: {len(partner_bookings)} rows, cols: {list(partner_bookings.columns)}")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TABLE 5: partner_venues  (was hpg_store_info)
# TRAPS:
#   - partner_location_code instead of hpg_store_id
#   - category instead of hpg_genre_name
#   - drop lat/long, add region_tag
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("Engineering partner_venues table...")

partner_venues = hpg_store.copy()
partner_venues = partner_venues.rename(columns={
    "hpg_store_id":   "partner_location_code",
    "hpg_genre_name": "category",
    "hpg_area_name":  "region_label",
})
partner_venues = partner_venues.drop(columns=["latitude", "longitude"])
partner_venues["region_tag"] = ["R" + str(random.randint(10, 99)) for _ in range(len(partner_venues))]

partner_venues.to_csv(f"{OUTPUT_DIR}/partner_venues.csv", index=False)
print(f"  partner_venues.csv: {len(partner_venues)} rows, cols: {list(partner_venues.columns)}")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TABLE 6: venue_crosswalk  (was store_id_relation)
# TRAPS:
#   - rename both ID columns  ⚠️ join trap
#   - intentionally corrupt 15% of mappings
#   - add is_active column (some False)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("Engineering venue_crosswalk table...")

crosswalk = store_rel.copy()
crosswalk = crosswalk.rename(columns={
    "air_store_id": "venue_code",
    "hpg_store_id": "partner_location_code",
})

# corrupt 15% of mappings  ⚠️ join trap
n_corrupt = int(len(crosswalk) * 0.15)
corrupt_idx = random.sample(range(len(crosswalk)), n_corrupt)
for idx in corrupt_idx:
    crosswalk.at[idx, "partner_location_code"] = "INVALID_" + str(random.randint(1000, 9999))

crosswalk["is_active"] = [False if i in corrupt_idx else True for i in range(len(crosswalk))]

crosswalk.to_csv(f"{OUTPUT_DIR}/venue_crosswalk.csv", index=False)
print(f"  venue_crosswalk.csv: {len(crosswalk)} rows, cols: {list(crosswalk.columns)}")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TABLE 7: calendar  (was date_info)
# TRAPS:
#   - rename calendar_date → service_day (matches visits table)
#   - add fiscal_period column (Japan FY: Apr-Mar)
#   - holiday_flg → is_special_day
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("Engineering calendar table...")

calendar = date_info.copy()
calendar = calendar.rename(columns={
    "calendar_date": "service_day",
    "holiday_flg":   "is_special_day",
})
calendar["service_day"] = pd.to_datetime(calendar["service_day"]).dt.strftime("%d-%b-%Y")

# add fiscal_period (Q1=Apr-Jun, Q2=Jul-Sep, Q3=Oct-Dec, Q4=Jan-Mar)
def fiscal_quarter(date_str):
    d = pd.to_datetime(date_str, format="%d-%b-%Y")
    m = d.month
    if m >= 4 and m <= 6:   return "FQ1"
    elif m >= 7 and m <= 9:  return "FQ2"
    elif m >= 10 and m <= 12: return "FQ3"
    else:                    return "FQ4"

calendar["fiscal_period"] = calendar["service_day"].apply(fiscal_quarter)

calendar.to_csv(f"{OUTPUT_DIR}/calendar.csv", index=False)
print(f"  calendar.csv: {len(calendar)} rows, cols: {list(calendar.columns)}")

print("\n✅ All 7 engineered tables saved to:", OUTPUT_DIR)
print("\nTrap summary:")
print("  visits:           guest_count (not visitors), fiscal_week + service_day (no raw date)")
print("  reservations:     expected_covers (not reserve_visitors), visit split to day+hour")
print("  venues:           no lat/long, district_code instead")
print("  partner_bookings: covers_booked, HPG origin hidden")
print("  partner_venues:   category (not hpg_genre_name)")
print("  venue_crosswalk:  15% corrupted mappings, is_active flag")
print("  calendar:         fiscal_period added, holiday_flg renamed")