SELECT
    passenger_count,
    COUNT(*)                  AS trips,
    ROUND(AVG(fare_amount)::NUMERIC, 2) AS avg_fare
FROM taxi.trips
GROUP BY passenger_count
ORDER BY passenger_count;

SELECT
    CAST(lpep_pickup_datetime AS DATE) AS date,
    SUM(total_amount) AS total_revenue
FROM taxi.trips
GROUP BY date
ORDER BY date DESC;

SELECT
    z.zone,
    COUNT(t.PULocationID) AS trip_count
FROM taxi.zones z
LEFT JOIN taxi.trips t ON z.LocationID = t.PULocationID
GROUP BY z.zone
HAVING COUNT(t.PULocationID) > 1000;

SELECT
    payment_type,
    AVG(tip_amount / fare_amount * 100) AS avg_tip_percentage,
    COUNT(*) AS total_trips,
    COUNT(tip_amount) AS trips_with_tip_amount
FROM taxi.trips
WHERE fare_amount > 0
GROUP BY payment_type
ORDER BY payment_type;