"""Asset lineage for extract, snapshot baseline, dbt build, and reconciliation.

The customer snapshot is stateful. Materialize the daily job from the start.
Rematerializing only the dbt assets against an old snapshot table is not a
supported rerun.
"""

import os
from pathlib import Path

from dagster import (
    AssetDep,
    AssetExecutionContext,
    AssetSelection,
    DefaultScheduleStatus,
    Definitions,
    ScheduleDefinition,
    asset,
    define_asset_job,
)
from dagster_dbt import DagsterDbtTranslator, DbtCliResource, DbtProject, dbt_assets

from meridian.config import lake_dir, repo_root, reports_dir, transform_dir, warehouse_path
from meridian.constants import SEED
from meridian.ingest.generate import generate
from meridian.ingest.lake import write_lake
from meridian.ingest.load import load_current_customers, load_foundation, reset_warehouse
from meridian.quality.reconcile import reconcile
from meridian.quality.report import write_report

_ROOT = repo_root()
_TRANSFORM = transform_dir(_ROOT)
os.environ.setdefault("MERIDIAN_ROOT", str(_ROOT))
os.environ.setdefault(
    "MERIDIAN_DUCKDB_PATH",
    str((_ROOT / "data" / "warehouse" / "meridian.duckdb").resolve()),
)
(_ROOT / "data" / "warehouse").mkdir(parents=True, exist_ok=True)

dbt_project = DbtProject(
    project_dir=_TRANSFORM,
    profiles_dir=_TRANSFORM,
    target="duckdb",
)
if not dbt_project.manifest_path.exists():
    dbt_project.preparer.prepare(dbt_project)


class _FolderTranslator(DagsterDbtTranslator):
    def get_group_name(self, dbt_resource_props: dict) -> str | None:
        fqn = dbt_resource_props.get("fqn", [])
        if len(fqn) > 1:
            return str(fqn[1])
        return "dbt"

    def get_asset_spec(self, manifest, unique_id, project):
        spec = super().get_asset_spec(manifest, unique_id, project)
        resource = manifest["nodes"].get(unique_id, {})
        fqn = resource.get("fqn", [])
        # Staging is the first dbt layer that reads the warehouse, so the
        # dbt build waits until the second customer extract has landed.
        if len(fqn) > 1 and fqn[1] == "staging":
            return spec.replace_attributes(
                deps=[*spec.deps, AssetDep("raw_customers_current")],
            )
        return spec


def _activate_warehouse() -> Path:
    path = warehouse_path(_ROOT)
    path.parent.mkdir(parents=True, exist_ok=True)
    os.environ["MERIDIAN_DUCKDB_PATH"] = str(path.resolve())
    os.environ["MERIDIAN_ROOT"] = str(_ROOT)
    return path


@asset(group_name="ingest", description="Deterministic SAP ECC and Oracle EBS parquet extracts.")
def lake_extract() -> dict[str, str]:
    _activate_warehouse()
    reset_warehouse(warehouse_path(_ROOT))
    dataset = generate(SEED)
    manifest = write_lake(dataset, lake_dir(_ROOT))
    return {"manifest": str(manifest), "seed": str(SEED)}


@asset(group_name="ingest", description="Load facts and the first customer extract into raw.")
def raw_foundation(lake_extract: dict[str, str]) -> str:
    del lake_extract
    load_foundation(warehouse_path(_ROOT), lake_dir(_ROOT))
    return "t1"


@asset(
    group_name="ingest",
    description="Snapshot customer master while the extract is still the first as-of.",
)
def customer_snapshot_baseline(
    context: AssetExecutionContext,
    dbt: DbtCliResource,
    raw_foundation: str,
) -> str:
    del raw_foundation
    _activate_warehouse()
    context.log.info("building the customer snapshot baseline")
    dbt.cli(
        [
            "build",
            "--select",
            "+snap_customer",
            "--exclude",
            "assert_snapshot_closed_rows",
        ]
    ).wait()
    return "baseline"


@asset(
    group_name="ingest",
    description="Replace customer masters with the second as-of and load history.",
)
def raw_customers_current(customer_snapshot_baseline: str) -> dict[str, str]:
    del customer_snapshot_baseline
    load_current_customers(warehouse_path(_ROOT), lake_dir(_ROOT))
    return {"as_of": "2025-12-15"}


@dbt_assets(
    manifest=dbt_project.manifest_path,
    project=dbt_project,
    dagster_dbt_translator=_FolderTranslator(),
)
def analytics_models(
    context: AssetExecutionContext,
    dbt: DbtCliResource,
    raw_customers_current: dict[str, str],
):
    context.log.info("dbt build after customer as-of %s", raw_customers_current["as_of"])
    _activate_warehouse()
    yield from dbt.cli(["build"], context=context).stream()


@asset(
    group_name="quality",
    description="Compare raw control totals to marts and write the reconciliation report.",
    deps=[analytics_models],
)
def reconciliation_report() -> str:
    report = reconcile(warehouse_path(_ROOT), lake_dir(_ROOT) / "manifest.json")
    paths = write_report(report, reports_dir(_ROOT))
    if report.status != "PASS":
        raise RuntimeError(report.summary)
    return str(paths["markdown"])


daily_erp_refresh = define_asset_job(
    name="daily_erp_refresh",
    selection=AssetSelection.all(),
    description="Extract, snapshot twice, build the star schema, and reconcile.",
)

daily_schedule = ScheduleDefinition(
    job=daily_erp_refresh,
    cron_schedule="0 6 * * *",
    execution_timezone="UTC",
    default_status=DefaultScheduleStatus.STOPPED,
)

defs = Definitions(
    assets=[
        lake_extract,
        raw_foundation,
        customer_snapshot_baseline,
        raw_customers_current,
        analytics_models,
        reconciliation_report,
    ],
    resources={"dbt": DbtCliResource(project_dir=dbt_project)},
    jobs=[daily_erp_refresh],
    schedules=[daily_schedule],
)
