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

## Day 3: SQL Deep Dive  

### Tasks  
1. The 3 longest trips in each pickup zone (ROW_NUMBER)
2. Days ranked by total fare (RANK vs DENSE_RANK, with a comment on how they differ)
3. A running total of daily revenue (SUM() OVER (ORDER BY day))
4. The day-over-day change in trip count (LAG)
5. A 7-day moving average of trips (ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)

## Day 4: SQL Deep Dive  

### Tasks  
1. Rank pickup zones by trip count within each borough (RANK + PARTITION BY).
2. Find the top 3 longest trips per day (ROW_NUMBER in a CTE, then filter rn <= 3).
3. Show daily revenue with a 7-day moving average.
4. Show each day’s trip count next to the previous day’s, plus the % change (LAG).

## Day 5: SQL Deep Dive

### Tasks  
1. Write a query joining trips to the zone lookup twice (pickup + dropoff) and summing fares by borough. Compare COUNT(*) before vs after the joins — prove there’s no fan-out.
2. Write one NOT IN query, add a NULL to the subquery, watch it break, then fix it with NOT EXISTS.
3. Pick your slowest query from this week, run EXPLAIN ANALYZE, add an index, rerun, and note the before/after time as a comment in your .sql file.

## Day 8: Python for data  

### Tasks  
1. Build dataframe of 100k rows (an int id, a float, a date, a text category), save it as `.csv`, `.json`, `.parquet`  
2. Print each file's size and the `dtypes`  

## Day 9: Python for data  

### Tasks  
1. Load one month of NYC TLC taxi trips (or any data.gov.my CSV) into a DataFrame
2. Print df.info() and fix at least 2 wrong dtypes (for example, datetimes stored as strings)
3. Drop duplicates and any rows with a negative fare or distance, then print how many rows you removed
4. Run a groupby that matches one of your Week 1 SQL answers (for example, average fare by hour of day) and check that the numbers agree
5. Save the cleaned data with df.to_parquet("clean.parquet")  

## Day 10: Python for data  

### Tasks  
Write `fetch_weather.py` that calls the free Open-Meteo forecast API for Kuala Lumpur (lat 3.14, lon 101.69) and asks for `hourly=temperature_2m,precipitation`.  
1. Use requests.get(url, params=..., timeout=10) and raise_for_status().
2. Turn the hourly block into a DataFrame with columns time, temperature_2m, precipitation, and parse time as a datetime.
3. Print the row count, the date range and the hottest hour.
4. Save it to data/kl_weather.csv.  

## Day 11: Python for data  

### Tasks  
Write a `fetch_json(url, max_retries=3)` function that:  
1. sets a 10 s timeout and calls raise_for_status()  
2. retries on timeouts, 429 and 5xx with backoff (1 s, 2 s, 4 s), logging each attempt  
3. raises right away on other 4xx errors  
4. raises a clear custom IngestError once retries are used up  

Test against `https://httpbin.org/status/500`, `/status/404`, `/delay/15`  

## Day 12: Python for data  

### Tasks  
Pick a public JSON API (eg. `api.data.gov.my` or API you used this week)  
1. Use a bad URL or a 1-second timeout. The script should catch the error, log it, and exit with a non-zero code.
2. Check the response with resp.raise_for_status() and retry 3 times with backoff.
3. Put one string value into a numeric column. Find the problem with breakpoint() and fix it with an explicit astype or pd.to_numeric(errors="coerce").  

## Day 13: Python for data

### Tasks  
Write ingest.py against Open-Meteo (free, no key). Use hourly temperature and precipitation for Kuala Lumpur (lat 3.14, lon 101.69).

1. extract(): requests.get with timeout=10, plus 3 retries with backoff
2. transform(): build a DataFrame from hourly, parse time to datetime, and add an ingested_at column
3. load(): write to data/weather_YYYY-MM-DD.parquet with pyarrow
4. main() with argparse for --lat, --lon and --out, and a requirements.txt in a fresh venv  

## Day 14: Python for data  

### Tasks  
1. Swap the prints for logging, and wrap the main flow so any exception gets logged and ends with sys.exit(1).
2. Run pip freeze > requirements.txt. Then delete the venv, recreate it, reinstall, and run python ingest.py from a clean shell.
3. Add a README.md with these sections: What it does · How to run · What broke · What I learned.
4. Commit, push, and tick Week 2 in your plan’s progress checklist.  

