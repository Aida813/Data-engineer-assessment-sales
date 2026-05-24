USE SalesDB;
GO
 
-- ─────────────────────────────────────────────
-- Customers table (SSIS loads into this)
-- ─────────────────────────────────────────────
IF OBJECT_ID('Customers', 'U') IS NULL
CREATE TABLE Customers (
    customer_id     VARCHAR(10)     NOT NULL,
    customer_name   VARCHAR(150)    NULL,
    email           VARCHAR(255)    NULL,
    region          VARCHAR(50)     NULL,
    join_date       DATE            NULL,
    loyalty_points  INT             NULL        DEFAULT 0,
    load_date       DATETIME                    DEFAULT GETDATE(),
    CONSTRAINT PK_Customers PRIMARY KEY (customer_id)
);
GO
 
 
-- ─────────────────────────────────────────────
-- ErrorLog table (SSIS logs bad records here)
-- ─────────────────────────────────────────────
IF OBJECT_ID('ErrorLog', 'U') IS NULL
CREATE TABLE ErrorLog (
    error_id        INT             IDENTITY(1,1) PRIMARY KEY,
    source          VARCHAR(50)     NOT NULL,   -- 'SSIS' or 'PythonETL'
    record_id       VARCHAR(50),
    error_reason    VARCHAR(1000),
    raw_data        NVARCHAR(MAX),              -- Store the original bad row
    logged_at       DATETIME                    DEFAULT GETDATE()
);
GO
 
 
-- ─────────────────────────────────────────────
-- SSISCheckpoint table (for restart/checkpoint)
-- ─────────────────────────────────────────────
IF OBJECT_ID('SSISCheckpoint', 'U') IS NULL
CREATE TABLE SSISCheckpoint (
    checkpoint_id   INT             IDENTITY(1,1) PRIMARY KEY,
    package_name    VARCHAR(100),
    last_run        DATETIME,
    status          VARCHAR(20),    -- 'Success' or 'Failed'
    records_loaded  INT,
    notes           VARCHAR(500)
);
GO
 
PRINT 'SSIS support tables created.';
