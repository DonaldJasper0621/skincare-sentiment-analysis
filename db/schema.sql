-- ============================================================
-- Sephora Consumer Intelligence Platform
-- Schema: 3 normalised tables + 2 analytical views
-- ============================================================

-- ── brands ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS brands (
    brand_id   SERIAL PRIMARY KEY,
    brand_name TEXT NOT NULL UNIQUE
);

-- ── products ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS products (
    product_id        TEXT PRIMARY KEY,
    brand_id          INT  REFERENCES brands(brand_id),
    product_name      TEXT,
    primary_category  TEXT,
    secondary_category TEXT,
    price_usd         NUMERIC(8,2),
    loves_count       INT,
    highlights        TEXT        -- raw JSON-like string from Sephora
);

-- ── reviews ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS reviews (
    review_id               BIGSERIAL PRIMARY KEY,
    product_id              TEXT     REFERENCES products(product_id),
    author_id               BIGINT,
    rating                  SMALLINT,
    is_recommended          BOOLEAN,
    sentiment_score         NUMERIC(6,4),
    sentiment_label         TEXT,
    skin_type               TEXT,
    submission_time         TIMESTAMPTZ,
    year_month              TEXT,
    total_pos_feedback      INT,
    total_neg_feedback      INT
);

-- ── indexes (query performance) ───────────────────────────────
CREATE INDEX IF NOT EXISTS idx_reviews_product   ON reviews(product_id);
CREATE INDEX IF NOT EXISTS idx_reviews_sentiment ON reviews(sentiment_label);
CREATE INDEX IF NOT EXISTS idx_reviews_rating    ON reviews(rating);
CREATE INDEX IF NOT EXISTS idx_products_brand    ON products(brand_id);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(secondary_category);
CREATE INDEX IF NOT EXISTS idx_products_price    ON products(price_usd);

-- ── view: brand_health ────────────────────────────────────────
-- Composite Brand Health Score:
--   35% VADER sentiment (normalised −1→1 to 0→1)
--   40% recommendation rate
--   25% star rating (normalised 1–5 to 0–1)
CREATE OR REPLACE VIEW brand_health AS
SELECT
    b.brand_name,
    p.secondary_category,
    COUNT(r.review_id)                                          AS review_count,
    ROUND(AVG(r.sentiment_score)::NUMERIC, 4)                  AS avg_sentiment,
    ROUND(AVG(r.rating)::NUMERIC, 3)                           AS avg_rating,
    ROUND(AVG(CASE WHEN r.is_recommended THEN 1.0 ELSE 0.0 END)::NUMERIC, 3) AS rec_rate,
    ROUND(COUNT(CASE WHEN r.sentiment_label = 'Negative' THEN 1 END)
          * 100.0 / NULLIF(COUNT(r.review_id), 0), 2)          AS neg_pct,
    -- composite score
    ROUND((
        ((AVG(r.sentiment_score) + 1) / 2.0) * 0.35
      + AVG(CASE WHEN r.is_recommended THEN 1.0 ELSE 0.0 END)  * 0.40
      + ((AVG(r.rating) - 1) / 4.0)                            * 0.25
    )::NUMERIC, 4)                                             AS brand_health_score
FROM brands b
JOIN products p  ON p.brand_id   = b.brand_id
JOIN reviews r   ON r.product_id = p.product_id
GROUP BY b.brand_name, p.secondary_category;

-- ── view: price_tier_sentiment ────────────────────────────────
CREATE OR REPLACE VIEW price_tier_sentiment AS
SELECT
    CASE
        WHEN p.price_usd <  20  THEN 'Budget (<$20)'
        WHEN p.price_usd <  50  THEN 'Mid ($20–50)'
        WHEN p.price_usd < 100  THEN 'Premium ($50–100)'
        ELSE                         'Luxury ($100+)'
    END                                                         AS price_tier,
    p.secondary_category,
    COUNT(r.review_id)                                          AS review_count,
    ROUND(AVG(r.sentiment_score)::NUMERIC, 4)                  AS avg_sentiment,
    ROUND(AVG(r.rating)::NUMERIC, 3)                           AS avg_rating,
    ROUND(AVG(CASE WHEN r.is_recommended THEN 1.0 ELSE 0.0 END)::NUMERIC, 3) AS rec_rate,
    ROUND(COUNT(CASE WHEN r.sentiment_label = 'Negative' THEN 1 END)
          * 100.0 / NULLIF(COUNT(r.review_id), 0), 2)          AS neg_pct
FROM products p
JOIN reviews r ON r.product_id = p.product_id
WHERE p.price_usd IS NOT NULL
GROUP BY price_tier, p.secondary_category;
