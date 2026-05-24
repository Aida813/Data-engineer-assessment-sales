import json
import re
import logging
from datetime import datetime

import pandas as pd


# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────
logging.basicConfig(
    filename="ssis_preprocess.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
INPUT_FILE = "customer_data.json"
CLEAN_OUTPUT = "clean_customers.csv"
ERROR_OUTPUT = "error_customers.csv"

VALID_REGIONS = {"North", "South", "East", "West"}
MAX_LOYALTY = 100000


# ─────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────

def is_valid_email(email):
    """Simple email validation: must have @ and a dot after it."""
    if not email:
        return False

    pattern = r'^[^@\s]+@[^@\s]+\.[^@\s]+$'
    return bool(re.match(pattern, str(email)))


def parse_date(val):
    """Try to parse a date in multiple formats."""
    if not val or str(val).strip() == "":
        return None

    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%m/%d/%Y",
        "%Y-%m-%dT%H:%M:%SZ"
    ]

    for fmt in formats:
        try:
            return datetime.strptime(
                str(val).strip(),
                fmt
            ).strftime("%Y-%m-%d")

        except ValueError:
            continue

    return None


def clean_name(name):
    """Remove special characters from customer names."""
    if not name:
        return None

    cleaned = re.sub(
        r'[^a-zA-Z\s\-\.]',
        '',
        str(name)
    ).strip()

    return cleaned if cleaned else None


# ─────────────────────────────────────────────
# MAIN PROCESSING
# ─────────────────────────────────────────────

def process():
    print("=" * 55)
    print("  Customer Data Pre-processor for SSIS")
    print("=" * 55)

    # Load JSON file
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        records = json.load(f)

    print(f"\n  Loaded {len(records)} records from {INPUT_FILE}")
    logger.info(f"Loaded {len(records)} records from {INPUT_FILE}")

    clean_rows = []
    error_rows = []

    for rec in records:
        customer_id = rec.get("customer_id", "")
        raw_name = rec.get("customer_name", "")
        email = rec.get("email", "")
        region = rec.get("region", "")
        raw_date = rec.get("join_date", "")
        loyalty_points = rec.get("loyalty_points")

        errors = []

        # ── Validate customer_id ──
        if not customer_id:
            errors.append("Missing customer_id")

        # ── Clean customer name ──
        clean_nm = clean_name(raw_name)

        if not clean_nm:
            errors.append("Missing or invalid customer_name")
            clean_nm = "UNKNOWN"

        # ── Validate email ──
        if not is_valid_email(email):
            errors.append(f"Invalid email: {email}")
            email = ""
        else:
            email = str(email)

        # ── Validate region ──
        if region not in VALID_REGIONS:
            errors.append(f"Invalid region: {region}")
            region = "Unknown"

        # ── Parse join date ──
        parsed_date = parse_date(raw_date)

        if not parsed_date:
            errors.append(f"Invalid join_date: {raw_date}")

        # ── Validate loyalty_points ──
        if loyalty_points is None:
            errors.append("Missing loyalty_points")
            loyalty_points = 0

        elif loyalty_points < 0:
            errors.append(f"Negative loyalty_points: {loyalty_points}")
            loyalty_points = 0

        elif loyalty_points > MAX_LOYALTY:
            errors.append(
                f"Outlier loyalty_points: {loyalty_points} "
                f"(capped to {MAX_LOYALTY})"
            )
            loyalty_points = MAX_LOYALTY

        # ── Trim values to match SQL table column sizes ──
        customer_id = str(customer_id)[:10] if customer_id else ""
        clean_nm = str(clean_nm)[:150] if clean_nm else "UNKNOWN"
        email = str(email)[:255] if email else ""
        region = str(region)[:50] if region else "Unknown"

        # ── Build cleaned row ──
        clean_row = {
            "customer_id": customer_id,
            "customer_name": clean_nm,
            "email": email,
            "region": region,
            "join_date": parsed_date or "",
            "loyalty_points": loyalty_points,
            "is_valid": 0 if errors else 1
        }

        # All records go to clean_rows because SSIS will split using is_valid
        clean_rows.append(clean_row)

        # Invalid records also go separately to error_rows
        if errors:
            error_row = {
                **clean_row,
                "error_reasons": "; ".join(errors)
            }

            error_rows.append(error_row)

            logger.warning(
                f"Record {customer_id}: {'; '.join(errors)}"
            )

    # ─────────────────────────────────────────────
    # WRITE OUTPUT FILES USING PANDAS
    # ─────────────────────────────────────────────

    # Main CSV for SSIS input: valid + invalid rows
    clean_df = pd.DataFrame(clean_rows)

    # Remove blank customer_id rows before loading to SQL primary key table
    clean_df = clean_df[clean_df["customer_id"] != ""]

    # Remove duplicate customer IDs to avoid SQL PK violation
    clean_df = clean_df.drop_duplicates(
        subset=["customer_id"],
        keep="last"
    )

    # Error CSV: invalid records only
    error_df = pd.DataFrame(error_rows)

    # Remove duplicates from error output also, for consistency
    if not error_df.empty:
        error_df = error_df[error_df["customer_id"] != ""]

        error_df = error_df.drop_duplicates(
            subset=["customer_id"],
            keep="last"
        )

    clean_df.to_csv(
        CLEAN_OUTPUT,
        index=False,
        encoding="utf-8"
    )

    error_df.to_csv(
        ERROR_OUTPUT,
        index=False,
        encoding="utf-8"
    )

    valid_count = len(clean_df[clean_df["is_valid"] == 1])
    invalid_count = len(clean_df[clean_df["is_valid"] == 0])

    print(
        f"\n  ✔ Clean output  → {CLEAN_OUTPUT} "
        f"({valid_count} valid + {invalid_count} flagged rows)"
    )

    print(
        f"  ✔ Error output  → {ERROR_OUTPUT} "
        f"({len(error_df)} error records)"
    )

    print("  ✔ Log           → ssis_preprocess.log")

    logger.info(
        f"Processing complete. "
        f"{valid_count} valid rows, "
        f"{invalid_count} flagged rows, "
        f"{len(error_df)} error records."
    )


if __name__ == "__main__":
    process()
