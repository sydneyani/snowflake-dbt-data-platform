# Design decisions

## DuckDB by default, Snowflake as a target

The project has to run on a laptop and in GitHub Actions with no warehouse account. DuckDB is the committed profile. Snowflake is an example output using key-pair environment variables. Models use unquoted identifiers and dbt cross-database functions so the same SQL is the Snowflake path.

`dbt-snowflake` stays an optional extra. The connector is large and CI never opens a connection.

## dbt-expectations, not a second quality tool

Column tests should run in the warehouse, next to the model, in the same `dbt build` CI already runs. A Great Expectations checkpoint would be a second runtime and a second set of failure logs. Source-to-target totals do not fit a column test, so those live in the Python reconciler, which reads raw and marts directly.

## Dagster

The graph is a few ordered steps plus a dbt project. Dagster assets show that graph and can call `dbt build` without a scheduler service. The schedule exists and is stopped so a local UI does not launch a run at 06:00 UTC.

The snapshot baseline is its own asset because a snapshot of a current-state extract only learns history if you run it twice, with a change in between.

## Synthetic ERP extracts

A public trip or retail file does not have document-versus-line totals, a test account group, or a customer master that changes between two extracts. The generator fixes those cases so tests can name the document. The tradeoff is that nobody should treat the row counts as a production volume.

## Line grain, and customers that stay source-specific

The sales fact is one accepted line. Header freight and header imbalances are reconciliation findings, not silent allocations.

Customer and product dimensions stay at source-system grain. A tax id or GTIN bridge is how two ERP accounts roll together. Collapsing them in the fact would hide which system sold the order and would force a survivorship rule this project does not need.

## Staging does not drop bad rows

The duplicate SAP customer and the rejected lines are visible in staging. Filtering belongs in intermediate, and excluded lines are written to an exception mart with one reason. The reason priority is shared by the generator manifest, a dbt macro, and the reconciler.

## Schema prefix left at the dbt default

Custom schemas land in `meridian_staging`, not a bare `staging`. That is the usual Snowflake pattern: the target schema (`meridian`, or `dev` / `prod` later) prefixes the layer. A macro that strips the prefix would make the local names shorter and the production names less safe.
