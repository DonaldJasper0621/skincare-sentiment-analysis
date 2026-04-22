-- ============================================================
-- Sephora Consumer Intelligence Platform
-- Analytics Queries — demonstrates SQL window functions,
-- CTEs, aggregations, and business insight extraction
-- ============================================================
-- Run against: sephora_intelligence (PostgreSQL 17)
-- ============================================================


-- ── 1. BRAND HEALTH SCORE LEADERBOARD ────────────────────────────────────────
-- Composite metric: 35% sentiment + 40% recommendation rate + 25% star rating
-- Surfaces brands that genuinely satisfy vs those that look good on stars only.
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    brand_name,
    secondary_category,
    review_count,
    avg_sentiment,
    ROUND(rec_rate * 100, 1)   AS rec_pct,
    avg_rating,
    brand_health_score
FROM brand_health
WHERE review_count >= 1000
ORDER BY brand_health_score DESC
LIMIT 20;


-- ── 2. BRAND RANKING WITHIN CATEGORY  (Window Function) ──────────────────────
-- RANK() OVER PARTITION: compare each brand to its own category peers.
-- Useful for category managers who need peer benchmarks, not global averages.
-- ─────────────────────────────────────────────────────────────────────────────
WITH ranked AS (
    SELECT
        brand_name,
        secondary_category,
        review_count,
        avg_rating,
        ROUND(rec_rate * 100, 1)  AS rec_pct,
        brand_health_score,
        RANK() OVER (
            PARTITION BY secondary_category
            ORDER BY brand_health_score DESC
        ) AS rank_in_category,
        ROUND(AVG(brand_health_score) OVER (
            PARTITION BY secondary_category
        ), 4)                     AS category_avg_score
    FROM brand_health
    WHERE review_count >= 500
)
SELECT *
FROM ranked
WHERE rank_in_category <= 3
ORDER BY secondary_category, rank_in_category;


-- ── 3. HIDDEN-RISK PRODUCTS ───────────────────────────────────────────────────
-- Products with high star ratings (≥4.2) but low sentiment + low rec rate.
-- High stars mask real dissatisfaction — actionable signal for Sephora buyers.
-- ─────────────────────────────────────────────────────────────────────────────
WITH product_stats AS (
    SELECT
        p.product_id,
        p.product_name,
        b.brand_name,
        p.secondary_category,
        p.price_usd,
        COUNT(r.review_id)                                              AS n,
        ROUND(AVG(r.rating)::NUMERIC, 2)                               AS avg_rating,
        ROUND(AVG(r.sentiment_score)::NUMERIC, 4)                      AS avg_sentiment,
        ROUND(AVG(CASE WHEN r.is_recommended THEN 1.0 ELSE 0.0 END)
              ::NUMERIC, 3)                                             AS rec_rate,
        ROUND(COUNT(CASE WHEN r.sentiment_label = 'Negative' THEN 1 END)
              * 100.0 / NULLIF(COUNT(r.review_id), 0), 1)              AS neg_pct
    FROM products p
    JOIN brands  b ON b.brand_id   = p.brand_id
    JOIN reviews r ON r.product_id = p.product_id
    GROUP BY p.product_id, p.product_name, b.brand_name,
             p.secondary_category, p.price_usd
    HAVING COUNT(r.review_id) >= 200
)
SELECT
    product_name,
    brand_name,
    secondary_category,
    price_usd,
    n           AS review_count,
    avg_rating,
    avg_sentiment,
    ROUND(rec_rate * 100, 1) AS rec_pct,
    neg_pct
FROM product_stats
WHERE avg_rating   >= 4.2
  AND avg_sentiment < 0.55
  AND rec_rate      < 0.85
ORDER BY neg_pct DESC
LIMIT 15;


-- ── 4. PRICE-TIER SENTIMENT GAP  (Key Resume Finding) ────────────────────────
-- Budget products (<$20) generate 38% more negative reviews than luxury ($100+)
-- despite near-identical star averages (4.26 vs 4.27).
-- Star ratings systematically mask price-tier dissatisfaction.
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    price_tier,
    SUM(review_count)                                   AS total_reviews,
    ROUND(AVG(avg_sentiment), 4)                        AS avg_sentiment,
    ROUND(AVG(avg_rating), 3)                           AS avg_rating,
    ROUND(AVG(rec_rate) * 100, 1)                       AS rec_pct,
    ROUND(SUM(review_count * neg_pct) /
          NULLIF(SUM(review_count), 0), 2)              AS weighted_neg_pct
