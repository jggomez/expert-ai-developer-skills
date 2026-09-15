# SCD Type 2 SQL Reference (BigQuery / Dataform)

## Target Table Shape

Every SCD Type 2 dimension needs, in addition to its business columns:

```sql
key_hash        STRING    -- hash or concatenation of the natural/business key
valid_from      TIMESTAMP
valid_to        TIMESTAMP -- NULL or '9999-12-31' while the row is current
is_current      BOOL
row_hash        STRING    -- hash of the tracked columns, to detect changes cheaply
```

## Merge Logic (plain BigQuery SQL)

Given a `staging` table holding the latest snapshot per key (already deduplicated from the Datastream change-log) and a `dim` table being maintained:

```sql
MERGE `project.dataset.dim_customer` AS target
USING (
  SELECT
    customer_id,
    name,
    address,
    tier,
    TO_HEX(SHA256(CONCAT(name, '|', address, '|', tier))) AS row_hash,
    CURRENT_TIMESTAMP() AS valid_from
  FROM `project.dataset.stg_customer_latest`
) AS source
ON target.customer_id = source.customer_id AND target.is_current = TRUE

-- Case 1: existing current row, but the tracked columns changed -> close it out
WHEN MATCHED AND target.row_hash != source.row_hash THEN
  UPDATE SET
    target.valid_to = source.valid_from,
    target.is_current = FALSE

-- Case 2: brand-new key -> insert as the first current row
WHEN NOT MATCHED BY TARGET THEN
  INSERT (customer_id, name, address, tier, row_hash, valid_from, valid_to, is_current)
  VALUES (source.customer_id, source.name, source.address, source.tier,
          source.row_hash, source.valid_from, NULL, TRUE);

-- A separate INSERT is required for Case 1's replacement row, since a single
-- MERGE statement cannot both UPDATE an existing row and INSERT a new one
-- for the same matched key in one pass:
INSERT INTO `project.dataset.dim_customer`
  (customer_id, name, address, tier, row_hash, valid_from, valid_to, is_current)
SELECT
  source.customer_id, source.name, source.address, source.tier,
  source.row_hash, source.valid_from, NULL, TRUE
FROM `project.dataset.stg_customer_latest` AS source
JOIN `project.dataset.dim_customer` AS target
  ON target.customer_id = source.customer_id
WHERE target.is_current = FALSE
  AND target.valid_to = source.valid_from; -- the row we just closed out above
```

**Why `row_hash` instead of comparing every column**: comparing one hashed column is cheaper to write and to scan than an `IS DISTINCT FROM` chain across every tracked column, and avoids the NULL-comparison pitfall entirely (`SHA256` on a `NULL`-containing `CONCAT` still produces a stable, comparable value as long as you `COALESCE` nullable columns before hashing).

## Dataform (`.sqlx`) Incremental Equivalent

```sql
config {
  type: "incremental",
  uniqueKey: ["customer_id", "valid_from"],
  bigquery: {
    partitionBy: "DATE(valid_from)"
  }
}

SELECT
  customer_id,
  name,
  address,
  tier,
  TO_HEX(SHA256(CONCAT(
    COALESCE(name, ''), '|', COALESCE(address, ''), '|', COALESCE(tier, '')
  ))) AS row_hash,
  CURRENT_TIMESTAMP() AS valid_from,
  CAST(NULL AS TIMESTAMP) AS valid_to,
  TRUE AS is_current
FROM ${ref("stg_customer_latest")}

${when(incremental(), `
WHERE customer_id NOT IN (
  SELECT customer_id FROM ${self()}
  WHERE is_current = TRUE
  AND row_hash = TO_HEX(SHA256(CONCAT(
    COALESCE(name, ''), '|', COALESCE(address, ''), '|', COALESCE(tier, '')
  )))
)
`)}
```

Closing out superseded rows (`valid_to`/`is_current`) still needs a companion `operations` block or a scheduled `UPDATE` — Dataform's `incremental` type only appends; it doesn't rewrite prior rows. Keep the close-out step as an explicit `postOperations` block in the same `.sqlx` file so both stay in sync.
