#!/usr/bin/env python3
"""Scaffold a Dataform .sqlx file implementing an SCD Type 2 dimension.

Generates the incremental SELECT and the change-detection WHERE clause
described in references/scd-type2-sql.md, parameterized by table name,
primary key column, and the columns whose changes should trigger a new
version. Read and adapt the output before running it — it does not know
your actual staging table's full schema.

Usage:
  python3 scaffold_scd2_dataform.py <table_name> <key_column> <tracked_col1,tracked_col2,...>
"""
import sys


TEMPLATE = """config {{
  type: "incremental",
  uniqueKey: ["{key_column}", "valid_from"],
  bigquery: {{
    partitionBy: "DATE(valid_from)"
  }}
}}

SELECT
  {key_column},
{select_columns}
  TO_HEX(SHA256(CONCAT(
{hash_columns}
  ))) AS row_hash,
  CURRENT_TIMESTAMP() AS valid_from,
  CAST(NULL AS TIMESTAMP) AS valid_to,
  TRUE AS is_current
FROM ${{ref("stg_{table_name}_latest")}}

${{when(incremental(), `
WHERE {key_column} NOT IN (
  SELECT {key_column} FROM ${{self()}}
  WHERE is_current = TRUE
  AND row_hash = TO_HEX(SHA256(CONCAT(
{hash_columns}
  )))
)
`)}}

-- TODO: add a postOperations block (or a companion scheduled query) that
-- sets valid_to = valid_from and is_current = FALSE on the row this new
-- version superseded. Dataform's `incremental` type only appends rows;
-- it does not rewrite the previous "current" row for you.
"""


def build_sqlx(table_name: str, key_column: str, tracked_columns: list) -> str:
    select_columns = "\n".join(f"  {col}," for col in tracked_columns)
    hash_columns = ",\n".join(
        f"    COALESCE(CAST({col} AS STRING), '')" for col in tracked_columns
    )
    return TEMPLATE.format(
        table_name=table_name,
        key_column=key_column,
        select_columns=select_columns,
        hash_columns=hash_columns,
    )


def main():
    if len(sys.argv) != 4:
        print(
            "Usage: python3 scaffold_scd2_dataform.py <table_name> <key_column> "
            "<tracked_col1,tracked_col2,...>",
            file=sys.stderr,
        )
        sys.exit(1)

    table_name, key_column, tracked_columns_arg = sys.argv[1:4]
    tracked_columns = [c.strip() for c in tracked_columns_arg.split(",") if c.strip()]

    if not tracked_columns:
        print("ERROR: at least one tracked column is required.", file=sys.stderr)
        sys.exit(1)

    output_path = f"dim_{table_name}.sqlx"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(build_sqlx(table_name, key_column, tracked_columns))

    print(f"Scaffolded {output_path}")
    print("Review it against your actual staging table schema before running it.")
    print("Remember to add the postOperations close-out step noted in the TODO.")


if __name__ == "__main__":
    main()
