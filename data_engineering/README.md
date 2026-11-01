# Data Engineering

Daily Data Engineering lessons.  

## Day 1: SQL Deep Dive  

### Tasks  

1. Download [NYC TLC taxi zone lookup CSV](https://github.com/DataTalksClub/nyc-tlc-data/releases/download/misc/taxi_zone_lookup.csv) and [one month of green taxi trips](https://github.com/DataTalksClub/nyc-tlc-data/releases/download/green/green_tripdata_2019-01.csv.gz) or from their [official page](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page). Create `zones` and `trips` tables.  
2. Write 4 queries in `week1.sql` with comment above each one  
    - trips with their pickup and dropoff zone names (join `zones` twice, using aliases)  
    - trip count per pickup borough  
    - zones that had zero pickups that month (LEFT JOIN ... WHERE trip is NULL)  
    - any trips whose Location ID has no matching zone  
    - Why does LEFT JOIN trips t ON … WHERE t.fare_amount > 10 drop the zero-pickup zones? Where would you move that condition to keep them?  

## Day2: SQL Deep Dive  

### Tasks
Queries:
1. Trips and average fare per passenger_count
2. Total revenue per day, sorted by date
3. Pickup zones with more than 1,000 trips (HAVING)
4. Average tip % per payment_type, counting only trips with fare > 0 (WHERE + GROUP BY)
5. COUNT(*) vs COUNT(tip_amount) side by side. Explain any difference.