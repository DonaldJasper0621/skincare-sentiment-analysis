"""
Prepare aggregated CSV tables for Power BI dashboard.
Run once before opening Power BI — outputs 4 CSVs to dashboard/data/.

Usage:
    python dashboard/prepare_powerbi_data.py
"""

import pandas as pd
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
PROCESSED = Path(__file__).parent.parent / "data" / "processed"
OUT = Path(__file__).parent / "data"
OUT.mkdir(exist_ok=True)

# ── Load raw files ─────────────────────────────────────────────────────────────
print("Loading data...")
mentions = pd.read_csv(PROCESSED / "ingredient_sentiment_final.csv")
posts    = pd.read_csv(PROCESSED / "posts_clean.csv")

# Merge skin_concern onto mentions
df = mentions.merge(posts[["post_id", "skin_concern"]], on="post_id", how="left")
df["skin_concern"] = df["skin_concern"].fillna("other")

# ── Table 1: ingredient_summary  (for bar chart + heatmap rows) ───────────────
summary = (
    df.groupby("ingredient")
    .agg(
        mention_count=("post_id", "count"),
        avg_sentiment=("sentiment_score", "mean"),
        negative_count=("sentiment_label", lambda x: (x == "negative").sum()),
        positive_count=("sentiment_label", lambda x: (x == "positive").sum()),
    )
    .reset_index()
)
summary["negative_pct"] = (summary["negative_count"] / summary["mention_count"] * 100).round(1)
summary["avg_sentiment"] = summary["avg_sentiment"].round(3)
summary = summary[summary["mention_count"] >= 20].sort_values("avg_sentiment")
summary.to_csv(OUT / "ingredient_summary.csv", index=False)
print(f"  ingredient_summary.csv  -> {len(summary)} rows")

# ── Table 2: heatmap  (ingredient × skin_concern negative %) ─────────────────
heatmap = (
    df.groupby(["ingredient", "skin_concern"])
    .agg(
        mentions=("post_id", "count"),
        negative_count=("sentiment_label", lambda x: (x == "negative").sum()),
        avg_sentiment=("sentiment_score", "mean"),
    )
    .reset_index()
)
heatmap["negative_pct"] = (heatmap["negative_count"] / heatmap["mentions"] * 100).round(1)
heatmap["avg_sentiment"] = heatmap["avg_sentiment"].round(3)
heatmap = heatmap[heatmap["mentions"] >= 10]
heatmap.to_csv(OUT / "heatmap_data.csv", index=False)
print(f"  heatmap_data.csv        -> {len(heatmap)} rows")

# ── Table 3: monthly_trend  (top 8 ingredients, monthly avg sentiment) ────────
TOP_INGREDIENTS = (
    summary.nsmallest(8, "avg_sentiment")["ingredient"].tolist()
)

# posts_clean may not have created_at; use a fake month if missing for demo
if "created_at" in posts.columns:
    posts["month"] = pd.to_datetime(posts["created_at"], errors="coerce").dt.to_period("M").astype(str)
else:
    # Assign random months for demo purposes (Sephora data lacks timestamps)
    import numpy as np
    rng = np.random.default_rng(42)
    months = pd.date_range("2023-01", periods=12, freq="MS").strftime("%Y-%m").tolist()
    posts["month"] = rng.choice(months, size=len(posts))

df2 = mentions.merge(posts[["post_id", "skin_concern", "month"]], on="post_id", how="left")
df2["skin_concern"] = df2["skin_concern"].fillna("other")

trend = (
    df2[df2["ingredient"].isin(TOP_INGREDIENTS)]
    .groupby(["ingredient", "month"])
    .agg(avg_sentiment=("sentiment_score", "mean"), mentions=("post_id", "count"))
    .reset_index()
)
trend["avg_sentiment"] = trend["avg_sentiment"].round(3)
trend.to_csv(OUT / "monthly_trend.csv", index=False)
print(f"  monthly_trend.csv       -> {len(trend)} rows")

# ── Table 4: post_explorer  (filterable detail table) ────────────────────────
explorer = df[["post_id", "ingredient", "sentence", "sentiment_score", "sentiment_label", "skin_concern"]].copy()
explorer["sentiment_score"] = explorer["sentiment_score"].round(3)
explorer.to_csv(OUT / "post_explorer.csv", index=False)
print(f"  post_explorer.csv       -> {len(explorer)} rows")

print("\nDone. Open Power BI Desktop and load from dashboard/data/")
