select
    node_id,
    trading_name,
    brand_name,
    is_motorway_service_station,
    is_supermarket_service_station,
    temporary_closure,
    permanent_closure,
    address_line_1,
    city,
    county,
    country,
    postcode,
    latitude,
    longitude,
    amenities,
    fuel_types
from {{ ref('stg_stations') }}
