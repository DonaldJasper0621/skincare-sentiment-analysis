"""
Export PostgreSQL query results to CSV for Power BI dashboards.
4 files → dashboard/data/powerbi/

Usage:
    python db/export_powerbi.py
"""

import psycopg2
import pandas as pd
from pathlib import Path

DB  = dict(host="localhost", port=5432, user="postgres",
           password="postgres", dbname="sephora_intelligence")
OUT = Path(__file__).parent.parent / "dashboard" / "data" / "powerbi"
OUT.mkdir(parents=True, exist_ok=True)


def q(conn, sql: str) -> pd.DataFrame:
    return pd.read_sql_query(sql, conn)


def main():
    conn = psycopg2.connect(**DB)

    # ── Page 1: Executive KPIs ──────────────────────────────────────────────
    print("Exporting Page 1: Executive KPIs...")
    kpi = q(conn, """
        SELECT
            COUNT(*)                                                       AS total_reviews,
            COUNT(DISTINCT p.brand_id)                                     AS total_brands,
            COUNT(DISTINCT r.product_id)                                   AS total_products,
            ROUND(AVG(r.sentiment_score)::NUMERIC, 4)                     AS avg_sentiment,
            ROUND(AVG(r.rating)::NUMERIC, 3)                              AS avg_rating,
            ROUND(AVG(CASE WHEN r.is_recommended THEN 1.0 ELSE 0.0 END)
                  ::NUMERIC * 100, 1)                                     AS rec_pct,
            ROUND(COUNT(CASE WHEN r.sentiment_label = 'Negative' THEN 1 END)
                  * 100.0 / COUNT(*), 2)                                  AS neg_pct
        FROM reviews r JOIN products p ON p.product_id = r.product_id
    """)
    kpi.to_csv(OUT / "kpi_summary.csv", index=False)

    monthly = q(conn, """
        SELECT year_month,
               COUNT(*) AS review_count,
               ROUND(AVG(sentiment_score)::NUMERIC, 4) AS avg_sentiment,
               ROUND(AVG(rating)::NUMERIC, 3) AS avg_rating,
               ROUND(COUNT(CASE WHEN sentiment_label='Negative' THEN 1 END)
                     * 100.0 / COUNT(*), 2) AS neg_pct
        FROM reviews WHERE year_month IS NOT NULL
        GROUP BY year_month ORDER BY year_month
    """)
    monthly.to_csv(OUT / "monthly_trend.csv", index=False)
    print(f"  kpi_summary.csv ({len(kpi)} row), monthly_trend.csv ({len(monthly)} rows)")

    # ── Page 2: Brand Benchmarking ──────────────────────────────────────────
    print("Exporting Page 2: Brand Benchmarking...")
    brands = q(conn, """
        SELECT brand_name, secondary_category, review_count,
               avg_sentiment, avg_rating,
               ROUND(rec_rate * 100, 1) AS rec_pct,
               neg_pct, brand_health_score
        FROM brand_health
        WHERE review_count >= 200
        ORDER BY brand_health_score DESC
    """)
    brands.to_csv(OUT / "brand_benchmarking.csv", index=False)
    print(f"  brand_benchmarking.csv ({len(brands)} rows)")

    # ── Page 3: Price-Value Matrix ──────────────────────────────────────────
    print("Exporting Page 3: Price-Value Matrix...")
    price = q(conn, """
        SELECT price_tier, secondary_category,
               SUM(review_count) AS review_count,
               ROUND(AVG(avg_sentiment), 4) AS avg_sentiment,
               ROUND(AVG(avg_rating), 3) AS avg_rating,
               ROUND(AVG(rec_rate) * 100, 1) AS rec_pct,
               ROUND(SUM(review_count * neg_pct) /
                     NULLIF(SUM(review_count), 0), 2) AS weighted_neg_pct
        FROM price_tier_sentiment
        GROUP BY price_tier, secondary_category
        ORDER BY price_tier, secondary_category
    """)
    price.to_csv(OUT / "price_value_matrix.csv", index=False)
    print(f"  price_value_matrix.csv ({len(price)} rows)")

    # ── Page 4: Product Risk Radar ──────────────────────────────────────────
    print("Exporting Page 4: Product Risk Radar...")
    risk = q(conn, """
        WITH ps AS (
            SELECT p.product_name, b.brand_name, p.secondary_category, p.price_usd,
                   COUNT(r.review_id) AS n,
                   ROUND(AVG(r.rating)::NUMERIC, 2) AS avg_rating,
                   ROUND(AVG(r.sentiment_score)::NUMERIC, 4) AS avg_sentiment,
                   ROUND(AVG(CASE WHEN r.is_recommended THEN 1.0 ELSE 0.0 END)::NUMERIC * 100, 1) AS rec_pct,
                   ROUND(COUNT(CASE WHEN r.sentiment_label='Negative' THEN 1 END)
                         * 100.0 / NULLIF(COUNT(r.review_id),0), 1) AS neg_pct,
                   ROUND((
                       ((AVG(r.sentiment_score)+1)/2.0)*0.35
                     + AVG(CASE WHEN r.is_recommended THEN 1.0 ELSE 0.0 END)*0.40
                     + ((AVG(r.rating)-1)/4.0)*0.25
                   )::NUMERIC, 4) AS health_score
            FROM products p JOIN brands b ON b.brand_id=p.brand_id
                            JOIN reviews r ON r.product_id=p.product_id
            GROUP BY p.product_name, b.brand_name, p.secondary_category, p.price_usd
            HAVING COUNT(r.review_id) >= 100
        )
        SELECT *,
               CASE WHEN avg_rating >= 4.2 AND rec_pct < 85 AND avg_sentiment < 0.55
                    THEN 'HIGH RISK'
                    WHEN avg_rating >= 4.0 AND rec_pct < 80
                    THEN 'WATCH'
                    ELSE 'OK'
               END AS risk_flag
        FROM ps
        ORDER BY neg_pct DESC
    """)
    risk.to_csv(OUT / "product_risk_radar.csv", index=False)
    print(f"  product_risk_radar.csv ({len(risk)} rows)")

    conn.close()
    print(f"\nAll files saved to: {OUT}")
    print("\nIn Power BI Desktop:")
    print("  Get Data → PostgreSQL")
    print("  Server: localhost  Database: sephora_intelligence")
    print("  OR: Get Data → Text/CSV → load from dashboard/data/powerbi/")


if __name__ == "__main__":
    main()
