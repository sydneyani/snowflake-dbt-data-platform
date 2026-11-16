# Interview walkthrough

This is the version to study before you talk through the repo. The numbers below are from the seed-42 run on 2026-11-16. If you rerun `make pipeline` you should get the same totals. If you do not, do not quote the old ones.

## Sixty seconds

I built a local ELT platform that consolidates SAP ECC and Oracle EBS sales and work orders into one star schema. The extract is a deterministic stand-in for the ERP tables, so the project runs without a paid warehouse. dbt on DuckDB does staging, intermediate, and marts, including a type 2 customer dimension. A separate Python check recomputes control totals from the raw tables and compares them to the facts. Dagster runs the whole thing, including two customer extracts so the snapshot actually closes old versions. The same dbt project has a Snowflake profile for when the raw tables live there.

## How to demo it

```bash
uv sync --all-groups
make pipeline
uv run dagster dev -m meridian.orchestration.definitions
```

Open `data/reports/reconciliation.md` and the Dagster asset catalog. Point at:

1. The lake under `data/lake`, partitioned customer files `as_of=2025-06-30` and `as_of=2025-12-15`.
2. `snap_customer` having 30 closed versions.
3. Sales documents `0000042201` (Columbus) and `0000042202` (Austin) on the fact, joined through `customer_key`.
4. The `EXPLAINED` row for Oracle order `500421`.

The schedule is defined and stopped. Say that out loud so nobody thinks the laptop will kick off a load at 06:00 UTC.

## What to say about the data

The generator is not a claim that you pulled production SAP. Say: "I modeled the extract on the tables I would actually land: VBAK/VBAP/KNA1/MARA/AFKO and the Oracle order, customer, item, and WIP tables. Prices live on the order line, not on MARA, because SAP price conditions are a different extract. Sold-to is flattened to the customer account; a real EBS extract still has the site-use hop."

Quantities are in the item base unit. Everything in this dataset is EA, so there is no unit-of-measure conversion. If they ask, the real version uses MARM or `MTL_UOM_CONVERSIONS` before you sum quantities.

FX rates are a smooth synthetic series. Do not call them historical ECB or market rates.

## Ingestion

`src/meridian/ingest/generate.py` builds the tables. `lake.py` writes parquet. `load.py` is the only code that knows about the warehouse file: `create or replace table raw.<name> as select * from read_parquet(...)`.

That boundary is the Snowflake story. Locally the loader is a DuckDB statement. In Snowflake it is `COPY INTO` from a stage, which `snowflake_load.py` renders and unit tests. You have not run it against a live account in this repo. Say that.

Two customer files exist because a snapshot only sees the current extract. History of name and address changes is also landed as its own extract, the way you would land CDHDR-style changes or a daily full master with an effective date. The dimension the facts use comes from the snapshot. A dbt test checks that the current snapshot row matches the latest history-extract row, so the two feeds cannot drift quietly.

The duplicate SAP customer stays in staging. Staging is one row per extract row. Deduping is an intermediate rule. That is a good sentence if they ask where data quality belongs.

## Staging, intermediate, marts

Staging renames and casts. `ktokd = 'TEST'` becomes `is_test_account`. Nothing is filtered.

Intermediate conforms the two ERPs onto one column set, dedupes the customer, and stamps `exclusion_reason`. Lines are not deleted. The exception mart is the deleted-looking population, with a reason.

Marts are the star schema. Facts are tables. Staging and intermediate are views.

Say the grains without looking them up:

- Sales fact: one accepted line. The customer key is the version effective on the order date.
- Work-order fact: one order or job, including open ones. No exclusion rule on that grain, so the control total is raw count versus fact count.
- Customer: one version per source customer. You do not collapse SAP and Oracle into one customer before the fact, because the selling system is part of the grain. The tax-id bridge is how an analyst rolls two accounts together.
- Product: one item per ERP. Same idea, with GTIN as the cross-ERP key. Product is not slowly changing in this project. Say that you scoped SCD to the customer because that is where the demo changes are.

`mart_sales_monthly` includes currency in the grain. Document amounts must not be summed across USD, EUR, and GBP. USD amounts can. Each order is single-plant, which is why `order_count` at plant grain does not double-count a document. If a later extract allows multi-plant orders, that metric has to change.

## SCD2

`snap_customer` is a check snapshot on name, city, region, postal code, credit limit, and deletion flag. It also sets `updated_at` to the business timestamp. dbt stores that value in `dbt_valid_from`. The first snapshot run, while the extract is still 30 June 2025, inserts everyone with `updated_at` of 2024-01-01 (or the late-customer date, but late customers are not in the first file). The second run sees the 1 November 2025 changes and closes those 30 rows.

If you only snapshotted once, every `dbt_valid_to` would be null and the point-in-time join would be untested. The closed-row test is excluded from the first `dbt build` and runs on the full build, so CI fails if someone drops the second pass.

Late customers (created 1 October 2025) appear only in the second extract. Their orders are on or after that date. The point-in-time join still finds them.

Do not say the snapshot replays SAP change documents by itself. The business date is on the extract. dbt records it. That is the difference between a check snapshot with `updated_at` and a snapshot whose `dbt_valid_from` is "whenever the job ran."

## Reconciliation, which is the part closest to the day job

The reconciler is not a dbt test. It opens DuckDB, reads `raw`, and reads the marts. Three-way match on accepted document amount and line count:

