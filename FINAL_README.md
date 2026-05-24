# Mid-Level Data Engineer Technical Assessment

## Project Overview

This project implements an end-to-end data engineering solution for processing and analyzing sales and customer data. The solution includes a Python ETL pipeline, SQL Server schema and analytical queries, SSIS customer data pipeline, data validation/error logging, and a Power BI dashboard.

## Technology Stack

| Area | Tools Used |
|---|---|
| Programming | Python |
| Data Processing | pandas |
| Database | Microsoft SQL Server |
| SQL Tool | SQL Server Management Studio |
| ETL Tool | SQL Server Integration Services |
| BI Tool | Power BI Desktop |
| Connectivity | pyodbc, ODBC Driver 17 for SQL Server, Microsoft OLE DB Driver |
| Version Control | GitHub |

## Repository Structure

```text
DATA_ENG_ASSESSMENT_APPLAB/
│
├── python_etl/
│   ├── etl_pipeline.py
│   ├── scaled_sales_data.json
│   ├── processed_sales_data.csv
│   └── etl_pipeline.log
│
├── sql/
│   ├── schema_and_queries.sql
│   └── ssis_tables.sql
│
├── SSIS/
│   ├── customer_data.json
│   ├── preprocess_ssis.py
│   ├── clean_customers.csv
│   ├── error_customers.csv
│   ├── ssis_preprocess.log
│   └── Package.dtsx
│
├── powerbi/
│   └── Sales_Customer_Dashboard.pbix
│
├── docs/
│   └── PowerBI_DAX_Measures.txt
│
├── screenshots/
│   ├── python_etl_success.png
│   ├── etl_log_success.png
│   ├── sql_transaction_count.png
│   ├── sql_query_results.png
│   ├── ssis_control_flow.png
│   ├── ssis_data_flow.png
│   ├── ssis_variables.png
│   ├── ssis_checkpoint_properties.png
│   ├── ssis_execution_success.png
│   ├── ssis_customers_count.png
│   ├── ssis_errorlog_count.png
│   ├── powerbi_dashboard.png
│   └── powerbi_model_view.png
│
└── README.md
```

> Note: If your screenshot file names are different, update the image paths in this README to match your exact GitHub screenshot file names.

---

# Part 1: Python ETL Pipeline

## Objective

The Python ETL pipeline processes semi-structured sales transaction data, validates and transforms the records, and loads the processed data into SQL Server.

The dataset was scaled to 800 records, satisfying the requirement to scale the sample dataset to 500–1,000 records.

## ETL Flow

```text
Generate Scaled Sales Data
        ↓
Extract JSON Records
        ↓
Flatten Nested Product Details
        ↓
Clean and Transform Data
        ↓
Create Derived Columns
        ↓
Apply Incremental Load Logic
        ↓
Load into SQL Server Transactions Table
        ↓
Export Processed CSV and Log File
```

## Key Transformations

The ETL pipeline performs the following transformations:

- Standardizes date formats
- Fills missing discounts with 0
- Replaces missing customer IDs with `UNKNOWN`
- Removes records with invalid negative or zero quantity
- Removes records with missing transaction IDs
- Removes records with invalid dates
- Calculates derived sales fields

## Derived Columns

| Column | Logic |
|---|---|
| `total_value` | `price × quantity × (1 - discount)` |
| `discount_amount` | `price × quantity × discount` |
| `revenue_tier` | Classifies transactions as Premium, Standard, or Basic |

Revenue tier logic:

```text
Premium  = total_value >= 2000
Standard = total_value >= 500
Basic    = total_value < 500
```

## Incremental Load Logic

The Python ETL checks existing `transaction_id` values in the SQL Server `Transactions` table before inserting data.

```text
Read existing transaction IDs
        ↓
Compare with transformed records
        ↓
Insert only new transaction IDs
```

This prevents duplicate transactions when the ETL pipeline is rerun.

## Logging

The pipeline writes execution details to:

```text
etl_pipeline.log
```

