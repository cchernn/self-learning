WITH zone_trips AS (
    SELECT
        z.borough,
        z.zone,
        COUNT(*) AS trip_count
    FROM taxi.trips t
    JOIN taxi.zones z
        ON t.pulocationid = z.locationid
    GROUP BY
        z.borough,
        z.zone
)
SELECT
    borough,
    zone,
    trip_count,
    RANK() OVER (
        PARTITION BY borough
        ORDER BY trip_count DESC
    ) AS zone_rank
FROM zone_trips
ORDER BY borough, zone_rank;

WITH ranked_trips AS (
    SELECT
        lpep_pickup_datetime::DATE AS day,
        pulocationid,
        dolocationid,
        trip_distance,
        fare_amount,
        ROW_NUMBER() OVER (
            PARTITION BY lpep_pickup_datetime::DATE
            ORDER BY trip_distance DESC
        ) AS rn
    FROM taxi.trips
)
SELECT
    day,
    pulocationid,
    dolocationid,
    trip_distance,
    fare_amount,
    rn
FROM ranked_trips
WHERE rn <= 3
ORDER BY day, rn;

WITH daily_revenue AS (
    SELECT
        lpep_pickup_datetime::DATE AS day,
        SUM(total_amount) AS daily_revenue
    FROM taxi.trips
    GROUP BY lpep_pickup_datetime::DATE
)
SELECT
    day,
    ROUND(daily_revenue::NUMERIC, 2) AS daily_revenue,
    ROUND(
        AVG(daily_revenue) OVER (
            ORDER BY day
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        )::NUMERIC,
        2
    ) AS moving_avg_7d
FROM daily_revenue
ORDER BY day;

WITH daily_trips AS (
    SELECT
        lpep_pickup_datetime::DATE AS day,
        COUNT(*) AS trip_count
    FROM taxi.trips
    GROUP BY lpep_pickup_datetime::DATE
),
trip_comparison AS (
    SELECT
        day,
        trip_count,
        LAG(trip_count) OVER (
            ORDER BY day
        ) AS previous_day_trips
    FROM daily_trips
)
SELECT
    day,
    trip_count,
    previous_day_trips,
    trip_count - previous_day_trips AS trip_count_change,
    ROUND(
        (
            (trip_count - previous_day_trips)::NUMERIC
            / NULLIF(previous_day_trips, 0)
        ) * 100,
        2
    ) AS percentage_change
FROM trip_comparison
ORDER BY day;