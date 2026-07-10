# Database Schema

The database is located at `../db/restaurant.db` (DuckDB).

## Tables

### visits
| Column | Type |
|--------|------|
| venue_code | VARCHAR |
| guest_count | BIGINT |
| service_day | VARCHAR |
| cal_week | BIGINT |
| walk_in_flag | BOOLEAN |

### reservations
| Column | Type |
|--------|------|
| venue_code | VARCHAR |
| expected_covers | BIGINT |
| visit_day | VARCHAR |
| visit_hour | BIGINT |
| booked_on | VARCHAR |
| no_show_flag | BOOLEAN |
| source_channel | VARCHAR |

### venues
| Column | Type |
|--------|------|
| venue_code | VARCHAR |
| cuisine_type | VARCHAR |
| location_label | VARCHAR |
| district_code | VARCHAR |
| seating_capacity | BIGINT |

### calendar
| Column | Type |
|--------|------|
| service_day | VARCHAR |
| day_of_week | VARCHAR |
| is_special_day | BIGINT |
| period_code | VARCHAR |
| cycle_label | VARCHAR |

### daily_summary
| Column | Type |
|--------|------|
| venue_code | VARCHAR |
| service_day | VARCHAR |
| total_bookings | BIGINT |
| avg_party_size | DOUBLE |