The log captures generation, extraction, transformation, invalid row removal, insert counts, and any database load errors.

## Python ETL Screenshots

### Python ETL Successful Execution

![Python ETL Successful Execution]

### ETL Log Output

![ETL Log Output]![alt text](python_etl_success-1.png)

---

# Part 2: SQL Server Database Design and Analytical Queries

## Objective

The SQL Server database stores the processed sales and customer data and supports analytical reporting.

Database used:

```text
SalesDB
```

## Tables Created

### Transactions

Stores sales transaction records loaded by the Python ETL pipeline.

Important columns:

```text
transaction_id
customer_id
product_id
product_name
category
price
quantity
discount
total_value
discount_amount
revenue_tier
sale_date
region
load_date
```

### Customers

Stores customer records loaded through the SSIS package.

Important columns:

```text
customer_id
customer_name
email
region
join_date
loyalty_points
load_date
```

### Products

Stores product master data.

Important columns:

```text
product_id
product_name
category
price
```

### ErrorLog

Stores invalid customer records identified during the SSIS pipeline.

Important columns:

```text
error_id
source
record_id
error_reason
logged_at
```

## Primary Keys

| Table | Primary Key |
|---|---|
| Transactions | `transaction_id` |
| Customers | `customer_id` |
| Products | `product_id` |
| ErrorLog | `error_id` |

## Foreign Key Note

The database schema includes normalized tables for `Transactions`, `Customers`, and `Products`. During ETL prototyping, foreign key constraints were relaxed to simplify the initial load and avoid load-order issues. In a production environment, dimension tables should be loaded first and foreign key enforcement should be enabled afterward.

## Indexes

| Index | Table | Column |
|---|---|---|
| `IX_Trans_Region` | Transactions | region |
| `IX_Trans_SaleDate` | Transactions | sale_date |
| `IX_Trans_ProductId` | Transactions | product_id |
| `IX_Trans_Category` | Transactions | category |
| `IX_Cust_Region` | Customers | region |

Indexes improve performance for filtering, grouping, joining, sorting, and aggregation queries.

## Analytical Queries Implemented

The following required SQL queries were implemented:

1. Total sales by region and category
2. Top 5 products by total revenue
3. Monthly sales trend
4. Average discount percentage per region
5. Number of transactions with `total_value > 1000`

## SQL Screenshots

### Transaction Count Verification

![SQL Transaction Count]![alt text](sql_count_transactions.png)

### SQL Query Results

![SQL Query Results]
![alt text](sql_query1_region_category.png)
![alt text](sql_query2_top5_products.png)
![alt text](sql_query3_monthly_trend.png)
![alt text](sql_query4_avg_discount.png)
![alt text](sql_query5_high_value.png)
---

# Part 3: SSIS Pipeline

## Objective

The SSIS package processes customer data, transforms and validates records, loads valid rows into the SQL Server `Customers` table, and logs invalid rows into the SQL Server `ErrorLog` table.

Source file:

```text
customer_data.json
```

Since SSIS works best with flat files, a Python preprocessing step converts the JSON file into CSV format for SSIS ingestion.

## SSIS Preprocessing

Script:

```text
preprocess_ssis.py
```

Input:

```text
customer_data.json
```

Outputs:

```text
clean_customers.csv
error_customers.csv
ssis_preprocess.log

```

The preprocessing script performs:

- JSON reading
- Customer name cleaning
- Email validation
- Region validation
- Join date parsing
- Loyalty points validation
- Outlier capping
- Negative loyalty point correction
- Duplicate customer ID removal
- Column length trimming to match SQL schema
- `is_valid` flag creation

The `is_valid` flag is used by SSIS to separate valid and invalid records.

## SSIS Control Flow

The SSIS package contains a Data Flow Task.

![SSIS Control Flow]![alt text](<ssis_control_flow (2).png>)

## SSIS Data Flow

```text
Flat File Source: clean_customers.csv
        ↓
Derived Column
        ↓
Conditional Split
     ↙              ↘
ValidRows          InvalidRows
   ↓                  ↓
OLE DB Destination   Derived Column_ErrorLog
Customers            ↓
                     OLE DB Destination
                     ErrorLog
```

