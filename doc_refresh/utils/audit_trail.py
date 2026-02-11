"""
LLM Decision Audit Trail for the doc_refresh pipeline.

Captures every LLM decision made during Stage 3 processing as JSON files and
generates self-contained HTML viewers for browsing results. Uses the Null Object
pattern so the pipeline incurs zero overhead when AUDIT_PATH is not configured.

Thread-safe via threading.Lock since Stage 3 uses ThreadPoolExecutor for parallel
LLM calls (subsection analysis, summaries, chunk summaries, embeddings).

Output structure per document:
    AUDIT_PATH/db_source/relative_stem/00_overview.json ... 10_embeddings.json + viewer.html
Root index:
    AUDIT_PATH/index.html
"""

import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AuditTrail:
    """Records LLM decisions and writes JSON files plus an HTML viewer per document."""

    def __init__(self, audit_dir: Path, db_source: str, relative_path: str):
        self._audit_dir = audit_dir
        self._db_source = db_source
        self._relative_path = relative_path
        self._lock = threading.Lock()
        self._records: Dict[str, Any] = {}
        self._start_time = time.time()

    def record_metadata_extraction(
        self,
        metadata: Dict[str, Any],
        usage: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record metadata extraction results."""
        with self._lock:
            self._records["01_metadata_extraction"] = {
                "step": "metadata_extraction",
                "model": "MODEL_LARGE",
                "extracted_fields": metadata,
                "usage": usage,
            }

    def record_document_classification(
        self,
        classification: Dict[str, Any],
        usage: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record document structure classification."""
        with self._lock:
            self._records["02_document_classification"] = {
                "step": "document_classification",
                "model": "MODEL_SMALL",
                "structure_type": classification.get("structure_type"),
                "confidence": classification.get("confidence"),
                "has_toc": classification.get("has_toc"),
                "toc_sections": classification.get("toc_sections", []),
                "usage": usage,
            }

    def record_section_detection(
        self,
        batch_results: List[Dict[str, Any]],
    ) -> None:
        """Record per-batch section detection results."""
        with self._lock:
            self._records["03_section_detection"] = {
                "step": "section_detection",
                "model": "MODEL_SMALL",
                "batch_count": len(batch_results),
                "batches": batch_results,
                "total_sections_found": sum(
                    b.get("sections_found", 0) for b in batch_results
                ),
            }

    def record_section_consolidation(
        self,
        raw_count: int,
        final_count: int,
        corrections: List[str],
        page_validation_fixes: int,
        usage: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record section consolidation results."""
        with self._lock:
            self._records["04_section_consolidation"] = {
                "step": "section_consolidation",
                "model": "MODEL_LARGE",
                "raw_section_count": raw_count,
                "final_section_count": final_count,
                "corrections_made": corrections,
                "page_validation_fixes": page_validation_fixes,
                "usage": usage,
            }

    def record_subsection_analysis(
        self,
        per_section_results: List[Dict[str, Any]],
    ) -> None:
        """Record per-section subsection analysis."""
        with self._lock:
            self._records["05_subsection_analysis"] = {
                "step": "subsection_analysis",
                "model": "MODEL_SMALL",
                "sections_analyzed": len(per_section_results),
                "sections": per_section_results,
                "total_subsections_found": sum(
                    r.get("subsection_count", 0) for r in per_section_results
                ),
            }

    def record_section_summaries(
        self,
        per_section_results: List[Dict[str, Any]],
        boilerplate_count: int,
        fallback_count: int,
    ) -> None:
        """Record section summary generation results."""
        with self._lock:
            self._records["06_section_summaries"] = {
                "step": "section_summaries",
                "model": "MODEL_LARGE",
                "sections_summarized": len(per_section_results),
                "boilerplate_sections": boilerplate_count,
                "fallback_sections": fallback_count,
                "sections": per_section_results,
            }

    def record_document_fields(
        self,
        description: str,
        usage_text: str,
        usage: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record document description and usage field generation."""
        with self._lock:
            self._records["07_document_fields"] = {
                "step": "document_fields",
                "model": "MODEL_SMALL",
                "document_description": description,
                "document_usage": usage_text,
                "usage": usage,
            }

    def record_chunk_generation(
        self,
        chunk_count: int,
        section_chunk_mapping: List[Dict[str, Any]],
    ) -> None:
        """Record chunk generation (no LLM call)."""
        with self._lock:
            self._records["08_chunk_generation"] = {
                "step": "chunk_generation",
                "llm_call": False,
                "chunk_count": chunk_count,
                "section_chunk_mapping": section_chunk_mapping,
            }

    def record_chunk_summaries(
        self,
        eligible_count: int,
        prefixed_count: int,
        batch_stats: List[Dict[str, Any]],
    ) -> None:
        """Record chunk summary prefix generation."""
        with self._lock:
            self._records["09_chunk_summaries"] = {
                "step": "chunk_summaries",
                "model": "MODEL_SMALL",
                "eligible_chunks": eligible_count,
                "prefixed_chunks": prefixed_count,
                "batch_count": len(batch_stats),
                "batches": batch_stats,
            }

    def record_embeddings(
        self,
        chunks_embedded: int,
        summary_embedded: bool,
        batch_stats: List[Dict[str, Any]],
    ) -> None:
        """Record embedding generation."""
        with self._lock:
            self._records["10_embeddings"] = {
                "step": "embeddings",
                "model": "MODEL_EMBEDDING",
                "chunks_embedded": chunks_embedded,
                "summary_embedded": summary_embedded,
                "batch_count": len(batch_stats),
                "batches": batch_stats,
            }

    def set_overview(
        self,
        file_name: str,
        page_count: int,
        structure_type: str,
        structure_confidence: str,
        section_count: int,
        chunk_count: int,
        degradation_signals: List[str],
    ) -> None:
        """Set the overview record with document-level statistics."""
        total_cost = self._compute_total_cost()
        elapsed = time.time() - self._start_time
        with self._lock:
            self._records["00_overview"] = {
                "step": "overview",
                "file_name": file_name,
                "db_source": self._db_source,
                "relative_path": self._relative_path,
                "page_count": page_count,
                "structure_type": structure_type,
                "structure_confidence": structure_confidence,
                "section_count": section_count,
                "chunk_count": chunk_count,
                "total_cost": total_cost,
                "total_time_seconds": round(elapsed, 2),
                "degradation_signals": degradation_signals,
            }

    def _compute_total_cost(self) -> float:
        """Sum cost from all usage records."""
        total = 0.0
        with self._lock:
            for record in self._records.values():
                if isinstance(record, dict):
                    usage = record.get("usage")
                    if isinstance(usage, dict):
                        total += usage.get("cost", 0) or 0
                    batches = record.get("batches")
                    if isinstance(batches, list):
                        for batch in batches:
                            if isinstance(batch, dict):
                                bu = batch.get("usage")
                                if isinstance(bu, dict):
                                    total += bu.get("cost", 0) or 0
        return round(total, 6)

    def finalize(self) -> Optional[Path]:
        """Write all JSON files and the HTML viewer to the audit directory.

        Returns:
            Path to the document audit folder, or None on failure.
        """
        stem = Path(self._relative_path).stem
        doc_dir = self._audit_dir / self._db_source / stem

        try:
            doc_dir.mkdir(parents=True, exist_ok=True)

            with self._lock:
                records_snapshot = dict(self._records)

            for filename, data in sorted(records_snapshot.items()):
                json_path = doc_dir / f"{filename}.json"
                with open(json_path, "w") as f:
                    json.dump(data, f, indent=2, default=str)

            viewer_path = doc_dir / "viewer.html"
            with open(viewer_path, "w") as f:
                f.write(_generate_viewer_html(records_snapshot, self._relative_path))

            logger.info("Audit trail written to %s", doc_dir)
            return doc_dir

        except Exception as exc:
            logger.error("Failed to write audit trail for %s: %s", self._relative_path, exc)
            return None

    def get_summary(self) -> Dict[str, Any]:
        """Return a summary dict for the index page."""
        with self._lock:
            overview = self._records.get("00_overview", {})
        return {
            "file_name": overview.get("file_name", self._relative_path),
            "db_source": self._db_source,
            "relative_path": self._relative_path,
            "page_count": overview.get("page_count", 0),
            "section_count": overview.get("section_count", 0),
            "chunk_count": overview.get("chunk_count", 0),
            "total_cost": overview.get("total_cost", 0),
            "total_time_seconds": overview.get("total_time_seconds", 0),
            "structure_type": overview.get("structure_type", ""),
            "degradation_signals": overview.get("degradation_signals", []),
        }


class NullAuditTrail(AuditTrail):
    """No-op audit trail when AUDIT_PATH is not configured."""

    def __init__(self) -> None:
        pass

    def record_metadata_extraction(self, *args: Any, **kwargs: Any) -> None:
        pass

    def record_document_classification(self, *args: Any, **kwargs: Any) -> None:
        pass

    def record_section_detection(self, *args: Any, **kwargs: Any) -> None:
        pass

    def record_section_consolidation(self, *args: Any, **kwargs: Any) -> None:
        pass

    def record_subsection_analysis(self, *args: Any, **kwargs: Any) -> None:
        pass

    def record_section_summaries(self, *args: Any, **kwargs: Any) -> None:
        pass

    def record_document_fields(self, *args: Any, **kwargs: Any) -> None:
        pass

    def record_chunk_generation(self, *args: Any, **kwargs: Any) -> None:
        pass

    def record_chunk_summaries(self, *args: Any, **kwargs: Any) -> None:
        pass

    def record_embeddings(self, *args: Any, **kwargs: Any) -> None:
        pass

    def set_overview(self, *args: Any, **kwargs: Any) -> None:
        pass

    def finalize(self) -> Optional[Path]:
        return None

    def get_summary(self) -> Dict[str, Any]:
        return {}


def create_audit_trail(
    audit_path: str,
    db_source: str,
    relative_path: str,
) -> AuditTrail:
    """Factory: return AuditTrail if audit_path is set, else NullAuditTrail."""
    if not audit_path:
        return NullAuditTrail()
    return AuditTrail(
        audit_dir=Path(audit_path),
        db_source=db_source,
        relative_path=relative_path,
    )


def generate_index_html(
    audit_path: str,
    documents: List[Dict[str, Any]],
) -> None:
    """Generate the root index.html listing all audited documents."""
    if not audit_path or not documents:
        return

    audit_dir = Path(audit_path)
    audit_dir.mkdir(parents=True, exist_ok=True)

    rows_html = ""
    for doc in documents:
        stem = Path(doc.get("relative_path", "unknown")).stem
        viewer_link = f"{doc.get('db_source', '')}/{stem}/viewer.html"
        degradation = doc.get("degradation_signals", [])
        deg_text = ", ".join(degradation) if degradation else "none"
        rows_html += f"""        <tr>
            <td><a href="{_html_escape(viewer_link)}">{_html_escape(doc.get('file_name', ''))}</a></td>
            <td>{_html_escape(doc.get('db_source', ''))}</td>
            <td>{doc.get('page_count', 0)}</td>
            <td>{_html_escape(doc.get('structure_type', ''))}</td>
            <td>{doc.get('section_count', 0)}</td>
            <td>{doc.get('chunk_count', 0)}</td>
            <td>${doc.get('total_cost', 0):.4f}</td>
            <td>{doc.get('total_time_seconds', 0):.1f}s</td>
            <td>{_html_escape(deg_text)}</td>
        </tr>
"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>IRIS Audit Trail - Index</title>
<style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 20px; background: #f5f5f5; color: #333; }}
    h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
    .summary {{ background: #fff; padding: 15px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
    th {{ background: #3498db; color: #fff; padding: 12px 15px; text-align: left; font-weight: 600; }}
    td {{ padding: 10px 15px; border-bottom: 1px solid #eee; }}
    tr:hover {{ background: #f0f7ff; }}
    a {{ color: #3498db; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
</style>
</head>
<body>
<h1>IRIS Audit Trail</h1>
<div class="summary">
    <strong>Documents processed:</strong> {len(documents)} |
    <strong>Total cost:</strong> ${sum(d.get('total_cost', 0) for d in documents):.4f}
</div>
<table>
    <thead>
        <tr>
            <th>File</th>
            <th>Database</th>
            <th>Pages</th>
            <th>Structure</th>
            <th>Sections</th>
            <th>Chunks</th>
            <th>Cost</th>
            <th>Time</th>
            <th>Degradation</th>
        </tr>
    </thead>
    <tbody>
{rows_html}    </tbody>
</table>
</body>
</html>"""

    index_path = audit_dir / "index.html"
    with open(index_path, "w") as f:
        f.write(html)

    logger.info("Audit index written to %s (%d documents)", index_path, len(documents))


def _html_escape(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


def _generate_viewer_html(records: Dict[str, Any], relative_path: str) -> str:
    """Generate a self-contained HTML viewer with tabs for each JSON record."""
    tab_names = {
        "00_overview": "Overview",
        "01_metadata_extraction": "Metadata",
        "02_document_classification": "Classification",
        "03_section_detection": "Section Detection",
        "04_section_consolidation": "Consolidation",
        "05_subsection_analysis": "Subsections",
        "06_section_summaries": "Summaries",
        "07_document_fields": "Doc Fields",
        "08_chunk_generation": "Chunks",
        "09_chunk_summaries": "Chunk Summaries",
        "10_embeddings": "Embeddings",
    }

    tabs_html = ""
    panels_html = ""
    first = True
    for key in sorted(tab_names.keys()):
        if key not in records:
            continue
        label = tab_names[key]
        active_class = " active" if first else ""
        hidden_attr = "" if first else ' style="display:none"'
        tabs_html += f'        <button class="tab{active_class}" onclick="showTab(\'{key}\')">{_html_escape(label)}</button>\n'

        json_str = json.dumps(records[key], indent=2, default=str)
        panels_html += f'    <div id="{key}" class="panel"{hidden_attr}><pre>{_html_escape(json_str)}</pre></div>\n'
        first = False

    overview = records.get("00_overview", {})
    cost_bar = (
        f"<strong>Cost:</strong> ${overview.get('total_cost', 0):.4f} | "
        f"<strong>Time:</strong> {overview.get('total_time_seconds', 0):.1f}s | "
        f"<strong>Pages:</strong> {overview.get('page_count', 0)} | "
        f"<strong>Sections:</strong> {overview.get('section_count', 0)} | "
        f"<strong>Chunks:</strong> {overview.get('chunk_count', 0)}"
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Audit: {_html_escape(relative_path)}</title>
<style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; background: #f5f5f5; color: #333; }}
    .header {{ background: #2c3e50; color: #fff; padding: 15px 20px; }}
    .header h1 {{ margin: 0; font-size: 18px; }}
    .cost-bar {{ background: #fff; padding: 10px 20px; border-bottom: 1px solid #ddd; font-size: 14px; }}
    .tab-bar {{ background: #ecf0f1; padding: 0 20px; display: flex; gap: 2px; overflow-x: auto; }}
    .tab {{ padding: 10px 16px; border: none; background: transparent; cursor: pointer; font-size: 13px; font-weight: 500; color: #666; border-bottom: 3px solid transparent; white-space: nowrap; }}
    .tab:hover {{ color: #333; background: #dfe6e9; }}
    .tab.active {{ color: #3498db; border-bottom-color: #3498db; background: #fff; }}
    .panel {{ padding: 20px; }}
    pre {{ background: #fff; padding: 20px; border-radius: 8px; overflow-x: auto; font-size: 13px; line-height: 1.5; box-shadow: 0 1px 3px rgba(0,0,0,0.1); white-space: pre-wrap; word-wrap: break-word; }}
    a {{ color: #3498db; }}
</style>
</head>
<body>
<div class="header">
    <h1>{_html_escape(relative_path)}</h1>
</div>
<div class="cost-bar">{cost_bar}</div>
<div class="tab-bar">
{tabs_html}</div>
{panels_html}
<script>
function showTab(id) {{
    document.querySelectorAll('.panel').forEach(p => p.style.display = 'none');
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.getElementById(id).style.display = 'block';
    event.target.classList.add('active');
}}
</script>
</body>
</html>"""
