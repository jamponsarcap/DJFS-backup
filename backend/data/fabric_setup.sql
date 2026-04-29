-- ============================================================
-- RM Insights – Fabric SQL Database Setup
-- Database: rm-insight-sql-db
-- Run this entire script in the Fabric SQL query editor
-- ============================================================


-- ── 1. CLIENTS ───────────────────────────────────────────────
CREATE TABLE dbo.clients (
    client_id    VARCHAR(20)  NOT NULL PRIMARY KEY,
    name         VARCHAR(100) NOT NULL,
    rm_name      VARCHAR(100) NOT NULL,
    last_review  DATE         NOT NULL,
    risk_profile VARCHAR(20)  NOT NULL   -- Balanced | Growth | Conservative
);

INSERT INTO dbo.clients VALUES
('cli_001', 'Sarah Chen',            'James Hargreaves', '2025-10-14', 'Balanced'),
('cli_002', 'Thompson Family Trust', 'Priya Mehta',      '2025-11-22', 'Growth'),
('cli_003', 'Alford Capital Ltd',    'James Hargreaves', '2025-09-05', 'Conservative');


-- ── 2. ACCOUNTS ──────────────────────────────────────────────
-- Each client can have multiple accounts (personal / joint / corporate)
CREATE TABLE dbo.accounts (
    account_id   VARCHAR(20)   NOT NULL PRIMARY KEY,
    client_id    VARCHAR(20)   NOT NULL REFERENCES dbo.clients(client_id),
    account_type VARCHAR(20)   NOT NULL,   -- personal | joint | corporate
    account_name VARCHAR(100)  NOT NULL,
    balance      DECIMAL(18,2) NOT NULL,
    currency     CHAR(3)       NOT NULL DEFAULT 'GBP'
);

-- Sarah Chen
INSERT INTO dbo.accounts VALUES
('acc_001a', 'cli_001', 'personal', 'ISA Portfolio',     542300.00, 'GBP'),
('acc_001b', 'cli_001', 'personal', 'General Investment', 489150.00, 'GBP'),
('acc_001c', 'cli_001', 'joint',    'Joint Savings',      253300.00, 'GBP');

-- Thompson Family Trust
INSERT INTO dbo.accounts VALUES
('acc_002a', 'cli_002', 'personal',  'Discretionary Portfolio', 2110500.00, 'GBP'),
('acc_002b', 'cli_002', 'joint',     'Family Trust Account',    1200620.00, 'GBP'),
('acc_002c', 'cli_002', 'corporate', 'Thompson Holdings Ltd',    559000.00, 'GBP');

-- Alford Capital Ltd
INSERT INTO dbo.accounts VALUES
('acc_003a', 'cli_003', 'corporate', 'Operating Account', 2100000.00, 'GBP'),
('acc_003b', 'cli_003', 'corporate', 'Reserve Portfolio', 4980000.00, 'GBP'),
('acc_003c', 'cli_003', 'corporate', 'Capital Reserve',   1352000.00, 'GBP');


-- ── 3. HOLDINGS ──────────────────────────────────────────────
-- One row per position per client.
-- current_price is updated by the market data service; cost_basis is static.
CREATE TABLE dbo.holdings (
    holding_id     INT           NOT NULL IDENTITY(1,1) PRIMARY KEY,
    client_id      VARCHAR(20)   NOT NULL REFERENCES dbo.clients(client_id),
    symbol         VARCHAR(10)   NOT NULL,
    name           VARCHAR(100)  NOT NULL,
    asset_class    VARCHAR(20)   NOT NULL,   -- equity | fixed_income | cash | alternatives
    quantity       DECIMAL(18,4) NOT NULL,
    current_price  DECIMAL(18,4) NOT NULL,
    market_value   DECIMAL(18,2) NOT NULL,
    cost_basis     DECIMAL(18,2) NOT NULL,
    gain_loss      DECIMAL(18,2) NOT NULL,
    gain_loss_pct  DECIMAL(8,2)  NOT NULL,
    weight         DECIMAL(6,2)  NOT NULL    -- % of total portfolio
);

