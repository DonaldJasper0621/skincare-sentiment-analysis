# Sephora Skincare Sentiment Analysis

NLP sentiment analysis of 1.09M+ Sephora customer reviews — identifying ingredient performance, brand rankings, and skin-type patterns across a 15-year dataset.

**Live Dashboard** → [donaldjsu.github.io/skincare-sentiment-analysis](https://donaldjsu.github.io/skincare-sentiment-analysis/dashboard/)

---

## Key Findings

| Metric | Result |
|---|---|
| Reviews analysed | 1,092,966 |
| Unique products | 2,351 |
| Brands tracked | 142 |
| Date range | 2008 – 2023 |
| Positive sentiment rate | **89.6%** |
| Rating ↔ Sentiment correlation | **r = 0.45** |
| Highest-sentiment ingredient | **AHA** (score: 0.795) |
| Top brand by sentiment | **Benefit Cosmetics** |

---

## Project Structure

```
skincare-sentiment-analysis/
├── data/
│   └── raw/                    # Kaggle source CSVs (not committed)
├── outputs/
│   ├── charts/                 # 6 generated visualisations
│   └── processed_reviews.csv   # Cleaned + scored dataset
├── dashboard/
│   └── index.html              # Interactive results dashboard
├── sql/
│   └── queries/                # Analytical SQL queries
├── analysis.py                 # Full end-to-end pipeline
├── requirements.txt
└── .env.example
```

---

## Methodology

### 1. Data Collection
- Source: [Sephora Products and Skincare Reviews](https://www.kaggle.com/datasets/nadyinky/sephora-products-and-skincare-reviews) via Kaggle API
- 5 review CSV files merged with product metadata (ingredients, categories)

### 2. Data Cleaning
- Dropped null/empty reviews and reviews under 10 characters
- Normalised skin type labels and parsed submission dates
- Merged review data with product ingredient lists

### 3. Sentiment Scoring
- Used **VADER** (Valence Aware Dictionary and sEntiment Reasoner) — a lexicon-based NLP model optimised for social/consumer text
- Compound score threshold: ≥ 0.05 = Positive, ≤ -0.05 = Negative, else Neutral

### 4. Ingredient Extraction
- Matched 28 key skincare ingredients (AHA, BHA, retinol, niacinamide, etc.) against product ingredient lists using keyword search
- Aggregated sentiment and star rating by ingredient

### 5. Analysis & Visualisation
- Sentiment by skin type, brand, category, and time
- Scatter analysis of star rating vs NLP sentiment score (r = 0.45)
- Monthly trend over 15-year period

---

## Charts

| # | Chart | Insight |
|---|---|---|
| 1 | Sentiment Distribution | 89.6% positive, 7.7% negative |
| 2 | Ingredients by Sentiment | AHA ranks highest; lactic acid lowest |
| 3 | Sentiment by Skin Type | Dry/combination most positive; oily most critical |
| 4 | Monthly Trend (2008–2023) | Consistently high, dips at trend-shift periods |
| 5 | Top 15 Brands | Benefit Cosmetics leads among 500+ review brands |
| 6 | Rating vs Sentiment Scatter | r = 0.45 — NLP captures nuance beyond star ratings |

---

## Setup

```bash
# Clone
git clone https://github.com/donaldjsu/skincare-sentiment-analysis.git
cd skincare-sentiment-analysis

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Add your Kaggle credentials to .env

# Download data
kaggle datasets download nadyinky/sephora-products-and-skincare-reviews \
  --unzip -p data/raw/

# Run full pipeline
python analysis.py
```

---

## Tools & Stack

- **Python 3.12** — data pipeline
- **Pandas** — data loading, cleaning, aggregation
- **VADER Sentiment** — NLP scoring
- **Matplotlib / Seaborn** — visualisation
- **Kaggle API** — data sourcing

---

## Dataset Credit

Nadya Tatarnikova — [Sephora Products and Skincare Reviews](https://www.kaggle.com/datasets/nadyinky/sephora-products-and-skincare-reviews) · CC BY 4.0
