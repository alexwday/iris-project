"""Unit tests for stage_1_scan auto-discovery deletion behavior."""

from doc_refresh.stages import stage_1_scan


class DummyFileSource:
    """Minimal file source stub for scan stage tests."""

    def __init__(self, folders):
        self._folders = folders

    def list_subfolders(self, folder_path=""):
        return list(self._folders)

    def list_files(self, folder_path, extensions=None):
        return []

    def get_file_hash(self, path):
        return "hash"


def test_auto_discover_marks_deleted_subfolder_documents_for_removal(monkeypatch):
    file_source = DummyFileSource(["active_db"])

    monkeypatch.setattr(stage_1_scan.config, "get_database_names", lambda: [])
    monkeypatch.setattr(
        stage_1_scan,
        "get_database_sources",
        lambda: ["active_db", "deleted_db"],
    )

    def fake_get_database_files(db_source):
        if db_source == "deleted_db":
            return [
                {
                    "document_id": "doc-1",
                    "file_path": "docs/removed_1.pdf",
                    "file_name": "removed_1.pdf",
                },
                {
                    "document_id": "doc-2",
                    "file_path": "docs/removed_2.pdf",
                    "file_name": "removed_2.pdf",
                },
            ]
        return []

    monkeypatch.setattr(stage_1_scan, "get_database_files", fake_get_database_files)

    result = stage_1_scan.run_stage(file_source=file_source)

    assert len(result.files_to_remove) == 2
    assert {f["db_source"] for f in result.files_to_remove} == {"deleted_db"}
    assert {f["file_path"] for f in result.files_to_remove} == {
        "docs/removed_1.pdf",
        "docs/removed_2.pdf",
    }
    assert result.scan_errors == []


def test_auto_discover_with_no_subfolders_still_cleans_stale_database_sources(monkeypatch):
    file_source = DummyFileSource([])

    monkeypatch.setattr(stage_1_scan.config, "get_database_names", lambda: [])
    monkeypatch.setattr(stage_1_scan, "get_database_sources", lambda: ["deleted_db"])
    monkeypatch.setattr(
        stage_1_scan,
        "get_database_files",
        lambda db_source: [
            {
                "document_id": "doc-1",
                "file_path": "docs/removed.pdf",
                "file_name": "removed.pdf",
            }
        ]
        if db_source == "deleted_db"
        else [],
    )

    result = stage_1_scan.run_stage(file_source=file_source)

    assert len(result.files_to_remove) == 1
    assert result.files_to_remove[0]["db_source"] == "deleted_db"
    assert result.files_to_remove[0]["file_path"] == "docs/removed.pdf"
    assert result.scan_errors == []


def test_configured_database_filter_does_not_auto_purge_undiscovered_sources(monkeypatch):
    file_source = DummyFileSource(["active_db"])

    monkeypatch.setattr(
        stage_1_scan.config,
        "get_database_names",
        lambda: ["active_db"],
    )
    monkeypatch.setattr(
        stage_1_scan,
        "get_database_sources",
        lambda: ["active_db", "deleted_db"],
    )

    called_sources = []

    def fake_get_database_files(db_source):
        called_sources.append(db_source)
        if db_source == "deleted_db":
            return [{"document_id": "doc-1", "file_path": "docs/removed.pdf"}]
        return []

    monkeypatch.setattr(stage_1_scan, "get_database_files", fake_get_database_files)

    result = stage_1_scan.run_stage(file_source=file_source)

    assert result.files_to_remove == []
    assert called_sources == ["active_db"]