-- Sarah Chen holdings
INSERT INTO dbo.holdings (client_id, symbol, name, asset_class, quantity, current_price, market_value, cost_basis, gain_loss, gain_loss_pct, weight) VALUES
('cli_001', 'AAPL',  'Apple Inc.',         'equity',       480,    189.3000,  90864.00,  72000.00,  18864.00,  26.20,  7.07),
('cli_001', 'MSFT',  'Microsoft Corp.',    'equity',       320,    415.2000, 132864.00, 110000.00,  22864.00,  20.80, 10.34),
('cli_001', 'VOD',   'Vodafone Group plc', 'equity',     12000,      0.7400,   8880.00,  14400.00,  -5520.00, -38.30,  0.69),
('cli_001', 'UK10Y', 'UK Gilts 10Y',       'fixed_income', 350,    982.5000, 343875.00, 350000.00,  -6125.00,  -1.75, 26.77),
('cli_001', 'CASH',  'Cash & Equivalents', 'cash',           1, 192300.0000, 192300.00, 192300.00,      0.00,   0.00, 14.97),
('cli_001', 'GOLD',  'iShares Gold ETF',   'alternatives', 2800,    162.0000, 453600.00, 380000.00,  73600.00,  19.40, 35.30),
('cli_001', 'REUK',  'UK REIT Fund',       'alternatives',  820,     76.1000,  62402.00,  55000.00,   7402.00,  13.50,  4.86);

-- Thompson Family Trust holdings
INSERT INTO dbo.holdings (client_id, symbol, name, asset_class, quantity, current_price, market_value, cost_basis, gain_loss, gain_loss_pct, weight) VALUES
('cli_002', 'NVDA',  'NVIDIA Corp.',        'equity',        1200,   875.4000, 1050480.00,  540000.00,  510480.00,  94.50, 27.14),
('cli_002', 'AMZN',  'Amazon.com Inc.',     'equity',        1800,   185.2000,  333360.00,  270000.00,   63360.00,  23.50,  8.61),
('cli_002', 'GSK',   'GSK plc',             'equity',       15000,    16.8200,  252300.00,  225000.00,   27300.00,  12.10,  6.52),
('cli_002', 'TPVG',  'TriplePoint Ventures','alternatives',  4200,    98.5000,  413700.00,  350000.00,   63700.00,  18.20, 10.69),
('cli_002', 'US30Y', 'US Treasury 30Y',     'fixed_income',   800,   965.1000,  772080.00,  800000.00,  -27920.00,  -3.49, 19.95),
('cli_002', 'CASH',  'Cash & Equivalents',  'cash',             1, 414200.0000,  414200.00,  414200.00,       0.00,   0.00, 10.70),
('cli_002', 'INTU',  'Intuit Inc.',         'equity',         780,   634.5000,  494910.00,  390000.00,  104910.00,  26.90, 12.79),
('cli_002', 'PRIV',  'Blackstone PE Fund',  'alternatives',     1, 139090.0000,  139090.00,  120000.00,   19090.00,  15.90,  3.60);