- manifest written by the generator
- SQL in the reconciler that reimplements the exclusion rules
- `fct_sales_order_lines`

On the seed-42 run all three say 8,801 lines and 2,786,783.00. USD matches at 2,907,700.45 between the reconciler SQL and the fact. The manifest does not carry a second USD implementation, so you do not claim a three-way match on USD.

Header tie-out is a different question from pipeline tie-out. The fact is at line grain. Oracle `500420` has 50.00 of header freight that was never allocated to lines. Residual after subtracting freight is zero. Oracle `500421` is 25.00 high with no freight code. That is a source defect. The pipeline status stays PASS and the check status is EXPLAINED. Anything else in that residual list fails the job.

Say the limit of the design in one sentence: the reconciler reimplements the rules, so a shared mistake in both places can still pass. The manifest is a third implementation on the document amount, which is why that total is three-way.

Exclusion order, if they ask: test account, cancelled, rejected line, invalid currency, missing quantity, missing FX. Test beats a rejection so a row has one reason.

## Orchestration

Dagster assets, in order:

1. `lake_extract` writes parquet and deletes the warehouse file. The snapshot is stateful, so a rerun starts clean.
2. `raw_foundation` loads facts and the first customer extract.
3. `customer_snapshot_baseline` runs `dbt build --select +snap_customer` and skips the closed-row test.
4. `raw_customers_current` loads the second customer extract and the history files.
5. `analytics_models` is the dbt project. Staging assets depend on step 4, so `dbt build` cannot start early.
6. `reconciliation_report` fails the asset if the report status is FAIL.

Rematerializing only the dbt asset against an old snapshot is not a supported rerun. Say that. It is the same lesson as "don't run a snapshot twice on the same change and expect idempotent history."

The verified Dagster command is:

```bash
uv run dagster asset materialize -m meridian.orchestration.definitions --select '*'
```

That run completed successfully. The `dbt build` inside it reported 137 passes, 0 warnings, and 0 errors, and finished in 2.68 seconds. The Dagster multiprocess executor reported the parent process exiting after 31.94 seconds. Those are timings from that one run, not a benchmark.

## Why DuckDB and a Snowflake profile

You want a hiring manager to clone the repo and run it. DuckDB is the default target in `transform/profiles.yml`. Snowflake is the alternate output in `profiles.yml.example`, key-pair auth, no password in the file. `dbt-snowflake` is an optional extra so CI does not install the connector.

The custom schema names become `meridian_staging` and so on. That is stock dbt behavior: the target schema prefixes the custom schema. On Snowflake, dev and prod targets then land in different schemas without a macro change.

## What CI proves

GitHub Actions installs from `uv.lock`, runs ruff, runs pytest, and runs sqlfluff with the dbt templater. Pytest includes the pipeline, so CI is not a unit-test-only green bar. sqlfluff runs after pytest because the dbt packages and the DuckDB file have to exist for the templater.

## Questions they ask, and a straight answer

**Why not Great Expectations?** The checks that matter here are warehouse SQL: the same engine that built the mart evaluates the test, and CI does not stand up a second tool. `dbt_expectations` covers ranges and sets. The reconciler covers source-to-target totals, which is the check GE would have been a clumsy host for.

**Why not Airflow?** One Python process, local UI, assets that match the dbt graph. Airflow is the right call when the estate is already Airflow. This repo is not that estate.

**Why synthetic data?** A public trip file does not exercise ERP keys, document versus line totals, or a customer master that changes between extracts. The generator lets the tests name the broken document.

**Is the customer conformed across ERPs?** Not inside the fact. The fact keeps the selling system's customer. `bridge_shared_customer` lists the 30 tax ids that appear on both. Survivorship rules are a business decision; collapsing early hides which system took the order.

**What would you add on a real Snowflake account?** Streams and tasks or the same Dagster job against the Snowflake target, a raw `COPY` from stages, masking on customer address columns, and freshness tests once extracts are actually daily. Freshness is intentionally off here because the demo extract is a fixed as-of date in 2025, and a freshness error would be noise.

**What is the fiscal calendar?** July to June. July is fiscal month 1 and fiscal quarter 1. It is a choice, not a claim about a specific company's calendar.

## What not to claim

- Do not say this ran in a Snowflake account. The profile is ready. CI used DuckDB.
- Do not say the FX rates are market data.
- Do not say you reconciled a production SAP system with these files.
- Do not quote a runtime you did not measure. The only timings in this doc are the 2.68 second `dbt build` and the 31.94 second Dagster executor line from the verified run. They are one machine, one run.
- Do not describe `mart_sales_monthly` as revenue. It is the sum of accepted line amounts. There is no cost, so there is no margin.

## If you only remember the defects

| Id | What it is | What the platform does |
| --- | --- | --- |
| SAP `0000000042` | Duplicate customer row in the extract | Staging keeps both. Intermediate keeps the later `extracted_at`. |
| SAP `0000042000` | Currency `XXX` | Excluded as `INVALID_CURRENCY`. One line, 45.00. |
| Oracle `500420` | 50.00 header freight | Header ties after freight. Not in the line fact. |
| Oracle `500421` | 25.00 header with no freight code | Reported as an explained source gap. |
| 20 SAP and 10 Oracle customers | Attribute change on 2025-11-01 | Two snapshot versions. Facts before that date keep the old city or name. |
| Test accounts | Account group or customer class `TEST`, 12 lines, 303.00 | In the exception mart, not the fact. |
