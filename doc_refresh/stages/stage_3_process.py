"""
Stage 3: Process - Create Structured Data from Extracted Content.

This stage transforms extracted document content into structured hierarchical
data suitable for vector search and LLM-based retrieval.

Processing steps:
1. Extract Document Metadata - Title, authors, dates from first pages
2. Structure Detection - Classify document, detect primary sections
3. Subsection Analysis - Identify subsections within primary sections
4. Enhanced Summarization - Generate detailed JSON summaries with key facts
5. Document Summary - Build complete summary with metadata header
6. Document Description/Usage - Generate catalog fields describing purpose and applicability
7. Context Generation - Add hierarchy prefixes to chunks
8. Chunk Summary Prefixes - Generate concise summaries and prepend to chunk content
9. Embedding Generation - Generate embeddings for chunks and summary

Functions:
    run_stage: Execute the processing stage
"""

import json
import logging
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from concurrent.futures import ThreadPoolExecutor, as_completed

from ..connections.llm import OpenAIConnectorError, calculate_token_cost, execute_llm_call
from ..connections.oauth import fetch_oauth_token
from ..stages.stage_2_extract import ExtractedDocument
from ..utils.env_config import config
from ..utils.prompt_loader import get_prompt
from ..utils.token_utils import count_tokens, truncate_to_tokens

logger = logging.getLogger(__name__)


class StructureType(str, Enum):
    """Document structure classification types."""

    CHAPTERS = "chapters"
    SECTIONS = "sections"
    TOPIC_BASED = "topic_based"
    SEMANTIC = "semantic"


def _normalize_structure_type(value: str) -> StructureType:
    """Normalize and validate a structure_type string to a StructureType enum."""
    normalized = value.lower().strip() if value else "semantic"
    valid_values = {e.value for e in StructureType}
    if normalized not in valid_values:
        logger.error(
            "Invalid structure_type '%s', falling back to SEMANTIC", value
        )
        return StructureType.SEMANTIC
    return StructureType(normalized)


@dataclass
class SectionBreak:
    """A detected section break in the document."""

    page_number: int
    title: str
    level: int = 1
    inferred: bool = False


_DEFAULT_METADATA_FIELDS = [
    {"name": "title", "description": "Document title", "type": "string", "required": True},
    {"name": "authors", "description": "List of authors", "type": "list", "required": True},
    {"name": "publication_date", "description": "Publication or effective date", "type": "string", "required": False},
    {"name": "publication_venue", "description": "Publisher, journal, or issuing organization", "type": "string", "required": False},
    {"name": "abstract", "description": "Executive summary or abstract from the document", "type": "string", "required": False},
]

_metadata_fields_cache: Optional[List[Dict[str, Any]]] = None


def _load_metadata_fields_config() -> List[Dict[str, Any]]:
    """Load and cache metadata fields configuration from JSON file."""
    global _metadata_fields_cache
    if _metadata_fields_cache is not None:
        return _metadata_fields_cache

    config_path = Path(__file__).resolve().parent.parent / "config" / "metadata_fields.json"
    try:
        with open(config_path) as f:
            data = json.load(f)
        _metadata_fields_cache = data.get("fields", _DEFAULT_METADATA_FIELDS)
        logger.info("Loaded metadata fields config: %d fields from %s", len(_metadata_fields_cache), config_path)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        logger.warning("Could not load metadata fields config (%s), using defaults", exc)
        _metadata_fields_cache = _DEFAULT_METADATA_FIELDS

    return _metadata_fields_cache


