-- Q1 trips with pickup and dropoff zones
SELECT 
    t.*,
    zpu.zone AS pickup_zone, 
    zdo.zone AS dropoff_zone
FROM taxi.trips t
LEFT JOIN taxi.zones zpu ON t.pulocationid = zpu.locationid
LEFT JOIN taxi.zones zdo ON t.dolocationid = zdo.locationid;

-- Q2 trips count by pickup borough
SELECT
    z.borough AS pickup_borough,
    COUNT(*) AS trip_count
FROM taxi.trips t
LEFT JOIN taxi.zones z ON t.pulocationid = z.locationid
GROUP BY z.borough;

-- Q3 zones with no trips
SELECT
    z.zone AS zone
FROM taxi.zones z
LEFT JOIN taxi.trips t ON t.pulocationid = z.locationid
WHERE t.pulocationid IS NULL
GROUP BY z.zone;

-- Q4 trips with missing pickup or dropoff zones
SELECT 
    t.*
FROM taxi.trips t
LEFT JOIN taxi.zones zpu ON t.pulocationid = zpu.locationid
LEFT JOIN taxi.zones zdo ON t.dolocationid = zdo.locationid
WHERE zpu.locationid IS NULL OR zdo.locationid IS NULL;

-- Q5 zones with no trips with fare amount greater than 10
SELECT
    z.locationid AS location_id,
    z.zone AS zone
FROM taxi.zones z
LEFT JOIN taxi.trips t 
    ON t.pulocationid = z.locationid 
    AND t.fare_amount > 10
WHERE t.pulocationid IS NULL