CREATE SCHEMA IF NOT EXISTS taxi;

CREATE TABLE IF NOT EXISTS taxi.zones (
    locationid INT PRIMARY KEY,
    borough TEXT,
    zone TEXT,
    service_zone TEXT
);

CREATE TABLE IF NOT EXISTS taxi.trips (
    vendorid INT,
    lpep_pickup_datetime TIMESTAMP,
    lpep_dropoff_datetime TIMESTAMP,
    store_and_fwd_flag TEXT,
    ratecodeid INT,
    pulocationid INT,
    dolocationid INT,
    passenger_count INT,
    trip_distance FLOAT,
    fare_amount FLOAT,
    extra FLOAT,
    mta_tax FLOAT,
    tip_amount FLOAT,
    tolls_amount FLOAT,
    ehail_fee FLOAT,
    improvement_surcharge FLOAT,
    total_amount FLOAT,
    payment_type INT,
    trip_type INT,
    congestion_surcharge FLOAT
);