![SSIS Data Flow]![alt text](ssis_data_flow.png)

## SSIS Components

| Component | Purpose |
|---|---|
| Flat File Source | Reads `clean_customers.csv` |
| Derived Column | Adds metadata columns |
| Conditional Split | Splits records based on `is_valid` |
| OLE DB Destination | Loads valid records into `Customers` |
| Derived Column_ErrorLog | Adds `source` and `error_reason` |
| OLE DB Destination_ErrorLog | Loads invalid records into `ErrorLog` |

## Conditional Split Logic

```text
ValidRows:
is_valid == "1"

InvalidRows:
is_valid == "0"
```

## Error Logging

Invalid records are inserted into `ErrorLog`.

| SSIS Column | SQL Column |
|---|---|
| `source` | `source` |
| `customer_id` | `record_id` |
| `error_reason` | `error_reason` |

`error_id` and `logged_at` are generated by SQL Server.

## Variables and Parameters

| Variable | Purpose |
|---|---|
| `CustomerFilePath` | Path for `clean_customers.csv` |
| `ServerName` | SQL Server instance |
| `DatabaseName` | SQL Server database |
| `ErrorSource` | Error source value, `SSIS` |

The `CustomerFilePath` variable is connected to the Flat File Connection Manager using an expression on the `ConnectionString` property. The `ErrorSource` variable is used in `Derived Column_ErrorLog`.

![SSIS Variables]![alt text](variables_ssis.png)

## Checkpoint and Restart Features

Checkpoint settings were enabled:

```text
SaveCheckpoints = True
CheckpointUsage = IfExists
CheckpointFileName = ssis_checkpoint.xml
```

![SSIS Checkpoint Properties]![alt text](ssis_checkpoint_properties.png)

## SSIS Execution Results

![SSIS Successful Execution]![alt text](ssis_execution_success.png)

### Customers Count

![SSIS Customers Count]![alt text](customer_table_count.png)

### ErrorLog Count

![SSIS ErrorLog Count]![alt text](error_table_count.png)

---

# Part 4: Power BI Dashboard

## Objective

The Power BI dashboard visualizes insights from both the sales and customer datasets.

Connection:

```text
Server: aida_dellG15\G15SQLSERVER
Database: SalesDB
```

Tables used:

```text
Transactions
Customers
```

## DAX Measures

### Total Sales

```DAX
Total Sales = SUM(Transactions[total_value])
```

### Average Sale per Transaction

```DAX
Avg Sale per Transaction = AVERAGE(Transactions[total_value])
```

### Total Loyalty Points

```DAX
Total Loyalty Points = SUM(Customers[loyalty_points])
```

### High Value Transactions

```DAX
High Value Transactions =
CALCULATE(
    COUNTROWS(Transactions),
    Transactions[total_value] > 1000
)
```

### Sales YTD

```DAX
Sales YTD =
TOTALYTD(
    [Total Sales],
    Transactions[sale_date]
)
```

### Units Sold

```DAX
Units Sold = SUM(Transactions[quantity])
```

A separate DAX documentation file is included:

```text
docs/PowerBI_DAX_Measures.txt
```

## Dashboard Visuals

| Visual | Description |
|---|---|
| Bar Chart | Total Sales by Region and Category |
| Line Chart | Monthly Sales Trend |
| Table | Top 5 Products by Revenue |
| Cards | Average Sale per Transaction, Total Customers, High Value Transactions |
| Donut Chart | Loyalty Points Distribution by Region |
| Column Chart | Total Sales by Revenue Tier |

## Power BI Dashboard Screenshot

![Power BI Dashboard]![alt text](powerbi_dashboard.png)

## Power BI Model View

![Power BI Model View]![alt text](powerbi_model_relationships.png)

## Dashboard Insights

Key insights from the dashboard:

