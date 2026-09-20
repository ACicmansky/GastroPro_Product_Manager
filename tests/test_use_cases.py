"""Tests for Hexagonal Architecture ports, use cases, and adapters."""

from typing import Dict, List, Optional
import pandas as pd
import pytest

from src.domain.categories.category_service import CategoryService
from src.domain.models import PipelineOptions
from src.domain.ports.events import CallbackEventSink, ConsoleEventSink, NullEventSink
from src.domain.ports.gateways import FeedGatewayPort, ExcelIOPort
from src.domain.ports.repositories import ProductRepositoryPort
from src.domain.ports.resolution import AutoSkipResolution, CallbackResolution
from src.domain.pricing.pricing_service import PricingService
from src.domain.products.merger import ProductMerger
from src.domain.transform.output_transformer import OutputTransformer
from src.pipeline.use_cases.export_catalog import ExportCatalogUseCase
from src.pipeline.use_cases.sync_catalog import SyncCatalogUseCase


class InMemoryProductRepository(ProductRepositoryPort):
    """In-memory repository port implementation for lightning-fast tests."""

    def __init__(self, initial_df: Optional[pd.DataFrame] = None):
        self._df = initial_df.copy() if initial_df is not None else pd.DataFrame()
        self.backup_called = False

    def get_all(self) -> pd.DataFrame:
        return self._df.copy()

    def upsert(self, df: pd.DataFrame) -> None:
        if df.empty:
            return
        if self._df.empty:
            self._df = df.copy()
        else:
            merged = pd.concat([self._df, df], ignore_index=True)
            if "code" in merged.columns:
                self._df = merged.drop_duplicates(subset=["code"], keep="last").reset_index(drop=True)
            else:
                self._df = merged

    def backup(self) -> Optional[str]:
        self.backup_called = True
        return "memory://backup.db"


class MockFeedGateway(FeedGatewayPort):
    """Mock feed gateway returning static test feeds."""

    def __init__(self, feeds: Optional[Dict[str, pd.DataFrame]] = None):
        self.feeds = feeds or {}
        self.calls: List[str] = []

    def fetch_and_parse(self, feed_name: str, url: str, config: dict) -> Optional[pd.DataFrame]:
        self.calls.append(feed_name)
        return self.feeds.get(feed_name)


class MockExcelIO(ExcelIOPort):
    """Mock Excel I/O tracking loaded and written DataFrames without disk operations."""

    def __init__(self, file_contents: Optional[Dict[str, pd.DataFrame]] = None):
        self.files = file_contents or {}
        self.written: Dict[str, pd.DataFrame] = {}

    def load_xlsx(self, file_path: str) -> pd.DataFrame:
        return self.files.get(file_path, pd.DataFrame()).copy()

    def write_xlsx(self, df: pd.DataFrame, file_path: str) -> None:
        self.written[file_path] = df.copy()


class RecordingEventSink:
    """Event sink recording all emitted events."""

    def __init__(self):
        self.stages: List[str] = []
        self.messages: List[str] = []
        self.ai_progress: List[tuple] = []

    def emit_progress(self, message: str) -> None:
        self.messages.append(message)

    def emit_stage(self, stage_key: str) -> None:
        self.stages.append(stage_key)

    def emit_ai_progress(self, current: int, total: int, message: str) -> None:
        self.ai_progress.append((current, total, message))


def test_export_catalog_use_case_empty_db_raises(config):
    """ExportCatalogUseCase raises RuntimeError when database has no products."""
    repo = InMemoryProductRepository()
    transformer = OutputTransformer(config)
    mock_excel = MockExcelIO()

    use_case = ExportCatalogUseCase(repo, transformer, excel_io=mock_excel)

    with pytest.raises(RuntimeError, match="V databáze sa nenachádzajú žiadne produkty"):
        use_case.execute("out/test.xlsx")


def test_export_catalog_use_case_success(config):
    """ExportCatalogUseCase exports products to Excel format using in-memory repo."""
    sample_df = pd.DataFrame(
        [
            {
                "code": "PROD-001",
                "name": "Stôl nerezový",
                "price": "150.00",
                "defaultCategory": "Nerezový nábytok",
                "source": "core",
            },
            {
                "code": "PROD-002",
                "name": "Drez nerezový",
                "price": "220.00",
                "defaultCategory": "Umývanie riadu",
                "source": "core",
            },
        ]
    )
    repo = InMemoryProductRepository(sample_df)
    transformer = OutputTransformer(config)
    mock_excel = MockExcelIO()
    event_sink = RecordingEventSink()

    use_case = ExportCatalogUseCase(repo, transformer, excel_io=mock_excel)
    result = use_case.execute("out/export.xlsx", event_sink=event_sink)

    assert result.product_count == 2
    assert "out/export.xlsx" in mock_excel.written
    assert len(mock_excel.written["out/export.xlsx"]) == 2
    assert any("Export dokončený" in m for m in event_sink.messages)


