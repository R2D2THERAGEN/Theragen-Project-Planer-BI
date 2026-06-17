-- db/26_sales_distributor.sql  (sub-stage F, F-T1)
-- Field-sales / distributor network -- Theragen's GTM org (Region -> RSM ->
-- Marketing Rep -> Distributor). A new subject area in the same model, standalone
-- (no relationship to Project). Additive, idempotent; applied via inline psycopg;
-- appended to the load_postgres.py DDL list. Loaded by an Excel import (F-T3).

CREATE SCHEMA IF NOT EXISTS sales;

CREATE TABLE IF NOT EXISTS sales.distributor (
    distributor_id  UUID PRIMARY KEY,
    name            VARCHAR NOT NULL,
    sales_type      VARCHAR,                       -- Distributor / Direct
    region          VARCHAR,                       -- SE / MW / SW / NE / Unknown
    rsm             VARCHAR,                        -- canonicalized Regional Sales Manager
    marketing_rep   VARCHAR,
    status_raw      VARCHAR,                        -- the messy source value, preserved
    status          VARCHAR,                        -- normalized: Active/Terminated/Inactive/Pending/Unknown
    active          BOOLEAN NOT NULL DEFAULT FALSE,
    products        VARCHAR,
    email           VARCHAR,
    external_ref    VARCHAR UNIQUE                   -- the import key (one row per distinct distributor)
);

CREATE OR REPLACE VIEW bi.distributor AS
SELECT
    distributor_id,
    name,
    sales_type,
    region,
    rsm,
    marketing_rep,
    status,
    active,
    products,
    email
FROM sales.distributor;