FROM price_tier_sentiment
GROUP BY price_tier
ORDER BY
    CASE price_tier
        WHEN 'Budget (<$20)'     THEN 1
        WHEN 'Mid ($20–50)'      THEN 2
        WHEN 'Premium ($50–100)' THEN 3
        ELSE 4
    END;


-- ── 5. SENTIMENT TREND OVER TIME  (Time-Series) ───────────────────────────────
-- Monthly avg sentiment across all reviews — identifies macro trend shifts.
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    year_month,
    COUNT(*)                                            AS review_count,
    ROUND(AVG(sentiment_score)::NUMERIC, 4)            AS avg_sentiment,
    ROUND(AVG(rating)::NUMERIC, 3)                     AS avg_rating,
    ROUND(COUNT(CASE WHEN sentiment_label = 'Negative' THEN 1 END)
          * 100.0 / COUNT(*), 2)                       AS neg_pct,
    -- rolling 3-month average
    ROUND(AVG(AVG(sentiment_score)::NUMERIC) OVER (
        ORDER BY year_month
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ), 4)                                              AS rolling_3m_sentiment
FROM reviews
WHERE year_month IS NOT NULL
GROUP BY year_month
ORDER BY year_month;


-- ── 6. SKIN TYPE SENTIMENT BREAKDOWN ─────────────────────────────────────────
-- Which skin types report more dissatisfaction?
-- Useful for product development and targeted marketing.
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    r.skin_type,
    COUNT(*)                                            AS review_count,
    ROUND(AVG(r.sentiment_score)::NUMERIC, 4)          AS avg_sentiment,
    ROUND(AVG(r.rating)::NUMERIC, 3)                   AS avg_rating,
    ROUND(COUNT(CASE WHEN r.sentiment_label = 'Negative' THEN 1 END)
          * 100.0 / COUNT(*), 2)                       AS neg_pct,
    ROUND(AVG(CASE WHEN r.is_recommended THEN 1.0 ELSE 0.0 END)
          ::NUMERIC * 100, 1)                          AS rec_pct
FROM reviews r
WHERE r.skin_type IS NOT NULL
  AND r.skin_type != 'Unknown'
GROUP BY r.skin_type
HAVING COUNT(*) >= 5000
ORDER BY avg_sentiment;


-- ── 7. RECOMMENDATION RATE VS STAR RATING DIVERGENCE  (Percentile) ──────────
-- Brands where recommendation intent diverges most from star rating.
-- A brand with 4.5 stars but 70% recommendation rate is over-relying on scores.
-- ─────────────────────────────────────────────────────────────────────────────
WITH brand_summary AS (
    SELECT
        b.brand_name,
        COUNT(r.review_id)                                              AS n,
        ROUND(AVG(r.rating)::NUMERIC, 3)                               AS avg_rating,
        ROUND(AVG(CASE WHEN r.is_recommended THEN 1.0 ELSE 0.0 END)
              ::NUMERIC, 3)                                             AS rec_rate
    FROM brands  b
    JOIN products p ON p.brand_id   = b.brand_id
    JOIN reviews  r ON r.product_id = p.product_id
    GROUP BY b.brand_name
    HAVING COUNT(r.review_id) >= 1000
),
divergence AS (
    SELECT *,
        -- normalise both to 0–1
        (avg_rating - 1) / 4.0                         AS norm_rating,
        rec_rate                                        AS norm_rec,
        -- gap: positive = rating inflated vs recommendation
        ROUND(((avg_rating - 1) / 4.0 - rec_rate)::NUMERIC, 4) AS rating_rec_gap
    FROM brand_summary
)
SELECT brand_name, n, avg_rating,
       ROUND(rec_rate * 100, 1) AS rec_pct,
       rating_rec_gap,
       NTILE(4) OVER (ORDER BY rating_rec_gap DESC) AS risk_quartile
FROM divergence
ORDER BY rating_rec_gap DESC
LIMIT 20;