-- Alford Capital Ltd holdings
INSERT INTO dbo.holdings (client_id, symbol, name, asset_class, quantity, current_price, market_value, cost_basis, gain_loss, gain_loss_pct, weight) VALUES
('cli_003', 'UK5Y',  'UK Gilts 5Y',           'fixed_income', 2500,   978.2000, 2445500.00, 2500000.00,  -54500.00,  -2.18, 29.00),
('cli_003', 'EU5Y',  'EUR Corp Bond ETF',      'fixed_income', 1200,   104.5000, 1254000.00, 1200000.00,   54000.00,   4.50, 14.87),
('cli_003', 'CASH',  'GBP Cash Deposits',      'cash',            1, 2352000.0000, 2352000.00, 2352000.00,      0.00,   0.00, 27.90),
('cli_003', 'MMKT',  'Sterling Money Market',  'cash',         9500,   105.2000,  999400.00,  950000.00,   49400.00,   5.20, 11.85),
('cli_003', 'SHRY',  'iShares Short Gilt',     'fixed_income', 5400,    73.4000,  396360.00,  378000.00,   18360.00,   4.86,  4.70),
('cli_003', 'INFRA', 'UK Infrastructure Fund', 'alternatives', 3800,   254.1000,  965580.00,  912000.00,   53580.00,   5.87, 11.45),
('cli_003', 'BRKR',  'Barclays Equity',        'equity',       2100,     9.5000,   19950.00,   18000.00,    1950.00,  10.80,  0.23);


-- ── 4. PERFORMANCE ───────────────────────────────────────────
-- Monthly portfolio value vs benchmark, 13 months (Jan 2024 – Jan 2025)
CREATE TABLE dbo.performance (
    perf_id          INT           NOT NULL IDENTITY(1,1) PRIMARY KEY,
    client_id        VARCHAR(20)   NOT NULL REFERENCES dbo.clients(client_id),
    period_date      DATE          NOT NULL,
    portfolio_value  DECIMAL(18,2) NOT NULL,
    benchmark_value  DECIMAL(18,2) NOT NULL
);

-- Sarah Chen – starts ~1.1M, ends ~1.28M
INSERT INTO dbo.performance (client_id, period_date, portfolio_value, benchmark_value) VALUES
('cli_001', '2024-01-01', 1112400.00, 1086800.00),
('cli_001', '2024-02-01', 1098750.00, 1079200.00),
('cli_001', '2024-03-01', 1134200.00, 1094500.00),
('cli_001', '2024-04-01', 1118600.00, 1088300.00),
('cli_001', '2024-05-01', 1152300.00, 1103700.00),
('cli_001', '2024-06-01', 1169800.00, 1116200.00),
('cli_001', '2024-07-01', 1188500.00, 1128400.00),
('cli_001', '2024-08-01', 1175200.00, 1121900.00),
('cli_001', '2024-09-01', 1203700.00, 1138600.00),
('cli_001', '2024-10-01', 1228400.00, 1152300.00),
('cli_001', '2024-11-01', 1219600.00, 1147800.00),
('cli_001', '2024-12-01', 1251900.00, 1163400.00),
('cli_001', '2025-01-01', 1284750.00, 1178200.00);

-- Thompson Family Trust – starts ~3.0M, ends ~3.87M
INSERT INTO dbo.performance (client_id, period_date, portfolio_value, benchmark_value) VALUES
('cli_002', '2024-01-01', 3042000.00, 2985600.00),
('cli_002', '2024-02-01', 3118500.00, 3022400.00),
('cli_002', '2024-03-01', 3089200.00, 3008700.00),
('cli_002', '2024-04-01', 3215800.00, 3078900.00),
('cli_002', '2024-05-01', 3302400.00, 3124600.00),
('cli_002', '2024-06-01', 3388100.00, 3167300.00),
('cli_002', '2024-07-01', 3491600.00, 3221800.00),
('cli_002', '2024-08-01', 3467300.00, 3208400.00),
('cli_002', '2024-09-01', 3582900.00, 3274100.00),
('cli_002', '2024-10-01', 3694200.00, 3318600.00),
('cli_002', '2024-11-01', 3751800.00, 3349200.00),
('cli_002', '2024-12-01', 3812400.00, 3378500.00),
('cli_002', '2025-01-01', 3870120.00, 3401700.00);

