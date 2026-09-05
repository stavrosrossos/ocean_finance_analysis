WITH card29_offers AS (
    SELECT
        application_id,
        clicked AS card29_clicked,
        apr AS card29_apr,
        likelihood AS card29_likelihood,
        apr_rank AS card29_apr_rank,
        likelihood_rank AS card29_likelihood_rank
    FROM quotes
    WHERE card_id = 'Card 29'
),

competitor_offers AS (
    SELECT
        application_id,
        card_id AS competitor_card,
        clicked AS competitor_clicked,
        apr AS competitor_apr,
        likelihood AS competitor_likelihood,
        apr_rank AS competitor_apr_rank,
        likelihood_rank AS competitor_likelihood_rank
    FROM quotes
    WHERE card_id <> 'Card 29'
),

head_to_head AS (
    SELECT
        c29.application_id,
        comp.competitor_card,

        c29.card29_clicked,
        comp.competitor_clicked,

        c29.card29_apr,
        comp.competitor_apr,

        c29.card29_likelihood,
        comp.competitor_likelihood,

        c29.card29_apr_rank,
        comp.competitor_apr_rank,

        c29.card29_likelihood_rank,
        comp.competitor_likelihood_rank

    FROM card29_offers c29

    INNER JOIN competitor_offers comp
        ON c29.application_id = comp.application_id
)

SELECT
    competitor_card,

    COUNT(*) AS applications_together,

    SUM(card29_clicked) AS card29_clicks,
    SUM(competitor_clicked) AS competitor_clicks,

    AVG(card29_clicked) AS card29_click_rate,
    AVG(competitor_clicked) AS competitor_click_rate,

    AVG(card29_clicked)
        / NULLIF(AVG(competitor_clicked), 0)
        AS click_rate_multiple,

    AVG(
        CASE
            WHEN card29_likelihood = competitor_likelihood
            THEN 1.0
            ELSE 0.0
        END
    ) AS same_likelihood_rate,

    AVG(
        CASE
            WHEN card29_likelihood > competitor_likelihood
            THEN 1.0
            ELSE 0.0
        END
    ) AS card29_higher_likelihood_rate,

    AVG(
        CASE
            WHEN card29_apr < competitor_apr
            THEN 1.0
            ELSE 0.0
        END
    ) AS card29_lower_apr_rate

FROM head_to_head

GROUP BY competitor_card

ORDER BY applications_together DESC;