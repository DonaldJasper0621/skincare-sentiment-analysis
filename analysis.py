"""
Sephora Skincare Sentiment Analysis
Full end-to-end pipeline: data loading, cleaning, sentiment scoring, insights
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import re
import warnings
from collections import Counter
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

warnings.filterwarnings("ignore")

# ── Paths ──────────────────────────────────────────────────────────────────────
DATA_DIR = "C:/WINDOWS/system32/skincare-sentiment-analysis/data/raw"
OUT_DIR  = "C:/WINDOWS/system32/skincare-sentiment-analysis/outputs"
CHARTS   = f"{OUT_DIR}/charts"

import os
os.makedirs(CHARTS, exist_ok=True)
os.makedirs(f"{OUT_DIR}", exist_ok=True)

# ── 1. Load & merge data ───────────────────────────────────────────────────────
print("Loading data...")
review_files = [
    f"{DATA_DIR}/reviews_0-250.csv",
    f"{DATA_DIR}/reviews_250-500.csv",
    f"{DATA_DIR}/reviews_500-750.csv",
    f"{DATA_DIR}/reviews_750-1250.csv",
    f"{DATA_DIR}/reviews_1250-end.csv",
]
reviews = pd.concat([pd.read_csv(f) for f in review_files], ignore_index=True)
products = pd.read_csv(f"{DATA_DIR}/product_info.csv")

# Merge on product_id
df = reviews.merge(
    products[["product_id", "ingredients", "primary_category",
              "secondary_category", "highlights", "loves_count"]],
    on="product_id", how="left"
)

print(f"  Total reviews loaded: {len(df):,}")
print(f"  Unique products: {df['product_id'].nunique():,}")
print(f"  Unique brands: {df['brand_name'].nunique():,}")

# ── 2. Clean ───────────────────────────────────────────────────────────────────
print("\nCleaning...")
df = df.dropna(subset=["review_text"])
df["review_text"] = df["review_text"].astype(str).str.strip()
df = df[df["review_text"].str.len() > 10]

# Parse date
df["submission_time"] = pd.to_datetime(df["submission_time"], errors="coerce")
df["year_month"] = df["submission_time"].dt.to_period("M")

# Normalise skin_type
df["skin_type"] = df["skin_type"].fillna("Unknown").str.strip().str.title()

# Rating as int
df["rating"] = pd.to_numeric(df["rating"], errors="coerce")

print(f"  Reviews after cleaning: {len(df):,}")

# ── 3. Sentiment scoring (VADER) ───────────────────────────────────────────────
print("\nRunning VADER sentiment analysis...")
analyzer = SentimentIntensityAnalyzer()

def score(text):
    s = analyzer.polarity_scores(str(text))
    return s["compound"]

df["sentiment_score"] = df["review_text"].apply(score)

def label(score):
    if score >= 0.05:  return "Positive"
    if score <= -0.05: return "Negative"
    return "Neutral"

df["sentiment_label"] = df["sentiment_score"].apply(label)

sent_dist = df["sentiment_label"].value_counts(normalize=True) * 100
print(f"  Positive: {sent_dist.get('Positive', 0):.1f}%")
print(f"  Neutral:  {sent_dist.get('Neutral',  0):.1f}%")
print(f"  Negative: {sent_dist.get('Negative', 0):.1f}%")

# ── 4. Ingredient extraction ───────────────────────────────────────────────────
print("\nExtracting ingredients...")

# Key ingredient list for skincare
KEY_INGREDIENTS = [
    "niacinamide", "hyaluronic acid", "retinol", "vitamin c", "spf",
    "ceramide", "peptide", "aha", "bha", "glycolic acid", "salicylic acid",
    "kojic acid", "arbutin", "zinc", "centella", "squalane", "bakuchiol",
    "collagen", "snail", "tea tree", "aloe", "rose hip", "jojoba",
    "shea butter", "glycerin", "lactic acid", "tranexamic acid", "azelaic acid"
]

def extract_ingredients(text):
    if pd.isna(text):
        return []
    text_lower = str(text).lower()
    return [ing for ing in KEY_INGREDIENTS if ing in text_lower]

df["found_ingredients"] = df["ingredients"].apply(extract_ingredients)

# Ingredient -> avg sentiment
all_ing_rows = []
for _, row in df.iterrows():
    for ing in row["found_ingredients"]:
        all_ing_rows.append({"ingredient": ing, "sentiment": row["sentiment_score"], "rating": row["rating"]})

ing_df = pd.DataFrame(all_ing_rows)

if len(ing_df) > 0:
    ing_stats = ing_df.groupby("ingredient").agg(
        avg_sentiment=("sentiment", "mean"),
        avg_rating=("rating", "mean"),
        product_count=("sentiment", "count")
    ).reset_index().sort_values("avg_sentiment", ascending=False)
    top_ingredients = ing_stats[ing_stats["product_count"] >= 20].head(15)
    print(f"  Ingredients analysed: {len(ing_stats)}")

# ── 5. Insights ────────────────────────────────────────────────────────────────
print("\nGenerating insights...")

# A) Sentiment by skin type
skin_sent = df.groupby("skin_type").agg(
    avg_sentiment=("sentiment_score", "mean"),
    review_count=("sentiment_score", "count")
).reset_index()
skin_sent = skin_sent[skin_sent["review_count"] >= 100].sort_values("avg_sentiment", ascending=False)

# B) Top brands by sentiment (min 500 reviews)
brand_sent = df.groupby("brand_name").agg(
    avg_sentiment=("sentiment_score", "mean"),
    avg_rating=("rating", "mean"),
    review_count=("sentiment_score", "count")
).reset_index()
top_brands = brand_sent[brand_sent["review_count"] >= 500].sort_values("avg_sentiment", ascending=False).head(15)

# C) Monthly trend
monthly = df.groupby("year_month").agg(
    avg_sentiment=("sentiment_score", "mean"),
    review_count=("sentiment_score", "count")
).reset_index()
monthly = monthly[monthly["review_count"] >= 50]
monthly["year_month_dt"] = monthly["year_month"].dt.to_timestamp()

# D) Category breakdown
cat_sent = df.groupby("primary_category").agg(
    avg_sentiment=("sentiment_score", "mean"),
    review_count=("sentiment_score", "count")
).reset_index()
cat_sent = cat_sent[cat_sent["review_count"] >= 200].sort_values("avg_sentiment", ascending=False)

# E) Rating vs sentiment correlation
corr = df[["rating", "sentiment_score"]].dropna().corr().iloc[0, 1]
print(f"  Rating vs Sentiment correlation: {corr:.3f}")

# ── 6. Charts ──────────────────────────────────────────────────────────────────
print("\nGenerating charts...")
sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams.update({"font.size": 11, "figure.dpi": 120})

# Chart 1 — Sentiment distribution
fig, ax = plt.subplots(figsize=(7, 4))
colors = {"Positive": "#4CAF50", "Neutral": "#FFC107", "Negative": "#F44336"}
labels = ["Positive", "Neutral", "Negative"]
sizes  = [sent_dist.get(l, 0) for l in labels]
bars = ax.bar(labels, sizes, color=[colors[l] for l in labels], width=0.5, edgecolor="white")
for bar, val in zip(bars, sizes):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
            f"{val:.1f}%", ha="center", va="bottom", fontweight="bold")
ax.set_ylabel("% of Reviews")
ax.set_title(f"Sentiment Distribution\n({len(df):,} reviews)", fontweight="bold")
ax.set_ylim(0, max(sizes) + 10)
plt.tight_layout()
plt.savefig(f"{CHARTS}/01_sentiment_distribution.png")
plt.close()

# Chart 2 — Top ingredients by sentiment
if len(ing_df) > 0 and len(top_ingredients) > 0:
    fig, ax = plt.subplots(figsize=(9, 6))
    colors_ing = ["#4CAF50" if v >= 0 else "#F44336" for v in top_ingredients["avg_sentiment"]]
    bars = ax.barh(top_ingredients["ingredient"], top_ingredients["avg_sentiment"],
                   color=colors_ing, edgecolor="white")
    ax.axvline(0, color="gray", linewidth=0.8, linestyle="--")
    ax.set_xlabel("Avg VADER Sentiment Score")
    ax.set_title("Top Ingredients by Average Sentiment Score", fontweight="bold")
    ax.invert_yaxis()
    plt.tight_layout()
    plt.savefig(f"{CHARTS}/02_ingredients_sentiment.png")
    plt.close()

# Chart 3 — Sentiment by skin type
if len(skin_sent) > 0:
    fig, ax = plt.subplots(figsize=(8, 5))
    palette = sns.color_palette("Blues_d", len(skin_sent))
    bars = ax.barh(skin_sent["skin_type"], skin_sent["avg_sentiment"],
                   color=palette, edgecolor="white")
    ax.set_xlabel("Avg Sentiment Score")
    ax.set_title("Sentiment Score by Skin Type", fontweight="bold")
    ax.invert_yaxis()
    for bar, cnt in zip(bars, skin_sent["review_count"]):
        ax.text(bar.get_width() + 0.002, bar.get_y() + bar.get_height()/2,
                f"n={cnt:,}", va="center", fontsize=9, color="gray")
    plt.tight_layout()
    plt.savefig(f"{CHARTS}/03_sentiment_by_skin_type.png")
    plt.close()

# Chart 4 — Monthly trend
if len(monthly) >= 6:
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(monthly["year_month_dt"], monthly["avg_sentiment"],
            color="#2196F3", linewidth=2, marker="o", markersize=3)
    ax.fill_between(monthly["year_month_dt"], monthly["avg_sentiment"],
                    alpha=0.15, color="#2196F3")
    ax.axhline(monthly["avg_sentiment"].mean(), color="gray",
               linestyle="--", linewidth=1, label="Overall avg")
    ax.set_ylabel("Avg Sentiment Score")
    ax.set_title("Monthly Sentiment Trend", fontweight="bold")
    ax.legend()
    plt.tight_layout()
    plt.savefig(f"{CHARTS}/04_monthly_trend.png")
    plt.close()

# Chart 5 — Top 15 brands
if len(top_brands) > 0:
    fig, ax = plt.subplots(figsize=(9, 7))
    palette = sns.color_palette("RdYlGn", len(top_brands))
    ax.barh(top_brands["brand_name"], top_brands["avg_sentiment"],
            color=palette, edgecolor="white")
    ax.set_xlabel("Avg Sentiment Score")
    ax.set_title("Top 15 Brands by Sentiment Score\n(min. 500 reviews)", fontweight="bold")
    ax.invert_yaxis()
    plt.tight_layout()
    plt.savefig(f"{CHARTS}/05_top_brands.png")
    plt.close()

# Chart 6 — Rating vs Sentiment scatter (sample)
sample = df[["rating", "sentiment_score"]].dropna().sample(min(5000, len(df)), random_state=42)
fig, ax = plt.subplots(figsize=(7, 5))
ax.scatter(sample["rating"], sample["sentiment_score"],
           alpha=0.15, color="#9C27B0", s=10)
# box avg per rating
for r in sorted(sample["rating"].unique()):
    avg = sample[sample["rating"] == r]["sentiment_score"].mean()
    ax.plot(r, avg, "o", color="black", markersize=8)
ax.set_xlabel("Star Rating")
ax.set_ylabel("VADER Sentiment Score")
ax.set_title(f"Star Rating vs Sentiment Score\n(correlation r = {corr:.3f})", fontweight="bold")
plt.tight_layout()
plt.savefig(f"{CHARTS}/06_rating_vs_sentiment.png")
plt.close()

# ── 7. Summary stats ───────────────────────────────────────────────────────────
print("\n" + "="*55)
print("SUMMARY STATS (for resume)")
print("="*55)
print(f"Total reviews analysed:     {len(df):,}")
print(f"Unique products:            {df['product_id'].nunique():,}")
print(f"Unique brands:              {df['brand_name'].nunique():,}")
print(f"Date range:                 {df['submission_time'].min().date()} -> {df['submission_time'].max().date()}")
print(f"Positive reviews:           {sent_dist.get('Positive',0):.1f}%")
print(f"Negative reviews:           {sent_dist.get('Negative',0):.1f}%")
print(f"Rating vs Sentiment corr:    r = {corr:.3f}")
if len(ing_df) > 0:
    best_ing = top_ingredients.iloc[0]
    worst_ing = top_ingredients.iloc[-1]
    print(f"Highest-sentiment ingredient: {best_ing['ingredient']} ({best_ing['avg_sentiment']:.3f})")
    print(f"Lowest-sentiment ingredient:  {worst_ing['ingredient']} ({worst_ing['avg_sentiment']:.3f})")
if len(top_brands) > 0:
    print(f"Top brand by sentiment:     {top_brands.iloc[0]['brand_name']}")

print("\nCharts saved to:", CHARTS)

# Save processed data
df.to_csv(f"{OUT_DIR}/processed_reviews.csv", index=False)
if len(ing_df) > 0:
    ing_stats.to_csv(f"{OUT_DIR}/ingredient_stats.csv", index=False)
print("Processed data saved.")
