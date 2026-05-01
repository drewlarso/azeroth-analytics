# Azeroth Analytics

## Data Flow

BNet API data is fetched and written to Cloudflare R2 as parquet files. DuckDB reads those files into a local database, and the TUI queries that local database for browsing and analysis.

## Database Setup

```sql
CREATE VIEW auctions AS SELECT * FROM read_parquet('data/auctions/**/*.parquet');

CREATE VIEW commodities AS SELECT * FROM read_parquet('data/commodities/**/*.parquet');

CREATE VIEW all_items AS SELECT * FROM read_parquet('data/static/items.parquet');

CREATE VIEW classes AS SELECT * FROM read_parquet('data/static/item_classes.parquet');

CREATE VIEW subclasses AS SELECT * FROM read_parquet('data/static/item_subclasses.parquet');

CREATE VIEW realms AS SELECT * FROM read_parquet('data/static/realms.parquet');

CREATE TABLE auction_items AS SELECT DISTINCT realm AS realm_id, item_id FROM auctions;

CREATE TABLE commodity_items AS SELECT DISTINCT item_id FROM commodities;

CREATE TABLE items AS
SELECT * FROM all_items
WHERE id IN (
    SELECT item_id FROM auction_items
    UNION
    SELECT item_id FROM commodity_items
);

CREATE TABLE recent_auctions AS SELECT * FROM auctions WHERE MAKE_TIMESTAMP(year::INT, month::INT, day::INT, hour::INT, 0, 0) >= NOW() - INTERVAL '24 hours';

CREATE TABLE recent_commodities AS SELECT * FROM commodities WHERE MAKE_TIMESTAMP(year::INT, month::INT, day::INT, hour::INT, 0, 0) >= NOW() - INTERVAL '24 hours';
```

## Query Summary

### [`api/database_manager.py`](/Users/drewl/school/4307/azeroth-analytics/api/database_manager.py)

Select all realms:

```sql
SELECT name, id FROM realms ORDER BY name
```

Select all item classes ("Armor", 4):

```sql
SELECT name, id FROM classes ORDER BY name
```

Select all item subclasses by class ("Helmet", 3):

```sql
SELECT name, id FROM subclasses WHERE class_id = ? ORDER BY name
```

Select name of classes by id:

```sql
SELECT name FROM classes WHERE id = ?
```

Select name of subclass by id and class id:

```sql
SELECT name FROM subclasses WHERE id = ? and class_id = ?
```

Select name of realm by id:

```sql
SELECT name FROM realms WHERE id = ?
```

Select name of item by id:

```sql
SELECT * FROM items WHERE id = ?
```

Get some useful aggregate data from commodities (no specific realm)

Market value shows the 15th percentile price, what you can expect to pay for an item

Within group sorts the data so we can actually get the bottom 15%

```sql
SELECT
    MIN(unit_price) AS min_price,
    MEDIAN(unit_price) AS median_price,
    PERCENTILE_CONT(0.15) WITHIN GROUP (ORDER BY unit_price) AS market_value,
    SUM(quantity) AS quantity_listed,
    COUNT(DISTINCT auction_id) AS auction_count,
    AVG(quantity) AS average_stack
FROM recent_commodities
WHERE item_id = ?
```

Same as before, but for items that have a specific realm:

```sql
SELECT
    MIN(unit_price) AS min_price,
    MEDIAN(unit_price) AS median_price,
    PERCENTILE_CONT(0.15) WITHIN GROUP (ORDER BY unit_price) AS market_value,
    SUM(quantity) AS quantity_listed,
    COUNT(auction_id) AS auction_count,
    AVG(quantity) AS average_stack
FROM recent_auctions
WHERE item_id = ?
    AND realm = ?
GROUP BY auction_id
```

Gets the remaining duration (LONG, MEDIUM, SHORT) from recent commodities:

```sql
SELECT duration, COUNT(*) AS count
FROM recent_commodities
WHERE item_id = ?
GROUP BY duration
```

Same as before, but for auctions with a realm:

```sql
SELECT duration, COUNT(*) AS count
FROM recent_auctions
WHERE item_id = ?
    AND realm = ?
GROUP BY duration
```

Gets the price history of a commodity

Splits the data into 24 hour buckets so that there are 14 points on the chart rather than like 1 million

```sql
SELECT
    TIME_BUCKET(
        INTERVAL '24 hours',
        MAKE_TIMESTAMP(year::INT, month::INT, day::INT, hour::INT, 0, 0)
    ) AS ts,
    MIN(unit_price)
FROM commodities
WHERE item_id = ?
GROUP BY ts
ORDER BY ts
```

Same as before, but for items with a realm

I read from the parquets directly instead of using the 'auctions' view

This is to avoid touching every other realm that we dont care about, letting us avoid loading them into memory

```sql
SELECT
    TIME_BUCKET(
        INTERVAL '24 hours',
        MAKE_TIMESTAMP(year::INT, month::INT, day::INT, hour::INT, 0, 0)
    ) AS ts,
    MIN(unit_price)
FROM read_parquet('data/auctions/region=us/realm={realm_id}/**/*.parquet')
WHERE item_id = ?
GROUP BY ts
ORDER BY ts
```

Get the price of a commodity at any hour:

```sql
SELECT hour::INT AS hour, MEDIAN(unit_price) AS median_price
FROM commodities
WHERE item_id = ?
GROUP BY hour
ORDER BY hour
```

Same as before, but for items with a realm:

```sql
SELECT
    DAYOFWEEK(MAKE_TIMESTAMP(year::INT, month::INT, day::INT, hour::INT, 0, 0)) AS dow,
    MEDIAN(unit_price) AS median_price
FROM commodities
WHERE item_id = ?
GROUP BY dow
ORDER BY dow
```

Split the data into buckets again, this time with the histogram function

This is used to show the amount of items at each price range (top right graph)

```sql
SELECT histogram(unit_price)
FROM (
    SELECT unit_price
    FROM recent_commodities
    WHERE item_id = ?
    GROUP BY auction_id, unit_price
)
```

Same as before... you get the idea

```sql
SELECT histogram(unit_price)
FROM (
    SELECT unit_price
    FROM recent_auctions
    WHERE item_id = ?
        AND realm = ?
    GROUP BY auction_id, unit_price
)
```

Get the cheapest price for an item on each realm

Used to get the best realm to buy/sell an item

```sql
SELECT DISTINCT realms.name, MIN(unit_price) as price
FROM recent_auctions
JOIN realms
    ON realms.id = recent_auctions.realm
WHERE item_id = ?
GROUP BY realms.name
ORDER BY price, realms.name
```
