with source as (
    select * from {{ source('raw', 'stations') }}
),

cleaned as (
    select
        node_id,
        nullif(trim(public_phone_number), '')   as public_phone_number,
        trading_name,
        brand_name,
        is_same_trading_and_brand_name,
        coalesce(temporary_closure, false)       as temporary_closure,
        coalesce(permanent_closure, false)       as permanent_closure,
        permanent_closure_date,
        is_motorway_service_station,
        is_supermarket_service_station,
        location ->>'address_line_1'             as address_line_1,
        location ->>'address_line_2'             as address_line_2,
        location ->>'city'                       as city,
        location ->>'county'                     as county,
        location ->>'country'                    as country,
        location ->>'postcode'                   as postcode,
        (location ->>'latitude')::float          as latitude,
        (location ->>'longitude')::float         as longitude,
        amenities,
        opening_times,
        fuel_types,
        loaded_at
    from source
)

select * from cleaned