def _build_metadata_tool_schema(fields_config: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build an OpenAI tool call function schema from metadata fields config."""
    properties = {}
    required = []

    for field_def in fields_config:
        name = field_def["name"]
        desc = field_def.get("description", name)
        field_type = field_def.get("type", "string")

        if field_type == "list":
            properties[name] = {
                "type": "array",
                "items": {"type": "string"},
                "description": desc,
            }
        else:
            properties[name] = {
                "type": "string",
                "description": desc,
            }

        if field_def.get("required", False):
            required.append(name)

    return {
        "type": "function",
        "function": {
            "name": "extract_metadata",
            "description": "Extract document metadata fields from the provided pages.",
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }


def _build_metadata_user_prompt(fields_config: List[Dict[str, Any]], page_excerpt: str) -> str:
    """Build user prompt listing the metadata fields to extract."""
    field_descriptions = "\n".join(
        f"- {f['name']}: {f.get('description', f['name'])} ({'required' if f.get('required') else 'optional'})"
        for f in fields_config
    )
    return (
        f"Extract the following metadata fields from this document excerpt:\n\n"
        f"{field_descriptions}\n\n"
        f"Document excerpt:\n{page_excerpt}"
    )


@dataclass
class Subsection:
    """A subsection (level 2) within a primary section."""

    id: str
    parent_section_id: str
    sequence_number: int  # Within parent (1, 2, 3...)
    title: str
    page_start: int
    page_end: int
    summary: Dict[str, Any] = field(default_factory=dict)  # JSON summary

    @property
    def page_count(self) -> int:
        return self.page_end - self.page_start + 1


@dataclass
class Section:
    """A primary section (level 1) in the document hierarchy."""

    id: str
    sequence_number: int  # Within document (1, 2, 3...)
    title: str
    page_start: int
    page_end: int
    summary: Dict[str, Any] = field(default_factory=dict)  # JSON summary
    subsections: List[Subsection] = field(default_factory=list)
    inferred: bool = False

    @property
    def page_count(self) -> int:
        return self.page_end - self.page_start + 1


@dataclass
class Chunk:
    """A chunk of document content with context."""

    id: str
    primary_section_id: Optional[str]
    subsection_id: Optional[str]
    chunk_number: int
    page_number: int
    raw_content: str
    hierarchy_path: str
    primary_section_number: Optional[int]
    primary_section_name: Optional[str]
    subsection_number: Optional[int]
    subsection_name: Optional[str]
    primary_section_page_count: Optional[int]
    subsection_page_count: Optional[int]
    embedding_prefix: Optional[str] = None
    embedding: Optional[List[float]] = None


@dataclass
class ProcessedDocument:
    """Complete processed document with all structured data."""

    file_info: Any  # FileInfo from stage 1
    structure_type: StructureType
    structure_confidence: str
    page_count: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    sections: List[Section] = field(default_factory=list)
    chunks: List[Chunk] = field(default_factory=list)
    document_summary: str = ""
    document_description: str = ""
    document_usage: str = ""
    summary_embedding: Optional[List[float]] = None
    processing_error: Optional[str] = None

    @property
    def is_valid(self) -> bool:
        """Check if processing was successful."""
        return len(self.chunks) > 0 and self.processing_error is None

    @property
    def primary_section_count(self) -> int:
        return len(self.sections)

    @property
    def subsection_count(self) -> int:
        return sum(len(s.subsections) for s in self.sections)


@dataclass
class ProcessingResult:
    """Result of the processing stage."""

    processed_documents: List[ProcessedDocument] = field(default_factory=list)
    failed_documents: List[ProcessedDocument] = field(default_factory=list)
    total_sections: int = 0
    total_subsections: int = 0
    total_chunks: int = 0
    total_llm_calls: int = 0
    total_embedding_calls: int = 0
    total_cost: float = 0.0


# Processing constants
CLASSIFICATION_PAGES = 100
BATCH_SIZE = 50
MAX_SECTION_PAGES = 100
EMBEDDING_BATCH_SIZE = 100
CHUNK_SUMMARY_BATCH_SIZE = 10
CHUNK_SUMMARY_MAX_CONTENT_TOKENS = 1500
CHUNK_SUMMARY_CONTEXT_TOKENS = 800
MAX_LLM_WORKERS = 4


def resolve_auth_token() -> str:
    """Return an auth token using OPENAI key when available, otherwise OAuth."""
    if config.OPENAI_API_KEY:
        return config.OPENAI_API_KEY
    return fetch_oauth_token()


def _get_model_costs(model_name: str) -> Tuple[float, float]:
    """Get prompt/completion token costs for a model name."""
    if model_name == config.MODEL_SMALL:
        capability = "small"
    elif model_name == config.MODEL_LARGE:
        capability = "large"
    else:
        capability = "embedding"

    settings = config.get_model_settings(capability)
    return settings["prompt_token_cost"], settings["completion_token_cost"]


def _call_llm(
    auth_token: str,
    messages: List[Dict[str, str]],
    model: str,
    temperature: float = 0.0,
    max_tokens: Optional[int] = None,
    response_format: Optional[Dict[str, Any]] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
    tool_choice: Optional[Any] = None,
) -> Tuple[Any, Optional[dict[str, Any]]]:
    """Wrapper around execute_llm_call with model-specific costs."""
    tool_name = "none"
    if tool_choice and isinstance(tool_choice, dict):
        tool_name = tool_choice.get("function", {}).get("name", "auto")
    logger.info(
        "LLM call: model=%s, tool=%s, max_tokens=%s, messages=%d",
        model,
        tool_name,
        max_tokens or "default",
        len(messages),
    )

    prompt_cost, completion_cost = _get_model_costs(model)
    response, usage = execute_llm_call(
        auth_token,
        prompt_token_cost=prompt_cost,
        completion_token_cost=completion_cost,
        messages=messages,
        model=model,
        response_format=response_format,
        temperature=temperature,
        max_tokens=max_tokens,
        tools=tools,
        tool_choice=tool_choice,
    )

    finish_reason = "unknown"
    if hasattr(response, "choices") and response.choices:
        finish_reason = str(response.choices[0].finish_reason)

    if usage:
        logger.info(
            "LLM response: tool=%s, finish=%s, prompt_tokens=%s, completion_tokens=%s, cost=$%.4f",
            tool_name,
            finish_reason,
            usage.get("prompt_tokens"),
            usage.get("completion_tokens"),
            usage.get("cost", 0),
        )

    if finish_reason not in ("stop", "tool_calls"):
        logger.warning(
            "LLM finish_reason=%s (expected stop or tool_calls) for tool=%s — "
            "response may be truncated",
            finish_reason,
            tool_name,
        )

    return response, usage


def _create_embedding(
    auth_token: str,
    text_input: List[str],
    model: Optional[str] = None,
) -> Tuple[List[List[float]], Dict[str, Any]]:
    """Wrapper to generate embeddings using the shared LLM connector."""
    embedding_model = model or config.MODEL_EMBEDDING
    response = execute_llm_call(
        auth_token,
        is_embedding=True,
        input=text_input,
        model=embedding_model,
        timeout=config.REQUEST_TIMEOUT,
    )

    token_count = 0
    if hasattr(response, "usage") and response.usage:
        raw_token_count = getattr(response.usage, "total_tokens", None)
        if raw_token_count is None:
            logger.warning("Embedding response missing total_tokens in usage data")
        token_count = raw_token_count or 0

    prompt_cost, _ = _get_model_costs(config.MODEL_EMBEDDING)
    cost = calculate_token_cost(token_count, 0, prompt_cost, 0)

    embeddings = [item.embedding for item in response.data]
    usage_details = {
        "model": embedding_model,
        "token_count": token_count,
        "cost": cost,
        "response_time_ms": None,
        "embedding_count": len(embeddings),
    }
    return embeddings, usage_details


def _load_prompt(name: str) -> Tuple[str, Optional[Dict[str, Any]], str]:
    """Return system prompt, tool definition, and user prompt for stage 3.

    Raises:
        ValueError: If the prompt is not found in the database.
    """
    system_prompt, tools, user_prompt = get_prompt(
        "stage_3", name, model="doc_refresh"
    )
    tool_def = tools[0] if tools else None
    return system_prompt, tool_def, user_prompt


def _safe_format(template: str, **kwargs: Any) -> str:
    """Replace {key} placeholders in template without disturbing other braces.

    Unlike str.format(), this leaves unknown {placeholders} and literal JSON
    braces intact, which is critical for DB prompts that contain JSON examples.
    """
    for key, value in kwargs.items():
        template = template.replace(f"{{{key}}}", str(value))
    return template


def _parse_tool_arguments(message: Any) -> Optional[Dict[str, Any]]:
    """Extract tool call arguments from a response message."""
    tool_calls = getattr(message, "tool_calls", None) or []
    if not tool_calls:
        return None

    fn = tool_calls[0].function
    raw = fn.arguments
    logger.info(
        "Tool call: %s (%d chars of arguments)",
        fn.name,
        len(raw) if raw else 0,
    )
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning(
            "Failed to parse tool arguments for %s: %s — raw (first 500 chars): %s",
            fn.name,
            exc,
            (raw or "")[:500],
        )
        repaired = _try_repair_json(raw)
        if repaired is not None:
            logger.info("Recovered tool arguments via JSON repair for %s", fn.name)
            return repaired
        return None


def _try_repair_json(raw: str) -> Optional[Dict[str, Any]]:
    """Attempt to fix truncated JSON from tool call arguments."""
    if not raw or not raw.strip():
        return None

    text = raw.rstrip()

    for suffix in ['"}]}', '"}]', '"}', '"}'  , '}]}'  , '}]', '}}', '}']:
        candidate = text + suffix
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue

    return None


def _find_section_title_position(page_text: str, title: str) -> Optional[int]:
    """Find the start-of-line position where a section title appears in page text."""
    words = title.split()
    if not words:
        return None

    md_chars = r'[\*_#\s]*'
    pattern = md_chars + md_chars.join(re.escape(w) for w in words)
    match = re.search(r'(?:^|\n)' + r'[\*_#\d.\s]*' + pattern, page_text, re.IGNORECASE)
    if match:
        pos = match.start()
        if page_text[pos] == '\n':
            pos += 1
        return pos

    plain_pos = page_text.lower().find(title.lower())
    if plain_pos != -1:
        line_start = page_text.rfind('\n', 0, plain_pos)
        return line_start + 1 if line_start != -1 else 0

    return None


def _get_section_page_items(
    pages: List[str], sections: List[Section], section_index: int
) -> List[Tuple[int, str]]:
    """Extract per-page content for a section as (page_number, text) tuples."""
    section = sections[section_index]
    result = []

    for page_num in range(section.page_start, section.page_end + 1):
        page_idx = page_num - 1
        if page_idx < 0 or page_idx >= len(pages):
            continue
        page_text = pages[page_idx]

        if page_num == section.page_start:
            pos = _find_section_title_position(page_text, section.title)
            if pos is not None and pos > 0:
                page_text = page_text[pos:]

        if page_num == section.page_end and section_index + 1 < len(sections):
            next_section = sections[section_index + 1]
            if next_section.page_start == page_num:
                pos = _find_section_title_position(page_text, next_section.title)
                if pos is not None:
                    page_text = page_text[:pos]

        if page_text.strip():
            result.append((page_num, page_text))

    return result


def _get_section_pages(
    pages: List[str], sections: List[Section], section_index: int
) -> List[str]:
    """Extract per-page content for a section, splitting at title boundaries on shared pages."""
    return [text for _, text in _get_section_page_items(pages, sections, section_index)]


def _validate_section_page_numbers(
    pages: List[str], section_breaks: List[SectionBreak]
) -> List[SectionBreak]:
    """Validate and correct section break page numbers by searching for titles in page text."""
    corrected = []
    for sb in section_breaks:
        if sb.inferred:
            corrected.append(sb)
            continue

        search_start = max(0, sb.page_number - 2)
        search_end = min(len(pages), sb.page_number + 1)

        found_page = None
        for page_idx in range(search_start, search_end):
            if _find_section_title_position(pages[page_idx], sb.title) is not None:
                found_page = page_idx + 1
                break

        if found_page is not None and found_page != sb.page_number:
            logger.info(
                "Corrected page number for '%s': %d -> %d",
                sb.title, sb.page_number, found_page,
            )
            corrected.append(
                SectionBreak(
                    page_number=found_page,
                    title=sb.title,
                    level=sb.level,
                    inferred=sb.inferred,
                )
            )
        else:
            corrected.append(sb)

    return corrected


def _strip_markdown_for_embedding(text: str) -> str:
    """Remove markdown formatting for cleaner embedding input."""
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'(?<!\w)_([^_]+)_(?!\w)', r'\1', text)
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\|', ' ', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'-{3,}', '', text)
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()


_BOILERPLATE_SECTIONS = {
    "abstract": {
        "overview": "This section contains the paper's abstract.",
        "key_topics": [],
        "key_metrics": {},
        "key_findings": [],
        "notable_facts": [],
        "not_fully_covered": [],
    },
    "references": {
        "overview": "This section contains the bibliography/references cited in the document.",
        "key_topics": [],
        "key_metrics": {},
        "key_findings": [],
        "notable_facts": [],
        "not_fully_covered": [],
    },
    "bibliography": {
        "overview": "This section contains the bibliography/references cited in the document.",
        "key_topics": [],
        "key_metrics": {},
        "key_findings": [],
        "notable_facts": [],
        "not_fully_covered": [],
    },
    "acknowledgements": {
        "overview": "This section contains acknowledgements of funding and support.",
        "key_topics": [],
        "key_metrics": {},
        "key_findings": [],
        "notable_facts": [],
        "not_fully_covered": [],
    },
    "acknowledgments": {
        "overview": "This section contains acknowledgements of funding and support.",
        "key_topics": [],
        "key_metrics": {},
        "key_findings": [],
        "notable_facts": [],
        "not_fully_covered": [],
    },
    "acknowledgement": {
        "overview": "This section contains acknowledgements of funding and support.",
        "key_topics": [],
        "key_metrics": {},
        "key_findings": [],
        "notable_facts": [],
        "not_fully_covered": [],
    },
}


def _is_boilerplate_section(title: str) -> Optional[Dict[str, Any]]:
    """Return a minimal summary dict if the section title is boilerplate, else None."""
    normalized = re.sub(r'^[\d.\s]+', '', title).strip().lower()
    return _BOILERPLATE_SECTIONS.get(normalized)


def run_stage(
    extracted_documents: List[ExtractedDocument],
) -> ProcessingResult:
    """
    Execute the processing stage.

    Transforms extracted documents into structured hierarchical data.

    Args:
        extracted_documents: List of ExtractedDocument from Stage 2.

    Returns:
        ProcessingResult with processed documents and statistics.
    """
    result = ProcessingResult()

    if not extracted_documents:
        logger.info("No documents to process")
        return result

    logger.info("Processing %d extracted documents", len(extracted_documents))

    for i, extracted in enumerate(extracted_documents, 1):
        logger.info(
            "Processing document %d/%d: %s (%d pages)",
            i,
            len(extracted_documents),
            extracted.file_info.file_name,
            extracted.page_count,
        )

        try:
            auth_token = resolve_auth_token()
            start_time = time.time()
            processed = process_document(extracted, auth_token)
            duration = time.time() - start_time

            if processed.is_valid:
                result.processed_documents.append(processed)
                result.total_sections += len(processed.sections)
                result.total_subsections += processed.subsection_count
                result.total_chunks += len(processed.chunks)
                logger.info(
                    "Processed %s: %d sections, %d subsections, %d chunks (%.1fs)",
                    extracted.file_info.file_name,
                    len(processed.sections),
                    processed.subsection_count,
                    len(processed.chunks),
                    duration,
                )
            else:
                result.failed_documents.append(processed)
                logger.warning(
                    "Failed to process %s: %s",
                    extracted.file_info.file_name,
                    processed.processing_error,
                )

        except Exception as exc:
            logger.error(
                "Error processing %s: %s",
                extracted.file_info.file_name,
                exc,
            )
            result.failed_documents.append(
                ProcessedDocument(
                    file_info=extracted.file_info,
                    structure_type=StructureType.SEMANTIC,
                    structure_confidence="low",
                    page_count=extracted.page_count,
                    processing_error=str(exc),
                )
            )

    # Log summary
    logger.info(
        "Processing complete: %d successful, %d failed, %d sections, %d subsections, %d chunks",
        len(result.processed_documents),
        len(result.failed_documents),
        result.total_sections,
        result.total_subsections,
        result.total_chunks,
    )

    return result


def process_document(
    extracted: ExtractedDocument,
    auth_token: str,
) -> ProcessedDocument:
    """
    Process a single document through all stages.

    Args:
        extracted: ExtractedDocument with pages.
        auth_token: Authentication token for API calls.

    Returns:
        ProcessedDocument with all structured data.
    """
    pages = extracted.pages

    # Initialize result
    processed = ProcessedDocument(
        file_info=extracted.file_info,
        structure_type=StructureType.SEMANTIC,
        structure_confidence="low",
        page_count=len(pages),
    )

    try:
        # Steps 1+2 are independent — run in parallel
        with ThreadPoolExecutor(max_workers=2) as executor:
            metadata_future = executor.submit(
                extract_document_metadata, pages, auth_token
            )
            structure_future = executor.submit(detect_structure, pages, auth_token)

            metadata = metadata_future.result()
            structure_type, confidence, section_breaks, _ = structure_future.result()

        processed.metadata = metadata
        processed.structure_type = structure_type
        processed.structure_confidence = confidence

        # Step 3: Build primary sections with page ranges
        sections = build_primary_sections(pages, section_breaks)

        # Step 4: Analyze subsections within each primary section
        sections = analyze_subsections(pages, sections, auth_token)

        # Step 5: Generate enhanced summaries for sections and subsections
        sections = generate_enhanced_summaries(pages, sections, auth_token)
        processed.sections = sections

        # Step 6: Build complete document summary
        document_summary = build_document_summary(metadata, sections, len(pages))
        processed.document_summary = document_summary

        # Steps 7+8 are independent — run in parallel
        with ThreadPoolExecutor(max_workers=2) as executor:
            fields_future = executor.submit(
                generate_document_fields, metadata, sections, document_summary, auth_token
            )
            embedding_future = executor.submit(
                generate_summary_embedding, document_summary, auth_token
            )

            document_description, document_usage = fields_future.result()
            summary_embedding = embedding_future.result()

        processed.document_description = document_description
        processed.document_usage = document_usage
        processed.summary_embedding = summary_embedding

        # Step 9: Generate chunks with proper section/subsection linkage
        chunks = generate_chunks(pages, sections)
        processed.chunks = chunks

        # Step 9.5: Generate and prepend chunk summary prefixes
        chunks = generate_chunk_summaries(chunks, sections, auth_token)
        processed.chunks = chunks

        # Step 10: Generate chunk embeddings
        chunks = generate_embeddings(chunks, auth_token)
        processed.chunks = chunks

        # Degradation check: if multiple sub-steps produced empty/fallback results,
        # flag the document as degraded even though no single step raised an exception
        degradation_signals = []
        if not processed.metadata:
            degradation_signals.append("empty metadata")
        if processed.structure_type == StructureType.SEMANTIC and processed.structure_confidence == "low":
            if len(pages) > 5:
                degradation_signals.append("default structure classification")
        if processed.summary_embedding is None:
            degradation_signals.append("missing summary embedding")
        if not processed.document_description or processed.document_description == (processed.metadata.get("title", "") or "Unknown"):
            degradation_signals.append("fallback document description")

        if len(degradation_signals) >= 3:
            processed.processing_error = (
                f"Degraded processing: {', '.join(degradation_signals)}"
            )
            logger.error(
                "Document processing degraded for %s: %s",
                processed.file_info.file_name,
                processed.processing_error,
            )

        return processed

    except Exception as exc:
        processed.processing_error = str(exc)
        logger.error("Document processing failed: %s", exc)
        return processed


def extract_document_metadata(
    pages: List[str],
    auth_token: str,
) -> Dict[str, Any]:
    """
    Extract document metadata from first pages using LLM.

    Fields are driven by the metadata_fields.json config file.

    Args:
        pages: List of page texts.
        auth_token: Authentication token.

    Returns:
        Dict with metadata fields from config (e.g. title, authors, etc.).
    """
    if not pages:
        return {}

    fields_config = _load_metadata_fields_config()

    first_pages = "\n\n---PAGE BREAK---\n\n".join(pages[:5])
    first_pages = truncate_to_tokens(first_pages, 9000)

    system_prompt, _, user_template = _load_prompt("extract_document_metadata")

    tool_def = _build_metadata_tool_schema(fields_config)

    try:
        user_prompt = _safe_format(user_template, page_excerpt=first_pages)
    except (KeyError, IndexError):
        user_prompt = _build_metadata_user_prompt(fields_config, first_pages)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        response, _ = _call_llm(
            auth_token,
            messages,
            model=config.MODEL_LARGE,
            temperature=0.1,
            tools=[tool_def],
            tool_choice={"type": "function", "function": {"name": "extract_metadata"}},
        )
        message = response.choices[0].message
        args = _parse_tool_arguments(message)
        if args:
            return args

        logger.warning("Metadata extraction returned no tool call")
    except (OpenAIConnectorError, ConnectionError, OSError) as exc:
        logger.warning(
            "Metadata extraction failed due to network/API error, "
            "continuing with empty metadata: %s",
            exc,
        )
    except Exception as exc:
        logger.warning("Metadata extraction failed: %s", exc)
    return {}


def detect_structure(
    pages: List[str],
    auth_token: str,
) -> Tuple[StructureType, str, List[SectionBreak], Dict[str, Any]]:
    """
    Detect document structure and section breaks.

    Args:
        pages: List of page texts.
        auth_token: Authentication token.

    Returns:
        Tuple of (structure_type, confidence, section_breaks, classification_info).
    """
    if not pages:
        return StructureType.SEMANTIC, "low", [], {}

    # Phase 1: Classify document using first N pages
    classification_pages = pages[:CLASSIFICATION_PAGES]
    classification = classify_document(classification_pages, auth_token)

    structure_type = _normalize_structure_type(classification.get("structure_type", "semantic"))
    confidence = classification.get("confidence", "low")
    has_toc = classification.get("has_toc", False)
    toc_sections = classification.get("toc_sections", [])

    logger.info(
        "Document classified as %s (confidence: %s, has_toc: %s)",
        structure_type.value,
        confidence,
        has_toc,
    )

    # Phase 2: Detect sections in batches
    all_sections = []
    previous_context = ""

    num_batches = (len(pages) + BATCH_SIZE - 1) // BATCH_SIZE
    for batch_num in range(num_batches):
        start_idx = batch_num * BATCH_SIZE
        end_idx = min(start_idx + BATCH_SIZE, len(pages))
        batch_pages = pages[start_idx:end_idx]
        start_page = start_idx + 1
        end_page = end_idx

        logger.debug(
            "Processing batch %d/%d (pages %d-%d)",
            batch_num + 1,
            num_batches,
            start_page,
            end_page,
        )

        sections, continued = detect_sections_batch(
            batch_pages,
            start_page,
            end_page,
            structure_type,
            previous_context,
            auth_token,
        )

        all_sections.extend(sections)

        if sections:
            last = sections[-1]
            previous_context = f"Previous section: '{last.title}' on page {last.page_number}"
        elif continued:
            previous_context = f"Continuing section: '{continued}'"

    logger.info(
        "Detected %d raw sections across %d batches", len(all_sections), num_batches
    )

    # Phase 3: Consolidate and correct using LLM
    final_sections = consolidate_sections_llm(
        all_sections,
        len(pages),
        structure_type,
        confidence,
        has_toc,
        toc_sections,
        auth_token,
    )

    if not final_sections:
        raise RuntimeError(
            "LLM section consolidation returned no sections. "
            "Cannot proceed without valid document structure."
        )

    # Validate section page numbers against actual page text
    final_sections = _validate_section_page_numbers(pages, final_sections)

    # Ensure first section starts at page 1
    if not final_sections or final_sections[0].page_number > 1:
        final_sections.insert(
            0,
            SectionBreak(
                page_number=1,
                title="Document Start",
                level=1,
                inferred=True,
            ),
        )

    logger.info("Final structure: %d sections after consolidation", len(final_sections))

    classification_info = {
        "has_toc": has_toc,
        "toc_sections": toc_sections,
    }
    return structure_type, confidence, final_sections, classification_info


def classify_document(pages: List[str], auth_token: str) -> Dict[str, Any]:
    """Classify document structure type using prompt from database."""
    default_result = {
        "structure_type": "semantic",
        "confidence": "low",
        "has_toc": False,
        "toc_sections": [],
    }
    pages_content = format_pages_for_prompt(pages)

    system_prompt, tool_def, user_template = _load_prompt("classify_document")

    if not tool_def:
        raise ValueError(
            "classify_document prompt has no tool_definition in database"
        )

    try:
        user_content = _safe_format(
            user_template,
            page_count=len(pages),
            pages_content=pages_content,
        )
    except Exception as exc:
        logger.warning("Classification prompt formatting failed: %s", exc)
        return default_result

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    tools = [tool_def]
    tool_choice = {"type": "function", "function": {"name": "classify_document_structure"}}

    try:
        response, _ = _call_llm(
            auth_token,
            messages,
            model=config.MODEL_SMALL,
            temperature=0.1,
            tools=tools,
            tool_choice=tool_choice,
        )
        message = response.choices[0].message
        args = _parse_tool_arguments(message)
        if args:
            return args

        logger.warning("Classification returned no tool call")
    except (OpenAIConnectorError, ConnectionError, OSError):
        raise
    except Exception as exc:
        logger.warning("Classification failed (malformed response): %s", exc)
        return default_result
    return default_result


def detect_sections_batch(
    pages: List[str],
    start_page: int,
    end_page: int,
    structure_type: StructureType,
    previous_context: str,
    auth_token: str,
) -> Tuple[List[SectionBreak], Optional[str]]:
    """Detect section breaks in a batch of pages using prompts from database."""
    pages_content = format_pages_for_prompt(pages, start_page)

    system_prompt, tool_def, user_template = _load_prompt("detect_sections_batch")

    if not tool_def:
        raise ValueError(
            "detect_sections_batch prompt has no tool_definition in database"
        )

    guidance_name = f"structure_guidance_{structure_type.value}"
    _, _, structure_guidance = _load_prompt(guidance_name)
    if not structure_guidance:
        _, _, structure_guidance = _load_prompt("structure_guidance_semantic")

    try:
        user_content = _safe_format(
            user_template,
            structure_type=structure_type.value,
            previous_context=previous_context or "First batch - no previous sections",
            start_page=start_page,
            end_page=end_page,
            pages_content=pages_content,
            structure_guidance=structure_guidance or "",
        )
    except Exception as exc:
        logger.warning(
            "Section detection prompt formatting failed for pages %d-%d: %s",
            start_page,
            end_page,
            exc,
        )
        return [], None

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    tools = [tool_def]
    tool_choice = {"type": "function", "function": {"name": "detect_section_breaks"}}

    try:
        response, _ = _call_llm(
            auth_token,
            messages,
            model=config.MODEL_SMALL,
            temperature=0.1,
            tools=tools,
            tool_choice=tool_choice,
        )
        message = response.choices[0].message
        args = _parse_tool_arguments(message)
        if args:
            section_breaks = []
            for section in args.get("sections", []):
                page_number = section.get("page_number")
                title = section.get("title", "")
                if page_number is None:
                    continue
                section_breaks.append(
                    SectionBreak(
                        page_number=page_number,
                        title=title,
                        level=section.get("level", 1),
                    )
                )

            return section_breaks, args.get("continued_section_title")

        logger.warning(
            "Section detection returned no tool call for pages %d-%d", start_page, end_page
        )
    except (OpenAIConnectorError, ConnectionError, OSError):
        raise
    except Exception as exc:
        logger.warning(
            "Section detection failed for pages %d-%d (malformed response): %s",
            start_page,
            end_page,
            exc,
        )
        return [], None
    return [], None


def consolidate_sections_llm(
    sections: List[SectionBreak],
    total_pages: int,
    structure_type: StructureType,
    confidence: str,
    has_toc: bool,
    toc_sections: List[str],
    auth_token: str,
) -> List[SectionBreak]:
    """Consolidate section breaks using prompts from database."""
    if not sections:
        return []

    system_prompt, tool_def, user_template = _load_prompt("consolidate_structure")

    if not tool_def:
        raise ValueError(
            "consolidate_structure prompt has no tool_definition in database"
        )

    sections_text = "\n".join(
        f"- Page {s.page_number}: {s.title}"
        for s in sorted(sections, key=lambda x: x.page_number)
    )

    toc_info = ""
    if toc_sections:
        toc_info = (
            "<toc_sections>\n"
            + "\n".join(f"- {s}" for s in toc_sections)
            + "\n</toc_sections>"
        )

    fallback_sections = sorted(sections, key=lambda s: s.page_number)

    try:
        user_content = _safe_format(
            user_template,
            structure_type=structure_type.value,
            confidence=confidence,
            total_pages=total_pages,
            has_toc=has_toc,
            toc_info=toc_info,
            all_sections=sections_text,
        )
    except Exception as exc:
        logger.warning(
            "Consolidation prompt formatting failed: %s — using unconsolidated sections",
            exc,
        )
        return fallback_sections

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    tools = [tool_def]
    tool_choice = {"type": "function", "function": {"name": "consolidate_sections"}}

    try:
        response, _ = _call_llm(
            auth_token,
            messages,
            model=config.MODEL_LARGE,
            temperature=0.1,
            tools=tools,
            tool_choice=tool_choice,
        )
        message = response.choices[0].message
        args = _parse_tool_arguments(message)

        if args:
            raw_sections = args.get("sections", [])
            dropped = [s for s in raw_sections if s.get("page_number") is None]
            if dropped:
                logger.warning(
                    "Dropped %d sections with missing page_number from consolidation: %s",
                    len(dropped),
                    [s.get("title", "<no title>") for s in dropped],
                )

            consolidated = [
                SectionBreak(
                    page_number=s.get("page_number"),
                    title=s.get("title", ""),
                    level=s.get("level", 1),
                )
                for s in raw_sections
                if s.get("page_number") is not None
            ]

            corrections = args.get("corrections_made", [])
            if corrections:
                logger.info(
                    "LLM consolidation made %d corrections: %s",
                    len(corrections),
                    corrections[:3],
                )

            if consolidated:
                return sorted(consolidated, key=lambda s: s.page_number)

            logger.warning(
                "LLM consolidation returned empty sections — "
                "using unconsolidated sections"
            )
            return fallback_sections

        logger.warning(
            "LLM consolidation returned no tool call — "
            "using unconsolidated sections"
        )
        return fallback_sections

    except (OpenAIConnectorError, ConnectionError, OSError):
        raise
    except Exception as exc:
        logger.warning(
            "LLM consolidation failed: %s — using unconsolidated sections", exc
        )
        return fallback_sections


def build_primary_sections(
    pages: List[str],
    section_breaks: List[SectionBreak],
) -> List[Section]:
    """Build Section objects with page ranges derived from section break positions.

    Page ranges extend each section from its start page through to the page
    where the next section begins (inclusive), so sections sharing a page both
    claim that page. The last section extends to the final page.
    """
    if not section_breaks:
        return []

    sections = []
    total_pages = len(pages)

    for i, sb in enumerate(section_breaks):
        page_start = sb.page_number
        if i + 1 < len(section_breaks):
            page_end = section_breaks[i + 1].page_number
        else:
            page_end = total_pages
        page_end = max(page_end, page_start)

        section = Section(
            id=str(uuid.uuid4()),
            sequence_number=i + 1,
            title=sb.title,
            page_start=page_start,
            page_end=page_end,
            inferred=sb.inferred,
        )
        sections.append(section)

    logger.info("Built %d primary sections", len(sections))
    return sections


def analyze_subsections(
    pages: List[str],
    sections: List[Section],
    auth_token: str,
) -> List[Section]:
    """
    Analyze each primary section and identify subsections.

    Creates Subsection objects for each level-2 section found.
    Eligible sections are analyzed in parallel using a thread pool.
    """
    if not sections:
        return sections

    logger.info("Analyzing subsections for %d primary sections", len(sections))

    system_prompt, tool_def, user_template = _load_prompt("analyze_subsections")

    if not tool_def:
        raise ValueError(
            "analyze_subsections prompt has no tool_definition in database"
        )

    tools = [tool_def]
    tool_choice = {"type": "function", "function": {"name": "analyze_subsections"}}

    eligible = [
        (idx, section)
        for idx, section in enumerate(sections)
        if section.page_end - section.page_start + 1 > 1
    ]

    def _analyze_one(idx: int, section: Section) -> List[Subsection]:
        """Analyze subsections for a single section."""
        section_pages = _get_section_pages(pages, sections, idx)
        section_content = "\n\n---PAGE BREAK---\n\n".join(section_pages)
        section_content = truncate_to_tokens(section_content, 12000)

        user_prompt = _safe_format(
            user_template,
            section_title=section.title,
            page_start=section.page_start,
            page_end=section.page_end,
            section_content=section_content,
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        response, _ = _call_llm(
            auth_token,
            messages,
            model=config.MODEL_SMALL,
            temperature=0.2,
            tools=tools,
            tool_choice=tool_choice,
        )
        message = response.choices[0].message
        args = _parse_tool_arguments(message)
        if not args:
            logger.warning(
                "Subsection analysis returned no tool call for %s", section.title
            )
            return []

        subsections_data = args.get("subsections", [])
        logger.debug(
            "Found %d subsections in %s", len(subsections_data), section.title
        )

        subsections = []
        for seq_num, sub_data in enumerate(subsections_data, 1):
            subsection = Subsection(
                id=str(uuid.uuid4()),
                parent_section_id=section.id,
                sequence_number=seq_num,
                title=sub_data.get("title", f"Subsection {seq_num}"),
                page_start=max(
                    sub_data.get("page_start", section.page_start),
                    section.page_start,
                ),
                page_end=min(
                    sub_data.get("page_end", section.page_end),
                    section.page_end,
                ),
            )
            subsections.append(subsection)

        return subsections

    failed_count = 0

    with ThreadPoolExecutor(max_workers=MAX_LLM_WORKERS) as executor:
        futures = {
            executor.submit(_analyze_one, idx, section): section
            for idx, section in eligible
        }
        for future in as_completed(futures):
            section = futures[future]
            try:
                subsections = future.result()
                section.subsections = subsections
            except (OpenAIConnectorError, ConnectionError, OSError):
                raise
            except Exception as exc:
                logger.warning(
                    "Subsection analysis failed for %s: %s", section.title, exc
                )
                failed_count += 1

    if len(eligible) > 0 and failed_count == len(eligible):
        logger.error(
            "Subsection analysis failed for ALL %d eligible sections", len(eligible)
        )

    total_subsections = sum(len(s.subsections) for s in sections)
    logger.info("Identified %d subsections across all primary sections", total_subsections)
    return sections


def generate_enhanced_summaries(
    pages: List[str],
    sections: List[Section],
    auth_token: str,
) -> List[Section]:
    """
    Generate enhanced JSON summaries for sections and subsections.

    Non-boilerplate sections are summarized in parallel using a thread pool.
    Each summary includes overview, key_topics, key_metrics, key_findings,
    and notable_facts.
    """
    if not sections:
        return sections

    logger.info("Generating enhanced summaries for %d sections", len(sections))

    llm_indices = []
    for i, section in enumerate(sections):
        boilerplate = _is_boilerplate_section(section.title)
        if boilerplate is not None:
            logger.info("Using boilerplate summary for section: %s", section.title)
            section.summary = boilerplate
        else:
            llm_indices.append(i)

    if not llm_indices:
        return sections

    def _summarize_one(idx: int) -> Tuple[int, Dict[str, Any]]:
        """Generate summary for a single section."""
        section = sections[idx]
        section_pages = _get_section_pages(pages, sections, idx)
        logger.info(
            "Summarizing section %d/%d: '%s' (%d pages)",
            idx + 1,
            len(sections),
            section.title,
            len(section_pages),
        )
        summary = generate_section_summary_json(
            section_pages, section.title, section.page_start, section.page_end, auth_token
        )
        is_fallback = summary.get("is_fallback", False)
        logger.info(
            "Summary for '%s': %d topics, %d findings%s",
            section.title,
            len(summary.get("key_topics", [])),
            len(summary.get("key_findings", [])),
            " (FALLBACK)" if is_fallback else "",
        )
        return idx, summary

    with ThreadPoolExecutor(max_workers=MAX_LLM_WORKERS) as executor:
        futures = {
            executor.submit(_summarize_one, idx): idx
            for idx in llm_indices
        }
        for future in as_completed(futures):
            try:
                idx, summary = future.result()
                sections[idx].summary = summary
            except (OpenAIConnectorError, ConnectionError, OSError):
                raise
            except Exception as exc:
                idx = futures[future]
                logger.error(
                    "Summary generation failed for section %s: %s",
                    sections[idx].title,
                    exc,
                )

    fallback_count = sum(
        1 for s in sections
        if s.summary and s.summary.get("is_fallback")
    )
    if fallback_count > 0:
        logger.warning(
            "%d/%d sections used fallback summaries", fallback_count, len(sections)
        )

    return sections


def generate_section_summary_json(
    pages: List[str],
    title: str,
    page_start: int,
    page_end: int,
    auth_token: str,
) -> Dict[str, Any]:
    """
    Generate an enhanced JSON summary for a section.

    Returns dict with overview, key_topics, key_metrics, key_findings, notable_facts.
    """
    section_content = "\n\n---PAGE BREAK---\n\n".join(pages)

    system_prompt, tool_def, user_template = _load_prompt("generate_section_summary_json")

    if not tool_def:
        raise ValueError(
            "generate_section_summary_json prompt has no tool_definition in database"
        )

    default_summary = {
        "overview": f"Summary of {title}",
        "key_topics": [],
        "key_metrics": {},
        "key_findings": [],
        "notable_facts": [],
        "not_fully_covered": [],
        "is_fallback": True,
    }

    try:
        user_prompt = _safe_format(
            user_template,
            title=title,
            page_start=page_start,
            page_end=page_end,
            section_content=section_content,
        )
    except Exception as exc:
        logger.error("Summary prompt formatting failed for %s: %s", title, exc)
        return default_summary

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        response, _ = _call_llm(
            auth_token,
            messages,
            model=config.MODEL_LARGE,
            temperature=0.2,
            tools=[tool_def],
            tool_choice={
                "type": "function",
                "function": {"name": "generate_section_summary"},
            },
        )
        message = response.choices[0].message
        args = _parse_tool_arguments(message)
        if args:
            return args
        logger.error("Summary generation returned no tool call for %s", title)
    except (OpenAIConnectorError, ConnectionError, OSError):
        raise
    except Exception as exc:
        logger.error("Summary generation failed for %s: %s", title, exc)
    return default_summary


def build_document_summary(
    metadata: Dict[str, Any],
    sections: List[Section],
    page_count: int,
) -> str:
    """
    Build complete document summary with metadata header and all section summaries.
    """
    parts = []

    # Metadata header - iterate over whatever keys exist in the dict
    parts.append("# Document Metadata")
    skip_keys = {"abstract"}
    for key, value in metadata.items():
        if key in skip_keys or not value:
            continue
        if isinstance(value, list):
            parts.append(f"{key.replace('_', ' ').title()}: {', '.join(str(v) for v in value)}")
        else:
            parts.append(f"{key.replace('_', ' ').title()}: {value}")
    parts.append(f"Pages: {page_count}")
    parts.append("")

    # Abstract if available
    abstract = metadata.get("abstract", "")
    if abstract:
        parts.append("# Abstract")
        parts.append(str(abstract))
        parts.append("")

    # Section summaries
    parts.append("# Section Summaries")
    parts.append("")

    for section in sections:
        # Primary section header
        parts.append(
            f"## {section.sequence_number}. {section.title} (pages {section.page_start}-{section.page_end})"
        )

        # Section summary content (from JSON)
        if section.summary:
            if section.summary.get("overview"):
                parts.append(f"**Overview:** {section.summary['overview']}")

            if section.summary.get("key_topics"):
                topics = ", ".join(section.summary["key_topics"])
                parts.append(f"**Key Topics:** {topics}")

            if section.summary.get("key_metrics"):
                raw = section.summary["key_metrics"]
                if isinstance(raw, dict):
                    metrics = "; ".join(f"{k}: {v}" for k, v in raw.items())
                else:
                    metrics = "; ".join(str(m) for m in raw)
                parts.append(f"**Key Metrics:** {metrics}")

            if section.summary.get("key_findings"):
                for finding in section.summary["key_findings"]:
                    parts.append(f"- {finding}")

            if section.summary.get("notable_facts"):
                parts.append("**Notable Facts:**")
                for fact in section.summary["notable_facts"]:
                    parts.append(f"- {fact}")

            if section.summary.get("not_fully_covered"):
                parts.append("**Not Fully Covered:**")
                for item in section.summary["not_fully_covered"]:
                    parts.append(f"- {item}")

        # Subsection listing (titles and page ranges only)
        if section.subsections:
            parts.append("**Subsections:**")
            for sub in section.subsections:
                parts.append(
                    f"- {section.sequence_number}.{sub.sequence_number} {sub.title} (pages {sub.page_start}-{sub.page_end})"
                )

        parts.append("")

    return "\n".join(parts)


def generate_document_fields(
    metadata: Dict[str, Any],
    sections: List[Section],
    document_summary: str,
    auth_token: str,
) -> Tuple[str, str]:
    """
    Generate document description and usage fields using LLM.

    Args:
        metadata: Extracted document metadata dict.
        sections: List of processed sections with summaries.
        document_summary: Complete document summary for LLM context.
        auth_token: Authentication token for API calls.

    Returns:
        Tuple of (document_description, document_usage).
    """
    title = metadata.get("title", "") or "Unknown"
    fallback_description = title
    fallback_usage = ""

    system_prompt, tool_def, user_template = _load_prompt("generate_document_fields")

    truncated_summary = truncate_to_tokens(document_summary, 6000)
    user_prompt = _safe_format(user_template, document_summary=truncated_summary)

    try:
        response, _ = _call_llm(
            auth_token,
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            model=config.MODEL_SMALL,
            temperature=0.2,
            tools=[tool_def],
            tool_choice={"type": "function", "function": {"name": "generate_document_fields"}},
        )
        message = response.choices[0].message
        args = _parse_tool_arguments(message)
        if args:
            return (
                args.get("document_description", fallback_description),
                args.get("document_usage", fallback_usage),
            )
        logger.error("Document fields generation returned no tool call")
    except (OpenAIConnectorError, ConnectionError, OSError):
        raise
    except Exception as exc:
        logger.error("Document fields generation failed, using fallback: %s", exc)

    return fallback_description, fallback_usage


def generate_summary_embedding(
    document_summary: str,
    auth_token: str,
) -> Optional[List[float]]:
    """Generate embedding for the document summary."""
    if not document_summary:
        return None

    try:
        clean_summary = _strip_markdown_for_embedding(document_summary)
        token_count = count_tokens(clean_summary)
        if token_count > 8000:
            logger.warning(
                "Document summary exceeds 8000 tokens (%d tokens), "
                "embedding may be truncated by the model",
                token_count,
            )
        embeddings, _ = _create_embedding(
            auth_token,
            [clean_summary],
            model=config.MODEL_EMBEDDING,
        )
        return embeddings[0]
    except (OpenAIConnectorError, ConnectionError, OSError):
        raise
    except Exception as exc:
        logger.error("Summary embedding generation failed: %s", exc)
        return None


def generate_chunks(pages: List[str], sections: List[Section]) -> List[Chunk]:
    """Generate one chunk per page, annotated with section and subsection metadata.

    Each page within a section becomes its own chunk with an independent
    embedding. On shared boundary pages the content is trimmed at section
    title positions so each chunk contains only its section's text. Subsection
    assignment is determined by page range overlap.
    """
    if not pages:
        return []

    chunks = []
    chunk_index = 0
    blank_page_count = 0
    total_page_count = 0

    for i, section in enumerate(sections):
        page_items = _get_section_page_items(pages, sections, i)

        for page_num, page_content in page_items:
            total_page_count += 1
            if not page_content.strip():
                blank_page_count += 1
                continue

            subsection = None
            for sub in section.subsections:
                if sub.page_start <= page_num <= sub.page_end:
                    subsection = sub
                    break

            if subsection:
                hierarchy_path = f"{section.title} > {subsection.title}"
            else:
                hierarchy_path = section.title

            chunk = Chunk(
                id=str(uuid.uuid4()),
                primary_section_id=section.id,
                subsection_id=subsection.id if subsection else None,
                chunk_number=chunk_index,
                page_number=page_num,
                raw_content=page_content,
                hierarchy_path=hierarchy_path,
                primary_section_number=section.sequence_number,
                primary_section_name=section.title,
                subsection_number=subsection.sequence_number if subsection else None,
                subsection_name=subsection.title if subsection else None,
                primary_section_page_count=section.page_count,
                subsection_page_count=subsection.page_count if subsection else None,
            )
            chunks.append(chunk)
            chunk_index += 1

    if blank_page_count > 0:
        blank_ratio = blank_page_count / total_page_count if total_page_count else 0
        if blank_ratio >= 0.5:
            logger.warning(
                "High blank page ratio: %d/%d pages (%.0f%%) were blank — possible extraction issue",
                blank_page_count,
                total_page_count,
                blank_ratio * 100,
            )
        else:
            logger.info(
                "Skipped %d blank pages out of %d total", blank_page_count, total_page_count
            )

    logger.info("Generated %d chunks", len(chunks))
    return chunks


def _build_section_context(sections: List[Section]) -> str:
    """Build a compact document outline from section titles and overview summaries."""
    min_per_section_tokens = 50
    per_section_budget = max(
        min_per_section_tokens,
        CHUNK_SUMMARY_CONTEXT_TOKENS // max(len(sections), 1),
    )
    lines = []
    for section in sections:
        overview = section.summary.get("overview", "") if section.summary else ""
        overview_snippet = truncate_to_tokens(overview, per_section_budget)
        line = f"- Section {section.sequence_number}: {section.title}"
        if overview_snippet:
            line += f" — {overview_snippet}"
        lines.append(line)

        for sub in section.subsections:
            lines.append(f"  - {section.sequence_number}.{sub.sequence_number}: {sub.title}")

    result = "\n".join(lines)
    return truncate_to_tokens(result, CHUNK_SUMMARY_CONTEXT_TOKENS)


def _generate_chunk_summary_batch(
    chunks: List[Chunk],
    section_context: str,
    auth_token: str,
) -> Dict[int, str]:
    """Send a batch of chunks to MODEL_SMALL and return chunk_number-to-summary mapping."""
    system_prompt, tool_def, user_template = _load_prompt("generate_chunk_summaries")

    if not tool_def:
        raise ValueError(
            "generate_chunk_summaries prompt has no tool_definition in database"
        )

    chunk_blocks_list = []
    for chunk in chunks:
        content = truncate_to_tokens(chunk.raw_content, CHUNK_SUMMARY_MAX_CONTENT_TOKENS)
        section_name = chunk.primary_section_name or "Unknown"
        chunk_blocks_list.append(
            f"<chunk chunk_number=\"{chunk.chunk_number}\" "
            f"section=\"{section_name}\" page=\"{chunk.page_number}\">\n"
            f"{content}\n</chunk>"
        )
    chunk_blocks_text = "\n\n".join(chunk_blocks_list)

    user_prompt = _safe_format(
        user_template,
        section_context=section_context,
        chunk_blocks=chunk_blocks_text,
    )

    response, _ = _call_llm(
        auth_token,
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        model=config.MODEL_SMALL,
        temperature=0.2,
        max_tokens=4096,
        tools=[tool_def],
        tool_choice={"type": "function", "function": {"name": "provide_chunk_summaries"}},
    )

    message = response.choices[0].message
    args = _parse_tool_arguments(message)
    if not args:
        logger.warning(
            "Chunk summary batch returned no tool call for %d chunks",
            len(chunks),
        )
        return {}

    result = {}
    dropped_count = 0
    for item in args.get("summaries", []):
        cn = item.get("chunk_number")
        summary = item.get("summary", "")
        if cn is not None and summary:
            result[cn] = summary.strip()
        else:
            dropped_count += 1

    if dropped_count > 0:
        logger.warning(
            "Dropped %d chunk summaries from LLM response (missing chunk_number or empty summary)",
            dropped_count,
        )

    logger.info(
        "Chunk summary batch: %d/%d chunks got summaries",
        len(result),
        len(chunks),
    )
    return result


def generate_chunk_summaries(
    chunks: List[Chunk],
    sections: List[Section],
    auth_token: str,
) -> List[Chunk]:
    """Generate concise summaries and prefix them to chunk content for better embeddings.

    Batches non-boilerplate chunks, sends each batch to the LLM in parallel,
    and prepends the summary in square brackets to raw_content. Boilerplate chunks
    (Abstract, References, Acknowledgements) are skipped. On failure, chunks keep
    their original content.

    Args:
        chunks: List of Chunk objects from generate_chunks.
        sections: List of Section objects with summaries.
        auth_token: Authentication token for API calls.

    Returns:
        The same list of Chunk objects with embedding_prefix set where applicable.
    """
    if not chunks:
        return chunks

    section_context = _build_section_context(sections)

    eligible_chunks = [
        c for c in chunks
        if not _is_boilerplate_section(c.primary_section_name or "")
    ]

    if not eligible_chunks:
        logger.info("No eligible chunks for summary prefixes (all boilerplate)")
        return chunks

    logger.info(
        "Generating summary prefixes for %d/%d chunks (%d boilerplate skipped)",
        len(eligible_chunks),
        len(chunks),
        len(chunks) - len(eligible_chunks),
    )

    batches = [
        eligible_chunks[i : i + CHUNK_SUMMARY_BATCH_SIZE]
        for i in range(0, len(eligible_chunks), CHUNK_SUMMARY_BATCH_SIZE)
    ]
    total_batches = len(batches)
    failed_batches = 0
    summaries: Dict[int, str] = {}

    with ThreadPoolExecutor(max_workers=MAX_LLM_WORKERS) as executor:
        futures = {
            executor.submit(
                _generate_chunk_summary_batch, batch, section_context, auth_token
            ): batch_idx
            for batch_idx, batch in enumerate(batches)
        }
        for future in as_completed(futures):
            batch_idx = futures[future]
            try:
                batch_result = future.result()
                summaries.update(batch_result)
            except (OpenAIConnectorError, ConnectionError, OSError):
                raise
            except Exception as exc:
                failed_batches += 1
                logger.warning(
                    "Chunk summary batch %d failed, skipping %d chunks: %s",
                    batch_idx + 1,
                    len(batches[batch_idx]),
                    exc,
                )

    missing = [c for c in eligible_chunks if c.chunk_number not in summaries]
    if missing:
        logger.info("Retrying %d chunks that were missed in initial pass", len(missing))
        retry_batches = [
            missing[i : i + CHUNK_SUMMARY_BATCH_SIZE]
            for i in range(0, len(missing), CHUNK_SUMMARY_BATCH_SIZE)
        ]
        with ThreadPoolExecutor(max_workers=MAX_LLM_WORKERS) as executor:
            futures = {
                executor.submit(
                    _generate_chunk_summary_batch, batch, section_context, auth_token
                ): batch_idx
                for batch_idx, batch in enumerate(retry_batches)
            }
            for future in as_completed(futures):
                batch_idx = futures[future]
                try:
                    batch_result = future.result()
                    summaries.update(batch_result)
                except (OpenAIConnectorError, ConnectionError, OSError):
                    raise
                except Exception as exc:
                    logger.warning(
                        "Retry batch failed, %d chunks remain without summaries: %s",
                        len(retry_batches[batch_idx]),
                        exc,
                    )

    if failed_batches == total_batches and total_batches > 0:
        raise RuntimeError(
            f"All {total_batches} chunk summary batches failed — "
            "LLM may be unavailable"
        )

    prefixed_count = 0
    for chunk in chunks:
        summary = summaries.get(chunk.chunk_number)
        if summary:
            chunk.embedding_prefix = f"[{summary}]\n\n"
            prefixed_count += 1

    logger.info("Set embedding prefixes for %d/%d chunks", prefixed_count, len(eligible_chunks))
    return chunks


def generate_embeddings(chunks: List[Chunk], auth_token: str) -> List[Chunk]:
    """Generate embeddings for all chunks."""
    if not chunks:
        return chunks

    logger.info("Generating embeddings for %d chunks", len(chunks))

    for i in range(0, len(chunks), EMBEDDING_BATCH_SIZE):
        batch = chunks[i : i + EMBEDDING_BATCH_SIZE]
        texts = [
            truncate_to_tokens(
                (c.embedding_prefix or "") + _strip_markdown_for_embedding(c.raw_content),
                8000,
            )
            for c in batch
        ]

        try:
            embeddings, _ = _create_embedding(
                auth_token,
                texts,
                model=config.MODEL_EMBEDDING,
            )

            if len(embeddings) != len(batch):
                raise ValueError(
                    f"Embedding count mismatch: got {len(embeddings)} "
                    f"for {len(batch)} chunks"
                )

            for j, embedding in enumerate(embeddings):
                batch[j].embedding = embedding

        except Exception as exc:
            logger.error("Embedding batch %d failed: %s", i // EMBEDDING_BATCH_SIZE, exc)
            raise RuntimeError(
                f"Embedding generation failed for batch {i // EMBEDDING_BATCH_SIZE}: {exc}"
            ) from exc

    embedded_count = sum(1 for c in chunks if c.embedding is not None)
    logger.info("Generated %d/%d embeddings", embedded_count, len(chunks))

    return chunks


def format_pages_for_prompt(pages: List[str], start_page: int = 1) -> str:
    """Format pages for LLM prompt."""
    formatted = []
    for i, page in enumerate(pages):
        page_num = start_page + i
        formatted.append(f"--- PAGE {page_num} ---\n{page}\n")
    return "\n".join(formatted)
