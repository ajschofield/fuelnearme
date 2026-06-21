with prices as (
    select * from {{ ref('stg_fuel_prices') }}
),

stations as (
    select * from {{ ref('stg_stations') }}
),

joined as (
    select
        p.node_id,
        p.trading_name,
        p.fuel_type,
        p.price_pence,
        p.price_last_updated,
        p.price_change_effective_timestamp,
        p.loaded_at,
        s.brand_name,
        s.is_motorway_service_station,
        s.is_supermarket_service_station,
        s.address_line_1,
        s.city,
        s.county,
        s.country,
        s.postcode,
        s.latitude,
        s.longitude,
        s.temporary_closure,
        s.permanent_closure
    from prices p
    left join stations s on p.node_id = s.node_id
)

select * from joined
