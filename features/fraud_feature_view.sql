-- Fraud Alert Prioritization - Feature View
-- Purpose:
--   Build a transaction-level feature table for fraud triage modeling.
--   This mirrors the Python feature engineering pipeline and is written in
--   SQL so a data analyst can explain how the same logic would be productionized
--   in a warehouse.

CREATE OR REPLACE VIEW analytics.fraud_transaction_features AS
WITH base_transactions AS (
    SELECT
        t.transaction_id,
        t.event_ts,
        t.customer_id,
        t.merchant_id,
        t.channel,
        t.transaction_amount_usd,
        CASE WHEN t.txn_country = 'GB' THEN 'UK' ELSE t.txn_country END AS txn_country,
        t.txn_hour,
        t.device_risk_score,
        t.new_device_flag,
        t.velocity_1h,
        t.velocity_24h,
        t.geo_distance_km,
        t.merchant_risk_score,
        t.is_night_flag,
        t.alert_generated,
        t.fraud_label
    FROM raw.transactions AS t
),
customer_profile AS (
    SELECT
        c.customer_id,
        c.age,
        c.segment,
        CASE WHEN c.home_country = 'GB' THEN 'UK' ELSE c.home_country END AS home_country,
        c.digital_only,
        c.kyc_risk_band,
        c.synthetic_identity_score
    FROM raw.customers AS c
),
merchant_profile AS (
    SELECT
        m.merchant_id,
        m.merchant_category,
        m.merchant_risk_score AS merchant_profile_risk_score,
        m.channel_default
    FROM raw.merchants AS m
),
joined AS (
    SELECT
        bt.*,
        cp.age,
        cp.segment,
        cp.home_country,
        cp.digital_only,
        cp.kyc_risk_band,
        cp.synthetic_identity_score,
        mp.merchant_category,
        mp.merchant_profile_risk_score,
        mp.channel_default,
        CASE WHEN cp.customer_id IS NULL THEN 1 ELSE 0 END AS customer_profile_missing_flag,
        CASE WHEN mp.merchant_id IS NULL THEN 1 ELSE 0 END AS merchant_profile_missing_flag
    FROM base_transactions AS bt
    LEFT JOIN customer_profile AS cp
        ON bt.customer_id = cp.customer_id
    LEFT JOIN merchant_profile AS mp
        ON bt.merchant_id = mp.merchant_id
),
category_rates AS (
    SELECT
        merchant_category,
        AVG(CAST(fraud_label AS FLOAT)) AS merchant_cat_fraud_rate
    FROM joined
    WHERE merchant_category IS NOT NULL
    GROUP BY merchant_category
),
global_rate AS (
    SELECT AVG(CAST(fraud_label AS FLOAT)) AS global_fraud_rate
    FROM joined
)
SELECT
    j.transaction_id,
    j.event_ts,
    j.customer_id,
    j.merchant_id,
    j.channel,
    j.transaction_amount_usd,
    LOG(1 + GREATEST(j.transaction_amount_usd, 0)) AS amount_log1p,
    j.txn_country,
    j.txn_hour,
    SIN(2 * 3.141592653589793 * j.txn_hour / 24.0) AS hour_sin,
    COS(2 * 3.141592653589793 * j.txn_hour / 24.0) AS hour_cos,
    j.device_risk_score,
    j.new_device_flag,
    j.velocity_1h,
    j.velocity_24h,
    j.velocity_1h / NULLIF(j.velocity_24h + 1, 0) AS velocity_ratio,
    j.transaction_amount_usd / NULLIF(j.velocity_24h + 1, 0) AS amt_per_txn_24h,
    j.geo_distance_km,
    j.merchant_risk_score,
    j.merchant_profile_risk_score,
    j.merchant_category,
    COALESCE(cr.merchant_cat_fraud_rate, gr.global_fraud_rate) AS merchant_cat_fraud_rate,
    CASE WHEN j.geo_distance_km > 500 AND j.new_device_flag = 1 THEN 1 ELSE 0 END AS far_and_new,
    CASE WHEN j.home_country IS NOT NULL AND j.txn_country <> j.home_country THEN 1 ELSE 0 END AS cross_border_flag,
    CASE
        WHEN j.is_night_flag = 1
         AND j.home_country IS NOT NULL
         AND j.txn_country <> j.home_country
        THEN 1 ELSE 0
    END AS night_crossborder,
    EXTRACT(MONTH FROM j.event_ts) AS event_month,
    EXTRACT(DOW FROM j.event_ts) AS event_dayofweek,
    CASE WHEN EXTRACT(DOW FROM j.event_ts) IN (0, 6) THEN 1 ELSE 0 END AS event_is_weekend,
    j.customer_profile_missing_flag,
    j.merchant_profile_missing_flag,
    j.alert_generated,
    j.fraud_label
FROM joined AS j
CROSS JOIN global_rate AS gr
LEFT JOIN category_rates AS cr
    ON j.merchant_category = cr.merchant_category;

-- Production note:
--   The Python model uses out-of-fold target encoding on the training split.
--   In a warehouse implementation, merchant_cat_fraud_rate should be generated
--   from historical data only, never from the row currently being scored.
