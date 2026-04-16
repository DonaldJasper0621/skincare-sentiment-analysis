-- Sentiment breakdown per ingredient × skin concern
SELECT
    im.ingredient,
    p.skin_concern,
    COUNT(*)                                AS mention_count,
    ROUND(AVG(im.sentiment_score)::numeric, 3) AS avg_sentiment,
    ROUND(
        100.0 * SUM(CASE WHEN im.sentiment_label = 'negative' THEN 1 ELSE 0 END)
        / COUNT(*), 1
    )                                       AS negative_pct
FROM ingredient_mentions im
JOIN posts p ON im.post_id = p.post_id
WHERE p.skin_concern IS NOT NULL
GROUP BY im.ingredient, p.skin_concern
HAVING COUNT(*) >= 20
ORDER BY im.ingredient, avg_sentiment ASC;
