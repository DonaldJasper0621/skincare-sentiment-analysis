"""
Load processed Sephora data into PostgreSQL.

Usage:
    python db/load_data.py

Requires:
    pip install psycopg2-binary psycopg2
    PostgreSQL running on localhost:5432
"""

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from pathlib import Path
import numpy as np

# ── Config ─────────────────────────────────────────────────────────────────────
DB = dict(host="localhost", port=5432, user="postgres",
          password="postgres", dbname="sephora_intelligence")
PROCESSED = Path(__file__).parent.parent / "outputs" / "processed_reviews.csv"
SCHEMA    = Path(__file__).parent / "schema.sql"

CHUNK = 50_000  # rows per insert batch


def connect():
    return psycopg2.connect(**DB)


def run_schema(conn):
    print("Creating schema...")
    with conn.cursor() as cur:
        cur.execute(SCHEMA.read_text(encoding="utf-8"))
    conn.commit()
    print("  Schema OK")


def load_df() -> pd.DataFrame:
    print("Loading processed_reviews.csv...")
    df = pd.read_csv(PROCESSED, low_memory=False)
    print(f"  {len(df):,} rows loaded")

    # Clean up types
    df["rating"]            = pd.to_numeric(df["rating"], errors="coerce").astype("Int64")
    df["is_recommended"]    = df["is_recommended"].map({1.0: True, 0.0: False, 1: True, 0: False, True: True, False: False})
    df["price_usd"]         = pd.to_numeric(df["price_usd"], errors="coerce")
    df["loves_count"]       = pd.to_numeric(df["loves_count"], errors="coerce").astype("Int64")
    df["submission_time"]   = pd.to_datetime(df["submission_time"], errors="coerce")
    df["total_pos_feedback"] = pd.to_numeric(df["total_pos_feedback_count"], errors="coerce").astype("Int64")
    df["total_neg_feedback"] = pd.to_numeric(df["total_neg_feedback_count"], errors="coerce").astype("Int64")
    df["author_id"]         = pd.to_numeric(df["author_id"], errors="coerce").astype("Int64")
    return df


def insert_brands(conn, df) -> dict:
    """Insert unique brands, return {brand_name: brand_id}."""
    print("Inserting brands...")
    brands = df["brand_name"].dropna().unique().tolist()
    rows = [(b,) for b in brands]

    with conn.cursor() as cur:
        execute_values(cur,
            "INSERT INTO brands(brand_name) VALUES %s ON CONFLICT(brand_name) DO NOTHING",
            rows)
        cur.execute("SELECT brand_id, brand_name FROM brands")
        mapping = {name: bid for bid, name in cur.fetchall()}

    conn.commit()
    print(f"  {len(mapping)} brands inserted")
    return mapping


def insert_products(conn, df, brand_map: dict):
    print("Inserting products...")
    prod_cols = ["product_id", "brand_name", "product_name",
                 "primary_category", "secondary_category",
                 "price_usd", "loves_count", "highlights"]
    products = (
        df[prod_cols]
        .drop_duplicates(subset="product_id")
        .copy()
    )
    products["brand_id"] = products["brand_name"].map(brand_map)

    rows = []
    for _, r in products.iterrows():
        rows.append((
            r["product_id"],
            int(r["brand_id"]) if pd.notna(r["brand_id"]) else None,
            r["product_name"] if pd.notna(r["product_name"]) else None,
            r["primary_category"] if pd.notna(r["primary_category"]) else None,
            r["secondary_category"] if pd.notna(r["secondary_category"]) else None,
            float(r["price_usd"]) if pd.notna(r["price_usd"]) else None,
            int(r["loves_count"]) if pd.notna(r["loves_count"]) else None,
            str(r["highlights"]) if pd.notna(r["highlights"]) else None,
        ))

    with conn.cursor() as cur:
        execute_values(cur, """
            INSERT INTO products
              (product_id, brand_id, product_name, primary_category,
               secondary_category, price_usd, loves_count, highlights)
            VALUES %s
            ON CONFLICT(product_id) DO NOTHING
        """, rows)
    conn.commit()
    print(f"  {len(rows)} products inserted")


def insert_reviews(conn, df):
    print("Inserting reviews (this takes ~1–2 min)...")
    review_cols = [
        "product_id", "author_id", "rating", "is_recommended",
        "sentiment_score", "sentiment_label", "skin_type",
        "submission_time", "year_month",
        "total_pos_feedback", "total_neg_feedback",
    ]
    total = 0
    for start in range(0, len(df), CHUNK):
        chunk = df.iloc[start:start + CHUNK][review_cols]
        rows = []
        for _, r in chunk.iterrows():
            rows.append((
                r["product_id"] if pd.notna(r["product_id"]) else None,
                int(r["author_id"]) if pd.notna(r["author_id"]) else None,
                int(r["rating"]) if pd.notna(r["rating"]) else None,
                bool(r["is_recommended"]) if r["is_recommended"] is not None and str(r["is_recommended"]) not in ("nan", "<NA>") else None,
                float(r["sentiment_score"]) if pd.notna(r["sentiment_score"]) else None,
                r["sentiment_label"] if pd.notna(r["sentiment_label"]) else None,
                r["skin_type"] if pd.notna(r["skin_type"]) else None,
                r["submission_time"].isoformat() if pd.notna(r["submission_time"]) else None,
                r["year_month"] if pd.notna(r["year_month"]) else None,
                int(r["total_pos_feedback"]) if pd.notna(r["total_pos_feedback"]) else None,
                int(r["total_neg_feedback"]) if pd.notna(r["total_neg_feedback"]) else None,
            ))
        with conn.cursor() as cur:
            execute_values(cur, """
                INSERT INTO reviews
                  (product_id, author_id, rating, is_recommended,
                   sentiment_score, sentiment_label, skin_type,
                   submission_time, year_month,
                   total_pos_feedback, total_neg_feedback)
                VALUES %s
            """, rows)
        conn.commit()
        total += len(rows)
        print(f"  {total:,} / {len(df):,} rows", end="\r")

    print(f"\n  {total:,} reviews inserted")


def verify(conn):
    print("\nVerification:")
    with conn.cursor() as cur:
        for tbl in ["brands", "products", "reviews"]:
            cur.execute(f"SELECT COUNT(*) FROM {tbl}")
            n = cur.fetchone()[0]
            print(f"  {tbl:<12} {n:>10,} rows")

        print("\nTop 5 brands by Brand Health Score:")
        cur.execute("""
            SELECT brand_name, review_count, avg_sentiment,
                   rec_rate, avg_rating, brand_health_score
            FROM brand_health
            WHERE review_count >= 1000
            ORDER BY brand_health_score DESC
            LIMIT 5
        """)
        rows = cur.fetchall()
        print(f"  {'Brand':<25} {'Reviews':>8} {'Sentiment':>10} {'Rec%':>6} {'Rating':>7} {'Score':>7}")
        for row in rows:
            print(f"  {row[0]:<25} {row[1]:>8,} {row[2]:>10.4f} {float(row[3])*100:>5.1f}% {row[4]:>7.2f} {row[5]:>7.4f}")


def main():
    conn = connect()
    try:
        run_schema(conn)
        df = load_df()
        brand_map = insert_brands(conn, df)
        insert_products(conn, df, brand_map)
        insert_reviews(conn, df)
        verify(conn)
    finally:
        conn.close()
    print("\nDone. Database: sephora_intelligence")


if __name__ == "__main__":
    main()
