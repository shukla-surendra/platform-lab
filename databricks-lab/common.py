"""Shared helper: a local SparkSession with Delta Lake enabled.

Databricks gives you `spark` ready-made, with Delta built in. Locally we have to switch Delta on
ourselves. Everything else in the lessons is the same code you would run on Databricks.
"""
import shutil
from pathlib import Path

from delta import configure_spark_with_delta_pip
from pyspark.sql import SparkSession

WAREHOUSE = Path(__file__).parent / ".data"   # all tables and checkpoints land here (git-ignored)


def get_spark(app: str = "databricks-lab") -> SparkSession:
    builder = (
        SparkSession.builder.appName(app)
        .master("local[2]")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .config("spark.sql.shuffle.partitions", "4")          # default 200 is silly on a laptop
        .config("spark.ui.showConsoleProgress", "false")
        .config("spark.sql.warehouse.dir", str(WAREHOUSE / "warehouse"))
    )
    spark = configure_spark_with_delta_pip(builder).getOrCreate()
    spark.sparkContext.setLogLevel("ERROR")
    return spark


def fresh(name: str) -> str:
    """Return a clean directory path for a lesson's table; deletes the previous run's data."""
    path = WAREHOUSE / name
    shutil.rmtree(path, ignore_errors=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    return str(path)


def show_files(path: str) -> None:
    """Print a table folder's files, to see Delta's layout (parquet data + _delta_log)."""
    root = Path(path)
    for p in sorted(root.rglob("*")):
        if p.is_file() and not p.name.startswith(".") and not p.name.endswith(".crc"):
            print(f"  {p.relative_to(root)}  ({p.stat().st_size} bytes)")