## Day 15: Tooling + modeling  

### Tasks
Take CSV from Week 1 or 2 and write `inspect.sh` that prints:
1. Row count (minus header) and column count  
2. The header, one column name per line, numbered  
3. The top 5 most common values in a column you pass as a second argument  
4. How many rows have an empty value in that column  

Make it executable (`chmod +x`) add `set -euo pipefail`, and have it exist with clear message if file doesn't exists.  

## Day 16: Tooling + modeling  

### Tasks  
1. git switch -c feat/postgres-docker and add a placeholder docker-compose.yml plus a README line about it. Commit.  
2. Switch back to main, edit the same README line differently and commit, so the two branches now conflict.  
3. Merge the feature branch, resolve the conflict by hand and commit.  
4. Push both, open a pull request on GitHub (even into your own repo) and merge it.  

## Day 17: Tooling + modeling  

### Tasks  
1. Write a `docker-compose.yml` with a `postgres:16` service: user, password and DB set as env vars, port `5432:5432`, and a named volume mounted at `/var/lib/postgresql/data`.  
2. Add a second service, `pgadmin` (or just use `psql`), and connect to the DB.  
3. Create a table and insert 3 rows.
4. Run `docker compose down`, then `up -d` again.
✅ Done when your 3 rows are still there after the restart and the compose file is committed to your repo.  

## Day 18: Tooling + modeling  

### Tasks  
Using the data your `ingest.py` pulls:
1. Write down the grain in one sentence.  
2. Pick 1 fact table and at least 3 dimensions, including dim_date. List each table’s columns, with surrogate keys on the dimensions.  
3. Write the CREATE TABLE statements and run them in the Postgres you started in Docker this week.  
4. Insert 5 or more hand-made rows, then run one query that joins the fact table to two dimensions with a GROUP BY.  

## Day 19: Tooling + modeling  

### Tasks  
1. Write a docker-compose.yml with a postgres:16 service that has a named volume, a pg_isready healthcheck, and port 5432 mapped. Add a second service, pgadmin or adminer.
2. Write load.py to read your Parquet file from ingest.py and write it into a raw_* table with pandas + SQLAlchemy.
3. Break things on purpose, then fix them: stop and restart with docker compose down and with down -v, change the host port to one that’s already in use, and run load.py before the database is healthy.  

## Day 20: Tooling + modeling  

### Tasks  
1. Write docker-compose.yml with a postgres:16 service: env vars for user/password/db, port 5432, a named volume, and ./sql mounted to /docker-entrypoint-initdb.d/.  
2. In sql/01_schema.sql, create raw_* (data as it landed), 2–3 dim_* tables and one fact_* table, with PK/FK constraints.  
3. Write load.py. It reads your Week 2 Parquet into raw_* (pandas + SQLAlchemy to_sql), then runs INSERT … SELECT to fill the dims and then the fact.  
4. Finish line: after docker compose down -v && docker compose up -d && python load.py, a join from fact to every dim returns rows. Commit it.  

## Day 21: Tooling + modeling  

A **star schema** has one central **fact table** and several **dimension tables** around it. Each row in fact table is one measureable event at a stated grain, holding numeric measures plus foreign keys. Dimension tables hold the descriptive "who/what/when/where" attributes you filter and group by.  

### Tasks  
1. Run docker compose down -v, then docker compose up -d and your load script, and time how long the rebuild takes from scratch.  
2. Export your star schema diagram (dbdiagram.io, draw.io or Mermaid) to the repo, with the grain written on it.  
3. Write a README note covering what you built, the run steps, what broke and what you learned.  
4. Commit, push, and tick “Week 3” in the plan’s progress checklist. ✅ You’re done when a fresh git clone plus the README steps gives you loaded tables in under 15 minutes.  

## Day 22: Cloud warehouse  
Understand ETL vs ELT  
ETL because old warehouses had expensive storage and compute.  
ELT because transformation happen inside the warehouse, with cheap columnar storage and elastic compute, raw data stays untouched for re-transformation whenever business logic changes.  

### Tasks  
Take parquet output from `ingest.py` and build it both ways in DuckDB  
1. **ETL**: clean data in pandas (rename columns, cast types, drop nulls) then load it as `etl_clean`.  
2. **ELT**: load parquet file into `raw_data`, then write one SQL `CREATE TABLE elt_clean AS SELECT ...` that does the same cleaning  

