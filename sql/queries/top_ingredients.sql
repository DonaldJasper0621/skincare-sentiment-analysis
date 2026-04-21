-- Top 10 most negatively-mentioned ingredients (min 50 mentions)
SELECT
    ingredient,
    COUNT(*)                                                              AS mention_count,
    ROUND(AVG(sentiment_score)::numeric, 3)                              AS avg_sentiment,
    ROUND(
        100.0 * SUM(CASE WHEN sentiment_label = 'negative' THEN 1 ELSE 0 END)
        / COUNT(*), 1
    )                                                                     AS negative_pct,
    ROUND(
        100.0 * SUM(CASE WHEN sentiment_label = 'positive' THEN 1 ELSE 0 END)
        / COUNT(*), 1
    )                                                                     AS positive_pct
FROM ingredient_mentions
GROUP BY ingredient
HAVING COUNT(*) >= 50
ORDER BY avg_sentiment ASC
LIMIT 10;