-- Alford Capital Ltd – starts ~8.0M, ends ~8.43M (conservative, low volatility)
INSERT INTO dbo.performance (client_id, period_date, portfolio_value, benchmark_value) VALUES
('cli_003', '2024-01-01', 8024000.00, 7948000.00),
('cli_003', '2024-02-01', 8048200.00, 7971400.00),
('cli_003', '2024-03-01', 8019600.00, 7955800.00),
('cli_003', '2024-04-01', 8072300.00, 7994200.00),
('cli_003', '2024-05-01', 8118700.00, 8028600.00),
('cli_003', '2024-06-01', 8156400.00, 8054300.00),
('cli_003', '2024-07-01', 8198200.00, 8082700.00),
('cli_003', '2024-08-01', 8184600.00, 8071900.00),
('cli_003', '2024-09-01', 8241800.00, 8108400.00),
('cli_003', '2024-10-01', 8318500.00, 8152300.00),
('cli_003', '2024-11-01', 8362100.00, 8174800.00),
('cli_003', '2024-12-01', 8398700.00, 8196200.00),
('cli_003', '2025-01-01', 8432000.00, 8218600.00);


-- ── 5. CASH_FLOWS ────────────────────────────────────────────
-- Monthly inflows, outflows, and net for the calendar year 2024
CREATE TABLE dbo.cash_flows (
    cf_id      INT           NOT NULL IDENTITY(1,1) PRIMARY KEY,
    client_id  VARCHAR(20)   NOT NULL REFERENCES dbo.clients(client_id),
    year       INT           NOT NULL,
    month_num  INT           NOT NULL,   -- 1–12
    month_label VARCHAR(3)   NOT NULL,   -- Jan, Feb, ...
    inflow     DECIMAL(18,2) NOT NULL,
    outflow    DECIMAL(18,2) NOT NULL,
    net        DECIMAL(18,2) NOT NULL
);

-- Sarah Chen cash flows
INSERT INTO dbo.cash_flows (client_id, year, month_num, month_label, inflow, outflow, net) VALUES
('cli_001', 2024,  1, 'Jan', 32400.00, 14200.00, 18200.00),
('cli_001', 2024,  2, 'Feb', 28750.00, 12800.00, 15950.00),
('cli_001', 2024,  3, 'Mar', 41200.00, 19800.00, 21400.00),
('cli_001', 2024,  4, 'Apr', 25600.00, 11400.00, 14200.00),
('cli_001', 2024,  5, 'May', 38900.00, 16700.00, 22200.00),
('cli_001', 2024,  6, 'Jun', 22100.00, 10200.00, 11900.00),
('cli_001', 2024,  7, 'Jul', 44500.00, 21300.00, 23200.00),
('cli_001', 2024,  8, 'Aug', 19800.00,  9400.00, 10400.00),
('cli_001', 2024,  9, 'Sep', 35200.00, 15600.00, 19600.00),
('cli_001', 2024, 10, 'Oct', 29700.00, 13100.00, 16600.00),
('cli_001', 2024, 11, 'Nov', 42800.00, 18900.00, 23900.00),
('cli_001', 2024, 12, 'Dec', 31500.00, 14800.00, 16700.00);

-- Thompson Family Trust cash flows
INSERT INTO dbo.cash_flows (client_id, year, month_num, month_label, inflow, outflow, net) VALUES
('cli_002', 2024,  1, 'Jan', 98400.00, 42100.00, 56300.00),
('cli_002', 2024,  2, 'Feb', 75200.00, 38600.00, 36600.00),
('cli_002', 2024,  3, 'Mar', 112800.00, 54200.00, 58600.00),
('cli_002', 2024,  4, 'Apr', 68500.00, 31400.00, 37100.00),
('cli_002', 2024,  5, 'May', 124600.00, 58900.00, 65700.00),
('cli_002', 2024,  6, 'Jun', 59300.00, 28700.00, 30600.00),
('cli_002', 2024,  7, 'Jul', 138200.00, 67400.00, 70800.00),
('cli_002', 2024,  8, 'Aug', 52100.00, 24800.00, 27300.00),
('cli_002', 2024,  9, 'Sep', 109700.00, 48300.00, 61400.00),
('cli_002', 2024, 10, 'Oct', 88600.00, 41200.00, 47400.00),
('cli_002', 2024, 11, 'Nov', 131400.00, 59800.00, 71600.00),
('cli_002', 2024, 12, 'Dec', 94200.00, 43600.00, 50600.00);

