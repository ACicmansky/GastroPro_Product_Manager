"""Run comprehensive data quality and spec discrepancy audit over the SQLite catalog."""

import argparse
import json
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from datetime import datetime

import pandas as pd

from src.data.database.product_db import ProductDB
from src.domain.specs.auditor import CatalogAuditor


sys.stdout.reconfigure(encoding="utf-8")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def run_catalog_audit(db_path: str = "data/products.db", out_dir: str = "reports") -> pd.DataFrame:
    """Audit all products in SQLite DB and save CSV + summary JSON."""
    os.makedirs(out_dir, exist_ok=True)
    db = ProductDB(db_path)
    logger.info(f"Loading products from {db_path}...")
    df = db.get_all()
    logger.info(f"Loaded {len(df)} products. Running CatalogAuditor...")

    auditor = CatalogAuditor()
    issues_df = auditor.audit_dataframe(df)

    # Save CSV
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join(out_dir, f"data_quality_audit_{timestamp}.csv")
    latest_csv = os.path.join(out_dir, "data_quality_audit.csv")
    issues_df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    issues_df.to_csv(latest_csv, index=False, encoding="utf-8-sig")

    # Generate Summary Stats
    summary = {
        "timestamp": datetime.now().isoformat(),
        "total_products_audited": len(df),
        "total_issues_found": len(issues_df),
        "unique_flagged_products": int(issues_df["code"].nunique()) if not issues_df.empty else 0,
        "by_severity": issues_df["severity"].value_counts().to_dict() if not issues_df.empty else {},
        "by_issue_type": issues_df["issue_type"].value_counts().to_dict() if not issues_df.empty else {},
        "by_field": issues_df["field"].value_counts().to_dict() if not issues_df.empty else {},
    }

    summary_path = os.path.join(out_dir, "data_quality_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    logger.info(f"Audit completed: {len(issues_df)} issues found across {summary['unique_flagged_products']} products.")
    logger.info(f"Reports saved to {latest_csv} and {summary_path}")
    return issues_df


def main():
    parser = argparse.ArgumentParser(description="Audit catalog products for data quality and contradictions")
    parser.add_argument("--db", default="data/products.db", help="Path to SQLite DB")
    parser.add_argument("--out", default="reports", help="Output directory for reports")
    args = parser.parse_args()

    run_catalog_audit(db_path=args.db, out_dir=args.out)


if __name__ == "__main__":
    main()
