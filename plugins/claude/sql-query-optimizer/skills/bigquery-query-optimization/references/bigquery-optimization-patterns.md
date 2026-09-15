# BigQuery Optimization Patterns Reference

Source: Google Cloud's "Query Processing and Optimization" training material. Each pattern below is Original → Optimized → Reasoning, matching the rule numbers in `SKILL.md`.

---

## 1. Necessary columns only

```sql
-- Original
select * from `dataset.table`

-- Optimized
select * EXCEPT (dim1, dim2) from `dataset.table`
```
Only select the columns necessary, especially in inner queries. `SELECT *` is cost-inefficient and may hurt performance. If the number of columns to return is large, `SELECT * EXCEPT` is often more practical than listing every needed column.

## 2. Partitioning and clustering

A table partitioned by `datehour` and filtered on it:
```sql
SELECT * FROM `project.dataset.pageviews`
WHERE DATE(datehour) BETWEEN '2017-06-01' AND '2017-06-30'
LIMIT 1
```
Partitioned only: 1.7 sec elapsed, **180 GB** processed.
Partitioned + clustered (by `wiki, title`): 1.8 sec elapsed, **16 MB** processed — same query, same result, ~11,000x less data scanned.

## 4. Late aggregation

```sql
-- Original: aggregates inside each subquery before the join
select t1.dim1, sum(t1.m1), sum(t2.m2)
from (select dim1, sum(metric1) m1 from `dataset.table1` group by 1) t1
join (select dim1, sum(metric2) m2 from `dataset.table2` group by 1) t2
on t1.dim1 = t2.dim1
group by 1;

-- Optimized: join first, aggregate once at the end
select t1.dim1, sum(t1.m1), sum(t2.m2)
from (select dim1, metric1 m1 from `dataset.table1`) t1
join (select dim1, metric2 m2 from `dataset.table2`) t2
on t1.dim1 = t2.dim1
group by 1;
```
**Caution**: this only produces the same result if both tables are already at the same grain per join key (one row per key value) — otherwise pre-aggregating changes the semantics of the join, not just its cost.

## 5. JOIN table order

```sql
-- Original: small table first
select t1.dim1, sum(t1.metric1), sum(t2.metric2)
from small_table t1
join large_table t2 on t1.dim1 = t2.dim1
where t1.dim1 = 'abc'
group by 1;

-- Optimized: large table first
select t1.dim1, sum(t1.metric1), sum(t2.metric2)
from large_table t2
join small_table t1 on t1.dim1 = t2.dim1
where t1.dim1 = 'abc'
group by 1;
```
Manually place the largest table first, then decreasing size. BigQuery's optimizer can reorder in some cases, but don't rely on it.

## 6. Filter before JOINs

```sql
-- Original: filter only applied to the right side
select t1.dim1, sum(t1.metric1), sum(t2.metric3)
from `dataset.table1` t1
left join `dataset.table2` t2 on t1.dim1 = t2.dim1
where t2.dim2 = 'abc'
group by 1;

-- Optimized: filter applied to both sides
select t1.dim1, sum(t1.metric1), sum(t2.metric3)
from `dataset.table1` t1
left join `dataset.table2` t2 on t1.dim1 = t2.dim1
where t1.dim2 = 'abc' AND t2.dim2 = 'abc'
group by 1;
```
Review the query plan to confirm filtering happens as early as possible — if not, add the redundant filter or use a subquery to pre-filter.

## 9. JOIN explosions

Caused by a JOIN with a non-unique key on both sides. SQL relational algebra produces the cartesian product of rows sharing a join key — worst case, output rows = `len(left) * len(right)`. If the job finishes, compare output rows vs. input rows in the query plan. Confirm by grouping and counting rows per JOIN key on each side. Workaround: `GROUP BY` to pre-aggregate before joining, when semantically valid.

## 10. Skewed JOINs

BigQuery shuffles data so all rows with the same join key land on the same worker — an unbalanced key overloads that worker. Diagnose via the query plan: one worker's compute time is far above the average. Workarounds: pre-filter rows with the unbalanced key out of the main query and handle them separately, or split the query into two and `UNION ALL`.

## 11. WHERE clause expression order

```sql
-- Original: expensive LIKE scan runs on every row
SELECT text FROM `stackoverflow.comments`
WHERE text LIKE '%java%' AND user_display_name = 'anon'

-- Optimized: selective filter first
SELECT text FROM `stackoverflow.comments`
WHERE user_display_name = 'anon' AND text LIKE '%java%'
```
BigQuery does not reorder your WHERE expressions for you. The optimized version is faster because the expensive `LIKE` only scans rows already narrowed down to `user_display_name = 'anon'`.

## 12. ORDER BY with LIMIT

```sql
-- Risk: Resources Exceeded on a very large result set
select t.dim1, t.dim2, t.metric1
from `dataset.table` t
order by t.metric1 desc

-- Safe: bounded final sort
select t.dim1, t.dim2, t.metric1
from `dataset.table` t
order by t.metric1 desc
limit 1000
```
Final sorting happens on a single slot. Without a `LIMIT`, that slot must hold and sort the entire result set. With a `LIMIT`, intermediate workers can discard values beyond the limit early, instead of shipping everything to one node.

## 13. String comparison

```sql
-- Original
select dim1 from `dataset.table` where regexp_contains(dim1, '.*test.*')

-- Optimized
select dim1 from `dataset.table` where dim1 like '%test%'
```
`REGEXP_CONTAINS` offers more functionality than `LIKE` but at a real execution-time cost — prefer `LIKE` when you don't need actual regex features.

## 14. Approximate functions

```sql
-- Original
select dim1, count(distinct dim2) from `dataset.table` group by 1;

-- Optimized
select dim1, approx_count_distinct(dim2) from `dataset.table` group by 1;
```
Approximate functions are generally within 1% of the exact value and meaningfully faster on large cardinalities.

## 15. SQL UDFs over JavaScript UDFs, and persistent UDFs

```sql
-- Original: JS UDF (spins up a V8 subprocess per call)
create temporary function multiply(x INT64, y INT64)
returns INT64 language js as """ return x * y; """;
select multiply(2, 2) as result;

-- Optimized: SQL UDF
create temporary function multiply(x INT64, y INT64) as (x * y);
select multiply(2, 2) as result;
```

For logic reused across queries, make it **persistent** instead of temporary:
```sql
CREATE OR REPLACE FUNCTION your_dataset.addFourAndDivide(x INT64, y INT64) AS (
  (x + 4) / y
);

-- invoked from any query with full qualification:
SELECT val, `your_project.your_dataset.addFourAndDivide`(val, 2) AS result
FROM numbers;
```
This lets you build org-wide, centrally-maintained libraries of business logic instead of redefining the same temp function in every query.

## Scripting and stored procedures (caveat)

BigQuery scripting supports multiple statements, variables, and control flow (`IF`, `WHILE`) in one request. **Caveat**: each statement commits independently — a script is not one atomic transaction, so a failure partway through can leave earlier statements' effects in place.