-- Alford Capital Ltd cash flows
INSERT INTO dbo.cash_flows (client_id, year, month_num, month_label, inflow, outflow, net) VALUES
('cli_003', 2024,  1, 'Jan', 284000.00, 198000.00,  86000.00),
('cli_003', 2024,  2, 'Feb', 196500.00, 142300.00,  54200.00),
('cli_003', 2024,  3, 'Mar', 321800.00, 241600.00,  80200.00),
('cli_003', 2024,  4, 'Apr', 178200.00, 134700.00,  43500.00),
('cli_003', 2024,  5, 'May', 298400.00, 219800.00,  78600.00),
('cli_003', 2024,  6, 'Jun', 154600.00, 118200.00,  36400.00),
('cli_003', 2024,  7, 'Jul', 342100.00, 258400.00,  83700.00),
('cli_003', 2024,  8, 'Aug', 142800.00, 109600.00,  33200.00),
('cli_003', 2024,  9, 'Sep', 287600.00, 214300.00,  73300.00),
('cli_003', 2024, 10, 'Oct', 231400.00, 178900.00,  52500.00),
('cli_003', 2024, 11, 'Nov', 318700.00, 241200.00,  77500.00),
('cli_003', 2024, 12, 'Dec', 264300.00, 196800.00,  67500.00);


-- ── 6. RISK_ALERTS ───────────────────────────────────────────
CREATE TABLE dbo.risk_alerts (
    alert_id   INT          NOT NULL IDENTITY(1,1) PRIMARY KEY,
    client_id  VARCHAR(20)  NOT NULL REFERENCES dbo.clients(client_id),
    level      VARCHAR(10)  NOT NULL,   -- high | medium | low
    category   VARCHAR(50)  NOT NULL,
    message    VARCHAR(500) NOT NULL
);

INSERT INTO dbo.risk_alerts (client_id, level, category, message) VALUES
('cli_001', 'medium', 'Concentration', 'Fixed income allocation (26.8%) is below target range of 30–40% for a Balanced profile.'),
('cli_001', 'low',    'Currency',      '3.2% USD exposure without currency hedge in place.'),

('cli_002', 'high',   'Concentration', 'NVIDIA represents 27.1% of total portfolio – exceeds 20% single-stock limit for Growth profile.'),
('cli_002', 'medium', 'Liquidity',     'Private equity allocation (14.3%) locks capital until 2027 fund maturity.'),
('cli_002', 'low',    'Interest Rate', 'Long-duration US Treasuries are sensitive to Fed rate decisions (current duration: 24y).'),

('cli_003', 'low',    'Yield',         'Portfolio yield (3.8%) is below inflation (4.1%); real returns are currently negative.'),
('cli_003', 'low',    'Mandate',       'Equity exposure (0.23%) is minimal – confirm this aligns with updated investment mandate.');


-- ── Verify all tables ─────────────────────────────────────────
SELECT 'clients'     AS tbl, COUNT(*) AS rows FROM dbo.clients     UNION ALL
SELECT 'accounts',          COUNT(*)          FROM dbo.accounts     UNION ALL
SELECT 'holdings',          COUNT(*)          FROM dbo.holdings     UNION ALL
SELECT 'performance',       COUNT(*)          FROM dbo.performance  UNION ALL
SELECT 'cash_flows',        COUNT(*)          FROM dbo.cash_flows   UNION ALL
SELECT 'risk_alerts',       COUNT(*)          FROM dbo.risk_alerts;
