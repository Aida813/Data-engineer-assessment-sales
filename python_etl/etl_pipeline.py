import json
import random
import logging

from datetime import datetime, timedelta

import pandas as pd
import pyodbc


# =========================================================
# CONFIGURATION
# =========================================================

DB_SERVER = r"aida_dellG15\G15SQLSERVER"
DB_NAME = "SalesDB"
DB_DRIVER = "ODBC Driver 17 for SQL Server"

CONNECTION_STRING = (
    f"DRIVER={{{DB_DRIVER}}};"
    f"SERVER={DB_SERVER};"
    f"DATABASE={DB_NAME};"
    "Trusted_Connection=yes;"
)

TARGET_RECORDS = 800

PREMIUM_THRESHOLD = 2000
STANDARD_THRESHOLD = 500


# =========================================================
# LOGGING CONFIGURATION
# =========================================================

logging.basicConfig(
    filename="etl_pipeline.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger(__name__)


# =========================================================
# GENERATE SCALED DATASET
# =========================================================

def generate_scaled_dataset(target=TARGET_RECORDS):

    logger.info(f"Generating {target} sales records")

    products = [
        {"id": "P01", "name": "Laptop",   "category": "Electronics", "price": 999.99},
        {"id": "P02", "name": "Mouse",    "category": "Accessories", "price": 19.99},
        {"id": "P03", "name": "Monitor",  "category": "Electronics", "price": 299.50},
        {"id": "P04", "name": "Keyboard", "category": "Accessories", "price": 49.90},
        {"id": "P05", "name": "Desk",     "category": "Furniture",   "price": 189.00},
        {"id": "P06", "name": "Chair",    "category": "Furniture",   "price": 249.00},
        {"id": "P07", "name": "Webcam",   "category": "Electronics", "price": 79.99},
        {"id": "P08", "name": "Headset",  "category": "Accessories", "price": 59.99},
    ]

    regions = ["North", "South", "East", "West"]

    discounts = [0, 0.05, 0.10, 0.15, 0.20, None]

    start_date = datetime(2023, 1, 1)

    records = []

    for i in range(1, target + 1):

        product = random.choice(products)

        quantity = random.randint(1, 10)

        customer_id = f"C{random.randint(1, 100):03}"

        # Introduce missing customer IDs (~5% of records)
        if random.random() < 0.05:
            customer_id = None

        # Introduce invalid quantities (~3% of records)
        if random.random() < 0.03:
            quantity = -abs(quantity)

        sale_date = start_date + timedelta(
            days=random.randint(0, 364)
        )

        formats = [
            "%Y/%m/%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d"
        ]

        records.append({

            "transaction_id": f"T{i:04}",

            "customer_id": customer_id,

            "product": product,

            "quantity": quantity,

            "discount": random.choice(discounts),

            "date": sale_date.strftime(
                random.choice(formats)
            ),

            "region": random.choice(regions)

        })

    logger.info(f"{len(records)} records generated")

    return records


# =========================================================
# EXTRACT DATA
# =========================================================

def extract(records):

    logger.info("Starting extraction phase")

    flattened_rows = []

    for record in records:

        product = record.get("product", {})

        flattened_rows.append({

            "transaction_id": record.get("transaction_id"),

            "customer_id": record.get("customer_id"),

            "product_id": product.get("id"),

            "product_name": product.get("name"),

            "category": product.get("category"),

            "price": product.get("price"),

            "quantity": record.get("quantity"),

            "discount": record.get("discount"),

            "date": record.get("date"),

            "region": record.get("region")

        })

    df = pd.DataFrame(flattened_rows)

    logger.info(f"Extracted {len(df)} rows")

    return df


# =========================================================
# DATE PARSER
# =========================================================

def parse_date(value):

    if pd.isna(value):
        return None

    formats = [
        "%Y/%m/%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%m/%d/%Y"
    ]

    for fmt in formats:

        try:
            return datetime.strptime(str(value), fmt)

        except ValueError:
            continue

    logger.warning(f"Invalid date format: {value}")

    return None


# =========================================================
# REVENUE TIER
# Classifies each sale into Premium / Standard / Basic
# based on the total_value of that transaction
# =========================================================

def assign_revenue_tier(total_value):

    if total_value >= PREMIUM_THRESHOLD:
        return "Premium"

    elif total_value >= STANDARD_THRESHOLD:
        return "Standard"

    return "Basic"


# =========================================================
# TRANSFORM DATA
# =========================================================

def transform(df):

    logger.info("Starting transformation phase")

    original_count = len(df)

    # Standardize dates
    df["sale_date"] = pd.to_datetime(
        df["date"].apply(parse_date)
    )

    # Handle missing discounts — treat as no discount
    df["discount"] = df["discount"].fillna(0)

    # Handle missing customer IDs
    df["customer_id"] = (
        df["customer_id"].fillna("UNKNOWN")
    )

    # Remove rows with invalid (negative or zero) quantity
    invalid_quantity = df["quantity"] <= 0

    if invalid_quantity.sum() > 0:
        logger.warning(
            f"Removed {invalid_quantity.sum()} rows with invalid quantity"
        )

    df = df[~invalid_quantity]

    # Remove rows with missing transaction IDs
    invalid_transactions = df["transaction_id"].isna()

    if invalid_transactions.sum() > 0:
        logger.warning(
            f"Removed {invalid_transactions.sum()} rows with null transaction_id"
        )

    df = df[~invalid_transactions]

    # Remove rows where date could not be parsed
    invalid_dates = df["sale_date"].isna()

    if invalid_dates.sum() > 0:
        logger.warning(
            f"Removed {invalid_dates.sum()} rows with invalid dates"
        )

    df = df[~invalid_dates]

    # ── Derived Column 1: total_value ──
    # The actual revenue from this transaction after applying the discount
    # Formula: price × quantity × (1 - discount)
    df["total_value"] = (
        df["price"]
        * df["quantity"]
        * (1 - df["discount"])
    ).round(2)

    # ── Derived Column 2: discount_amount ──
    # How much money was saved due to the discount
    # Formula: price × quantity × discount
    df["discount_amount"] = (
        df["price"]
        * df["quantity"]
        * df["discount"]
    ).round(2)

    # ── Derived Column 3: revenue_tier ──
    # Classifies the sale as Premium / Standard / Basic
    # based on total_value thresholds defined in config
    df["revenue_tier"] = (
        df["total_value"].apply(assign_revenue_tier)
    )

    logger.info(
        f"Transformation completed. "
        f"{len(df)} valid rows remaining "
        f"(Removed {original_count - len(df)} rows)"
    )

    return df


# =========================================================
# LOAD DATA
# =========================================================

def load(df):

    logger.info("Starting load phase")

    try:

        with pyodbc.connect(CONNECTION_STRING) as conn:

            cursor = conn.cursor()

            # Fetch already-loaded transaction IDs (incremental logic)
            cursor.execute(
                "SELECT transaction_id FROM Transactions"
            )

            existing_ids = set(
                row[0] for row in cursor.fetchall()
            )

            # Only insert records not already in the database
            new_records = df[
                ~df["transaction_id"].isin(existing_ids)
            ]

            logger.info(
                f"{len(new_records)} new records identified for insert"
            )

            insert_sql = """
                INSERT INTO Transactions (
                    transaction_id,
                    customer_id,
                    product_id,
                    product_name,
                    category,
                    price,
                    quantity,
                    discount,
                    total_value,
                    discount_amount,
                    revenue_tier,
                    sale_date,
                    region
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            # Build list of tuples — faster than row-by-row insert
            rows_to_insert = [
                (
                    row.transaction_id,
                    row.customer_id,
                    row.product_id,
                    row.product_name,
                    row.category,
                    float(row.price),
                    int(row.quantity),
                    float(row.discount),
                    float(row.total_value),
                    float(row.discount_amount),
                    row.revenue_tier,
                    row.sale_date,
                    row.region
                )
                for row in new_records.itertuples(index=False)
            ]

            cursor.executemany(insert_sql, rows_to_insert)

            conn.commit()

            logger.info(
                f"{len(rows_to_insert)} records inserted successfully"
            )

    except Exception as e:

        logger.exception(
            f"Database load failed: {e}"
        )


# =========================================================
# MAIN PIPELINE
# =========================================================

def main():

    try:

        logger.info("ETL Pipeline Started")

        # Step 1: Generate 800-record dataset
        records = generate_scaled_dataset()

        # Save raw JSON for reference
        with open("scaled_sales_data.json", "w") as file:
            json.dump(records, file, indent=2)

        logger.info("Scaled dataset exported to scaled_sales_data.json")

        # Step 2: Extract
        raw_df = extract(records)

        # Step 3: Transform
        clean_df = transform(raw_df)

        # Step 4: Load into SQL Server
        load(clean_df)

        # Export final cleaned data as CSV
        clean_df.to_csv("processed_sales_data.csv", index=False)

        logger.info("Processed CSV exported to processed_sales_data.csv")

        logger.info("ETL Pipeline Completed Successfully")

        print("ETL Pipeline Completed Successfully")

    except Exception as e:

        logger.exception(f"Pipeline execution failed: {e}")

        print("ETL Pipeline Failed. Check etl_pipeline.log")


# =========================================================
# RUN PIPELINE
# =========================================================

if __name__ == "__main__":

    main()
