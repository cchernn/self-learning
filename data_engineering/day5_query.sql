SELECT
    COUNT(*) AS trips_before_join,
    COUNT(pickup.locationid) AS matched_pickups,
    COUNT(dropoff.locationid) AS matched_dropoffs,
    COUNT(*) AS rows_after_join
FROM taxi.trips t
LEFT JOIN taxi.zones pickup
    ON t.pulocationid = pickup.locationid
LEFT JOIN taxi.zones dropoff
    ON t.dolocationid = dropoff.locationid;


SELECT COUNT(*)
FROM taxi.trips
WHERE pulocationid NOT IN (
    SELECT locationid
    FROM taxi.zones
);

SELECT COUNT(*)
FROM taxi.trips
WHERE pulocationid NOT IN (
    SELECT locationid
    FROM taxi.zones

    UNION ALL

    SELECT NULL
);

SELECT COUNT(*)
FROM taxi.trips t
WHERE NOT EXISTS (
    SELECT 1
    FROM taxi.zones z
    WHERE z.locationid = t.pulocationid
);


EXPLAIN (ANALYZE, BUFFERS)
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
SELECT *
FROM ranked_trips
WHERE rn <= 3
ORDER BY day, rn;

CREATE INDEX idx_trips_pickup_date_distance
ON taxi.trips (
    (lpep_pickup_datetime::DATE),
    trip_distance DESC
);
ANALYZE taxi.trips;