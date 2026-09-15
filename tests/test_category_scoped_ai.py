"""Category-scoped AI re-run: product selection logic."""

import pandas as pd
import pytest

from src.ai.batch_orchestrator import BatchOrchestrator

pytestmark = pytest.mark.unit

CAT1 = "Chladenie > Vitríny"
CAT2 = "Varenie > Sporáky"


def test_select_scopes_to_category(tmp_path):
    orch = BatchOrchestrator(
        client=None,
        result_parser=None,
        config={"ai_enhancement": {"tmp_dir": str(tmp_path)}},
    )
    df = pd.DataFrame(
        [
            # legacy DB row with prefix: must still normalize to CAT1
            {"code": "A", "defaultCategory": "Tovary a kategórie > " + CAT1, "aiProcessed": "1"},
            {"code": "B", "defaultCategory": CAT2, "aiProcessed": "0"},
            {"code": "C", "defaultCategory": CAT1, "aiProcessed": "0"},
        ]
    )

    # scoped run reprocesses the whole category, aiProcessed ignored
    assert list(orch._select(df, False, {CAT1})["code"]) == ["A", "C"]
    # default run: only unprocessed
    assert list(orch._select(df, False, None)["code"]) == ["B", "C"]
    # force: everything
    assert list(orch._select(df, True, None)["code"]) == ["A", "B", "C"]
