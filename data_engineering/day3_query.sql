with ranked_trips as (
	select
		z.borough,
		z.zone,
		t.pulocationid,
		t.trip_distance,
		t.fare_amount,
		t.lpep_pickup_datetime,
		ROW_NUMBER() over (
			partition by t.pulocationid
			order by t.trip_distance DESC
		) as rn
	from taxi.trips t
	join taxi.zones z on t.pulocationid = z.locationid
)
select 
	*
from ranked_trips
where rn <= 3
order by borough, zone, rn;

with daily_fares as (
	select
		lpep_pickup_datetime::DATE as day,
		SUM(fare_amount) as total_fare
	from taxi.trips
	group by lpep_pickup_datetime::DATE
)
select
	day,
	round(total_fare::numeric, 2) as total_fare,
	rank() over (order by total_fare desc) as fare_rank,
	dense_rank() over (order by total_fare desc) as dense_fare_rank
from daily_fares
order by fare_rank;

with daily_revenue as (
	select
		lpep_pickup_datetime::DATE as day,
		sum(total_amount) as revenue
	from taxi.trips
	group by lpep_pickup_datetime::DATE
)
select 
	day,
	round(revenue::numeric, 2) as daily_revenue,
	round(
		sum(revenue) over (
			order by day
			rows between unbounded preceding and current row
		)::numeric,
		2
	) as running_revenue
from daily_revenue
order by day;

with daily_trips as (
	select
		lpep_pickup_datetime::DATE as day,
		count(*) as trip_count
	from taxi.trips
	group by lpep_pickup_datetime::DATE
)
select
	day,
	trip_count,
	LAG(trip_count) over (
		order by day
	) as previous_day_trips,
	trip_count - LAG(trip_count) over (
		order by day
	) as trip_count_change
from daily_trips
order by day;

with daily_trips as (
	select
		lpep_pickup_datetime::DATE as day,
		count(*) as trip_count
	from taxi.trips
	group by lpep_pickup_datetime::DATE
)
select
	day,
	trip_count,
	round(
		avg(trip_count) over (
			order by day
			rows between 6 preceding and current row
		),
		2
	) as moving_avg_7d
from daily_trips
order by day;
