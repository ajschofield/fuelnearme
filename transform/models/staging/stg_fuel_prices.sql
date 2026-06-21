with source as (
    select * from {{ source('raw', 'fuel_prices') }}
),

unnested as (
    select
        fp.node_id,
        fp.trading_name,
        fp.loaded_at,
        (price->>'fuel_type')                                    as fuel_type,
        (price->>'price')::numeric                               as price_pence,
        (price->>'price_last_updated')::timestamptz              as price_last_updated,
        (price->>'price_change_effective_timestamp')::timestamptz as price_change_effective_timestamp
    from source fp,
    lateral jsonb_array_elements(fp.fuel_prices) as price
)

select * from unnested