1. Premium transactions contribute the highest sales value.
2. Laptop is the highest revenue-generating product.
3. Electronics contributes strongly to overall revenue.
4. Monthly sales show variation across the year.
5. Loyalty points are distributed across customer regions.
6. High-value transactions represent an important revenue segment.
7. Revenue tier analysis helps separate Premium, Standard, and Basic transaction performance.

---

# Challenges Faced and Solutions

| Challenge | Solution |
|---|---|
| SQL Server, SSMS, Visual Studio SSDT/SSIS, and required database drivers were not initially installed on the system | Installed and configured SQL Server, SQL Server Management Studio, Visual Studio SSIS extension, ODBC Driver 17, and Microsoft OLE DB Driver for SQL Server to build and test the solution locally |
| Python could not connect to SQL Server | Corrected SQL Server instance to `aida_dellG15\G15SQLSERVER` |
| Foreign key load issue | Temporarily relaxed FK constraints during prototyping |
| SSIS provider error | Used Microsoft OLE DB Driver for SQL Server |
| CSV truncation errors | Trimmed data in Python preprocessing |
| Duplicate customer IDs | Added pandas deduplication |
| ErrorLog initially showed zero rows | Corrected Conditional Split logic |
| CSV file locked during SSIS run | Closed the open CSV file before execution |
| Checkpoint requirement | Enabled package checkpoint properties |
| Variables requirement | Added variables for file path, server, database, and error source |

---

# How to Run the Project

## Step 1: Create SQL Database and Tables

Run in SSMS:

```text
schema_and_queries.sql
ssis_tables.sql
```

## Step 2: Run Python ETL

```bash
cd python_etl
python etl_pipeline.py
```

Verify:

```sql
USE SalesDB;
SELECT COUNT(*) FROM Transactions;
```

## Step 3: Run Customer Preprocessing

```bash
cd SSIS
python preprocess_ssis.py
```

## Step 4: Run SSIS Package

Open the SSIS project in Visual Studio and run:

```text
Package.dtsx
```

Verify:

```sql
USE SalesDB;
SELECT COUNT(*) FROM Customers;
SELECT COUNT(*) FROM ErrorLog;
```

## Step 5: Run SQL Analytical Queries

Run the analytical query section in:

```text
schema_and_queries.sql
```

## Step 6: Open Power BI Dashboard

Open:

```text
Sales_Customer_Dashboard.pbix
```

Refresh the data connection if required.

---

# Files to Include in GitHub

Yes, include the generated files if they are not very large. For this assessment, including outputs is useful because they prove the pipelines ran successfully.

Recommended files to include:

```text
etl_pipeline.py
preprocess_ssis.py
schema_and_queries.sql
ssis_tables.sql
Package.dtsx
Sales_Customer_Dashboard.pbix
PowerBI_DAX_Measures.txt
README.md
customer_data.json
processed_sales_data.csv
scaled_sales_data.json
clean_customers.csv
error_customers.csv
etl_pipeline.log
ssis_preprocess.log
screenshots/
```

Recommended organization:

```text
outputs/
  processed_sales_data.csv
  scaled_sales_data.json
  clean_customers.csv
  error_customers.csv
  etl_pipeline.log
  ssis_preprocess.log
```

If any file is too large, keep it out of GitHub and mention it in the README. For this assessment, the CSV and log files are small enough to include.

---

# Production Deployment Suggestions

For production deployment, the following improvements are recommended:

1. Load dimension tables before loading transaction fact data.
2. Re-enable foreign key constraints after correct load order is implemented.
3. Use staging tables before loading final reporting tables.
4. Store file paths and connection details securely in configuration files or environment variables.
5. Schedule ETL jobs using SQL Server Agent or Azure Data Factory.
6. Add batch IDs and audit columns to track each ETL run.
7. Implement automated data quality checks.
8. Store raw invalid records in a dedicated error table.
9. Add a Date dimension table for better Power BI time intelligence.
10. Publish the dashboard to Power BI Service with scheduled refresh.

---



# GitHub Repository Link

https://github.com/Aida813/Data-engineer-assessment-sales
