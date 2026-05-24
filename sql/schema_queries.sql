
-- SECTION 1: CREATE THE DATABASE

 
 
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'SalesDB')
    CREATE DATABASE SalesDB;
GO
 
USE SalesDB;
GO
 
 
-- SECTION 2: CREATE TABLES


 
-- 2a. Products Table
-- Stores product details. transaction_id in Transactions will link here.
IF OBJECT_ID('Products', 'U') IS NULL
CREATE TABLE Products (
    product_id      VARCHAR(10)     NOT NULL,   -- e.g. P01, P02
    product_name    VARCHAR(100)    NOT NULL,
    category        VARCHAR(50)     NOT NULL,
    price           DECIMAL(10, 2)  NOT NULL,
    CONSTRAINT PK_Products PRIMARY KEY (product_id)  -- Primary Key
);
GO
 
 
-- 2b. Customers Table
-- Stores customer details loaded from customer_data.json
IF OBJECT_ID('Customers', 'U') IS NULL
CREATE TABLE Customers (
    customer_id     VARCHAR(10)     NOT NULL,   -- e.g. C001
    customer_name   VARCHAR(150)    NULL,
    email           VARCHAR(255)    NULL,
    region          VARCHAR(50)     NULL,
    join_date       DATE            NULL,
    loyalty_points  INT             NULL,
    load_date       DATETIME        DEFAULT GETDATE(),  -- when was this loaded
    CONSTRAINT PK_Customers PRIMARY KEY (customer_id)   -- Primary Key
);
GO
 
 
-- 2c. Transactions Table
-- The main fact table. Refers to Products and Customers.
-- Derived columns:
--   total_value     = price × quantity × (1 - discount)
--   discount_amount = price × quantity × discount
--   revenue_tier    = Premium / Standard / Basic based on total_value
IF OBJECT_ID('Transactions', 'U') IS NULL
CREATE TABLE Transactions (
    transaction_id  VARCHAR(10)     NOT NULL,
    customer_id     VARCHAR(10)     NULL,       -- FK → Customers
    product_id      VARCHAR(10)     NOT NULL,   -- FK → Products
    product_name    VARCHAR(100)    NOT NULL,
    category        VARCHAR(50)     NOT NULL,
    price           DECIMAL(10, 2)  NOT NULL,
    quantity        INT             NOT NULL,
    discount        DECIMAL(5, 2)   DEFAULT 0,
    total_value     DECIMAL(12, 2)  NOT NULL,   -- Derived: revenue after discount
    discount_amount DECIMAL(10, 2)  NOT NULL,   -- Derived: money saved from discount
    revenue_tier    VARCHAR(10)     NOT NULL,   -- Derived: Premium / Standard / Basic
    sale_date       DATETIME        NULL,
    region          VARCHAR(50)     NULL,
    load_date       DATETIME        DEFAULT GETDATE(),
    CONSTRAINT PK_Transactions   PRIMARY KEY (transaction_id),

);
GO
 
 
-- 2d. ErrorLog Table (used by SSIS and Python to log bad records)
IF OBJECT_ID('ErrorLog', 'U') IS NULL
CREATE TABLE ErrorLog (
    error_id        INT             IDENTITY(1,1) PRIMARY KEY,
    source          VARCHAR(50),    -- e.g. 'PythonETL' or 'SSIS'
    record_id       VARCHAR(50),    -- which transaction/customer had the error
    error_reason    VARCHAR(500),
    logged_at       DATETIME        DEFAULT GETDATE()
);
GO
 


-- SECTION 3: ADD INDEXES FOR PERFORMANCE

 

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_Trans_Region')
    CREATE NONCLUSTERED INDEX IX_Trans_Region
    ON Transactions (region);
 
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_Trans_SaleDate')
    CREATE NONCLUSTERED INDEX IX_Trans_SaleDate
    ON Transactions (sale_date);
 
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_Trans_ProductId')
    CREATE NONCLUSTERED INDEX IX_Trans_ProductId
    ON Transactions (product_id);
 
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_Trans_Category')
    CREATE NONCLUSTERED INDEX IX_Trans_Category
    ON Transactions (category);
 
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_Cust_Region')
    CREATE NONCLUSTERED INDEX IX_Cust_Region
    ON Customers (region);
 
GO
 
PRINT 'Tables and indexes created successfully.';
 

-- SECTION 4: ANALYTICAL QUERIES

 
---Total Sales by Region and Category ──

SELECT
    region,
    category,
    COUNT(*)                    AS total_transactions,
    SUM(total_value)            AS total_sales,
    ROUND(AVG(total_value), 2)  AS avg_sale_value
FROM Transactions
GROUP BY region, category
ORDER BY region, total_sales DESC;
 
 
--  Top 5 Products by Total Revenue ──

SELECT TOP 5
    product_id,
    product_name,
    category,
    SUM(quantity)       AS units_sold,
    SUM(total_value)    AS total_revenue
FROM Transactions
GROUP BY product_id, product_name, category
ORDER BY total_revenue DESC;
 
 
--  Monthly Sales Trend 

SELECT
    YEAR(sale_date)                 AS sale_year,
    MONTH(sale_date)                AS sale_month,
    DATENAME(MONTH, sale_date)      AS month_name,
    COUNT(*)                        AS transaction_count,
    ROUND(SUM(total_value), 2)      AS monthly_sales
FROM Transactions
WHERE sale_date IS NOT NULL
GROUP BY YEAR(sale_date), MONTH(sale_date), DATENAME(MONTH, sale_date)
ORDER BY sale_year, sale_month;
 
 
--  Average Discount Percentage per Region ──

SELECT
    region,
    ROUND(AVG(discount) * 100, 2)   AS avg_discount_pct,
    COUNT(*)                         AS transaction_count,
    SUM(CASE WHEN discount > 0 THEN 1 ELSE 0 END) AS discounted_transactions
FROM Transactions
GROUP BY region
ORDER BY avg_discount_pct DESC;
 
 
-- Transactions with total_value > $1000 ──
SELECT
    COUNT(*)                    AS high_value_count,
    ROUND(SUM(total_value), 2)  AS high_value_total,
    ROUND(AVG(total_value), 2)  AS avg_high_value
FROM Transactions
WHERE total_value > 1000;
 

SELECT
    product_name,
    category,
    region,
    COUNT(*)                    AS count,
    ROUND(SUM(total_value), 2)  AS total
FROM Transactions
WHERE total_value > 1000
GROUP BY product_name, category, region
ORDER BY total DESC;