def test_export_catalog_use_case_filter_categories(config):
    """ExportCatalogUseCase filters products by category list."""
    sample_df = pd.DataFrame(
        [
            {"code": "P1", "name": "Item 1", "defaultCategory": "Cat A"},
            {"code": "P2", "name": "Item 2", "defaultCategory": "Cat B"},
        ]
    )
    repo = InMemoryProductRepository(sample_df)
    transformer = OutputTransformer(config)
    mock_excel = MockExcelIO()

    use_case = ExportCatalogUseCase(repo, transformer, excel_io=mock_excel)
    result = use_case.execute("out/export.xlsx", selected_categories=["Cat A"])

    assert result.product_count == 1
    written_df = mock_excel.written["out/export.xlsx"]
    assert len(written_df) == 1
    assert written_df.loc[0, "code"] == "P1"


def test_sync_catalog_use_case_in_memory(config, tmp_path):
    """SyncCatalogUseCase executes end-to-end sync with in-memory repo, mock feed, and mock excel."""
    db_data = pd.DataFrame(
        [{"code": "OLD001", "name": "Old Product", "price": "50", "defaultCategory": "Cat A", "source": "core"}]
    )
    feed_data = pd.DataFrame(
        [{"code": "NEW001", "name": "New Product", "price": "100", "defaultCategory": "Cat A", "source": "testfeed"}]
    )

    repo = InMemoryProductRepository(db_data)
    feed_gw = MockFeedGateway({"testfeed": feed_data})
    mock_excel = MockExcelIO()
    event_sink = RecordingEventSink()

    test_config = dict(config)
    test_config["xml_feeds"] = {"testfeed": {"url": "http://example.com/feed.xml"}}

    use_case = SyncCatalogUseCase(
        product_repo=repo,
        merger=ProductMerger(),
        category_service=CategoryService(),
        transformer=OutputTransformer(test_config),
        pricing_service=PricingService(),
        feed_gateway=feed_gw,
        excel_io=mock_excel,
        config=test_config,
    )

    options = PipelineOptions(output_path="out/output.xlsx")
    result = use_case.execute(options, event_sink=event_sink)

    assert result.product_count >= 1
    assert "testfeed" in feed_gw.calls
    assert repo.backup_called is True
    assert "out/output.xlsx" in mock_excel.written

    # Check stage transitions in event sink
    assert "load" in event_sink.stages
    assert "feeds" in event_sink.stages
    assert "merge" in event_sink.stages
    assert "categories" in event_sink.stages
    assert "export" in event_sink.stages


def test_user_resolution_ports():
    """UserResolutionPort adapters behave as expected."""
    auto = AutoSkipResolution()
    assert auto.resolve_category("Cat 1") == "Cat 1"
    assert auto.resolve_price({}, pd.DataFrame()) is None

    cb = CallbackResolution(
        on_category=lambda old, name: f"Mapped {old}",
        on_price=lambda data, df: "99.90",
    )
    assert cb.resolve_category("Old") == "Mapped Old"
    assert cb.resolve_price({}, pd.DataFrame()) == "99.90"


def test_event_sink_ports():
    """EventSinkPort adapters handle events cleanly without exceptions."""
    null_sink = NullEventSink()
    null_sink.emit_progress("test")
    null_sink.emit_stage("load")
    null_sink.emit_ai_progress(1, 10, "msg")

    received = []
    cb_sink = CallbackEventSink(
        on_progress=lambda m: received.append(("progress", m)),
        on_stage=lambda s: received.append(("stage", s)),
        on_ai_progress=lambda cur, tot, m: received.append(("ai", cur, tot, m)),
    )
    cb_sink.emit_progress("hello")
    cb_sink.emit_stage("feeds")
    cb_sink.emit_ai_progress(5, 10, "chunk")

    assert ("progress", "hello") in received
    assert ("stage", "feeds") in received
    assert ("ai", 5, 10, "chunk") in received

    console_sink = ConsoleEventSink()
    console_sink.emit_progress("console progress")
    console_sink.emit_stage("merge")
    console_sink.emit_ai_progress(2, 5, "console ai")
