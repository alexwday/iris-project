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
8. Embedding Generation - Generate embeddings for chunks and summary

Functions:
    run_stage: Execute the processing stage
"""

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from ..connections.llm import calculate_token_cost, execute_llm_call
from ..connections.oauth import fetch_oauth_token
from ..stages.stage_2_extract import ExtractedDocument
from ..utils.env_config import config
from ..utils.process_monitoring import get_process_monitor
from ..utils.prompt_loader import fetch_prompt_raw

logger = logging.getLogger(__name__)


class StructureType(str, Enum):
    """Document structure classification types."""

    CHAPTERS = "chapters"
    SECTIONS = "sections"
    TOPIC_BASED = "topic_based"
    SEMANTIC = "semantic"


@dataclass
class SectionBreak:
    """A detected section break in the document."""

    page_number: int
    title: str
    level: int = 1
    inferred: bool = False


@dataclass
class DocumentMetadata:
    """Extracted document metadata."""

    title: str = ""
    authors: List[str] = field(default_factory=list)
    publication_date: str = ""
    publication_venue: str = ""
    abstract: str = ""


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
    embedding: Optional[List[float]] = None


@dataclass
class ProcessedDocument:
    """Complete processed document with all structured data."""

    file_info: Any  # FileInfo from stage 1
    structure_type: StructureType
    structure_confidence: str
    page_count: int
    metadata: DocumentMetadata = field(default_factory=DocumentMetadata)
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


def _resolve_auth_token() -> str:
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
    prompt_cost, completion_cost = _get_model_costs(model)
    return execute_llm_call(
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
        token_count = getattr(response.usage, "total_tokens", 0) or 0

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
    """Return system prompt, tool definition, and user prompt for stage 3."""
    try:
        return fetch_prompt_raw("stage_3", name, model="doc_refresh")
    except Exception as exc:
        logger.warning("Prompt not found for stage_3/%s: %s", name, exc)
        return "", None, ""


def _parse_tool_arguments(message: Any) -> Optional[Dict[str, Any]]:
    """Extract tool call arguments from a response message."""
    tool_calls = getattr(message, "tool_calls", None) or []
    if not tool_calls:
        return None

    try:
        return json.loads(tool_calls[0].function.arguments)
    except (ValueError, TypeError, AttributeError) as exc:
        logger.warning("Failed to parse tool arguments: %s", exc)
        return None


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
    monitor = get_process_monitor()
    monitor.start_stage("stage_3_process")

    result = ProcessingResult()

    if not extracted_documents:
        logger.info("No documents to process")
        monitor.end_stage("stage_3_process", "completed")
        return result

    # Get auth token once for all API calls
    auth_token = _resolve_auth_token()

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

    monitor.add_stage_details(
        "stage_3_process",
        documents_processed=len(result.processed_documents),
        documents_failed=len(result.failed_documents),
        total_sections=result.total_sections,
        total_subsections=result.total_subsections,
        total_chunks=result.total_chunks,
    )

    monitor.end_stage("stage_3_process", "completed")
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
        # Step 1: Extract document metadata (title, authors, etc.)
        metadata = extract_document_metadata(pages, auth_token)
        processed.metadata = metadata

        # Step 2: Detect structure and primary sections
        structure_type, confidence, section_breaks, _ = detect_structure(
            pages, auth_token
        )
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

        # Step 7: Generate document description and usage
        document_description, document_usage = generate_document_fields(
            metadata, sections, auth_token
        )
        processed.document_description = document_description
        processed.document_usage = document_usage

        # Step 8: Generate summary embedding
        summary_embedding = generate_summary_embedding(document_summary, auth_token)
        processed.summary_embedding = summary_embedding

        # Step 9: Generate chunks with proper section/subsection linkage
        chunks = generate_chunks(pages, sections)
        processed.chunks = chunks

        # Step 10: Generate chunk embeddings
        chunks = generate_embeddings(chunks, auth_token)
        processed.chunks = chunks

        return processed

    except Exception as exc:
        processed.processing_error = str(exc)
        logger.error("Document processing failed: %s", exc)
        return processed


def extract_document_metadata(
    pages: List[str],
    auth_token: str,
) -> DocumentMetadata:
    """
    Extract document metadata from first pages using LLM.

    Args:
        pages: List of page texts.
        auth_token: Authentication token.

    Returns:
        DocumentMetadata with extracted information.
    """
    if not pages:
        return DocumentMetadata()

    # Use first 2 pages for metadata extraction
    first_pages = "\\n\\n---PAGE BREAK---\\n\\n".join(pages[:2])
    first_pages = first_pages[:15000]  # Token limit

    system_prompt, tool_def, user_template = _load_prompt("extract_document_metadata")
    if not user_template:
        logger.warning("Metadata prompt missing, returning default metadata")
        return DocumentMetadata()

    try:
        user_prompt = user_template.format(page_excerpt=first_pages)
    except Exception as exc:
        logger.warning("Metadata prompt formatting failed: %s", exc)
        return DocumentMetadata()

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    tools = [tool_def] if tool_def else []
    tool_choice = (
        {"type": "function", "function": {"name": "extract_metadata"}}
        if tool_def
        else None
    )

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
            return DocumentMetadata(
                title=args.get("title", ""),
                authors=args.get("authors", []),
                publication_date=args.get("publication_date", ""),
                publication_venue=args.get("publication_venue", ""),
                abstract=str(args.get("abstract", ""))[:500],
            )

        logger.warning("Metadata extraction returned no tool call")
    except Exception as exc:
        logger.warning("Metadata extraction failed: %s", exc)
    return DocumentMetadata()


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

    structure_type = StructureType(classification.get("structure_type", "semantic"))
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

    # Fallback to simple consolidation if LLM fails
    if not final_sections:
        logger.warning(
            "LLM consolidation returned no sections, using simple consolidation"
        )
        final_sections = consolidate_sections_simple(all_sections, len(pages))

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

    # Load prompts from database
    system_prompt, tool_def, user_template = _load_prompt("classify_document")
    if not user_template:
        logger.warning("Classification prompt missing, using defaults")
        return default_result

    try:
        user_content = user_template.format(
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

    tools = [tool_def] if tool_def else []
    tool_choice = (
        {"type": "function", "function": {"name": "classify_document_structure"}}
        if tool_def
        else None
    )

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
    except Exception as exc:
        logger.warning("Classification failed: %s", exc)
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

    # Load prompts from database
    system_prompt, tool_def, user_template = _load_prompt("detect_sections_batch")
    if not user_template:
        logger.warning(
            "Section detection prompt missing for pages %d-%d", start_page, end_page
        )
        return [], None

    # Get structure-specific guidance from database
    guidance_name = f"structure_guidance_{structure_type.value}"
    _, _, structure_guidance = _load_prompt(guidance_name)
    if not structure_guidance:
        _, _, structure_guidance = _load_prompt("structure_guidance_semantic")

    # Format user prompt
    try:
        user_content = user_template.format(
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

    tools = [tool_def] if tool_def else []
    tool_choice = (
        {"type": "function", "function": {"name": "detect_section_breaks"}}
        if tool_def
        else None
    )

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
    except Exception as exc:
        logger.warning(
            "Section detection failed for pages %d-%d: %s", start_page, end_page, exc
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

    # Load prompts from database
    system_prompt, tool_def, user_template = _load_prompt("consolidate_structure")
    if not user_template:
        logger.warning("Consolidation prompt missing")
        return []

    # Format sections for prompt
    sections_text = "\n".join(
        f"- Page {s.page_number}: {s.title}"
        for s in sorted(sections, key=lambda x: x.page_number)
    )

    # Format ToC info
    toc_info = ""
    if toc_sections:
        toc_info = (
            "<toc_sections>\n"
            + "\n".join(f"- {s}" for s in toc_sections)
            + "\n</toc_sections>"
        )

    # Format user prompt
    try:
        user_content = user_template.format(
            structure_type=structure_type.value,
            confidence=confidence,
            total_pages=total_pages,
            has_toc=has_toc,
            toc_info=toc_info,
            all_sections=sections_text,
        )
    except Exception as exc:
        logger.warning("Consolidation prompt formatting failed: %s", exc)
        return []

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    tools = [tool_def] if tool_def else []
    tool_choice = (
        {"type": "function", "function": {"name": "consolidate_sections"}}
        if tool_def
        else None
    )

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
            consolidated = [
                SectionBreak(
                    page_number=s.get("page_number"),
                    title=s.get("title", ""),
                    level=s.get("level", 1),
                )
                for s in args.get("sections", [])
                if s.get("page_number") is not None
            ]

            corrections = args.get("corrections_made", [])
            if corrections:
                logger.info(
                    "LLM consolidation made %d corrections: %s",
                    len(corrections),
                    corrections[:3],
                )

            return sorted(consolidated, key=lambda s: s.page_number)

        logger.warning("LLM consolidation returned no tool call")

    except Exception as exc:
        logger.warning("LLM consolidation failed: %s", exc)
        return []
    return []


def consolidate_sections_simple(
    sections: List[SectionBreak],
    total_pages: int,
) -> List[SectionBreak]:
    """Simple consolidation - deduplicate and enforce max section size (fallback)."""
    if not sections:
        return []

    # Sort by page number
    sorted_sections = sorted(sections, key=lambda s: s.page_number)

    # Remove duplicates
    seen = set()
    unique = []
    for s in sorted_sections:
        key = (s.page_number, s.title)
        if key not in seen:
            seen.add(key)
            unique.append(s)

    # Enforce max section size by adding splits if needed
    final = []
    for i, section in enumerate(unique):
        final.append(section)

        # Check distance to next section
        if i + 1 < len(unique):
            next_page = unique[i + 1].page_number
        else:
            next_page = total_pages + 1

        section_size = next_page - section.page_number
        if section_size > MAX_SECTION_PAGES:
            # Add inferred splits
            for split_page in range(
                section.page_number + MAX_SECTION_PAGES,
                next_page,
                MAX_SECTION_PAGES,
            ):
                final.append(
                    SectionBreak(
                        page_number=split_page,
                        title=f"{section.title} (continued)",
                        level=1,
                        inferred=True,
                    )
                )

    return sorted(final, key=lambda s: s.page_number)


def build_primary_sections(
    pages: List[str],
    section_breaks: List[SectionBreak],
) -> List[Section]:
    """Build Section objects with page ranges (no summaries yet)."""
    if not section_breaks:
        return []

    sections = []
    total_pages = len(pages)

    for i, sb in enumerate(section_breaks):
        # Calculate page range
        page_start = sb.page_number
        if i + 1 < len(section_breaks):
            page_end = section_breaks[i + 1].page_number - 1
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
    """
    if not sections:
        return sections

    logger.info("Analyzing subsections for %d primary sections", len(sections))

    system_prompt, tool_def, user_template = _load_prompt("analyze_subsections")
    if not user_template or not tool_def:
        logger.warning("Subsection prompt missing, skipping analysis")
        return sections

    tools = [tool_def]
    tool_choice = {"type": "function", "function": {"name": "analyze_subsections"}}

    for section in sections:
        # Skip very short sections (3 pages or less)
        section_length = section.page_end - section.page_start + 1
        if section_length <= 3:
            logger.debug(
                "Skipping subsection analysis for short section: %s (%d pages)",
                section.title,
                section_length,
            )
            continue

        # Get section content
        section_pages = pages[section.page_start - 1 : section.page_end]
        section_content = "\n\n---PAGE BREAK---\n\n".join(section_pages)
        section_content = section_content[:50000]  # Token limit

        try:
            user_prompt = user_template.format(
                section_title=section.title,
                page_start=section.page_start,
                page_end=section.page_end,
                section_content=section_content,
            )
        except Exception as exc:
            logger.warning(
                "Subsection prompt formatting failed for %s: %s", section.title, exc
            )
            continue

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
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
                continue

            subsections_data = args.get("subsections", [])
            logger.debug(
                "Found %d subsections in %s", len(subsections_data), section.title
            )

            # Create Subsection objects
            for seq_num, sub_data in enumerate(subsections_data, 1):
                subsection = Subsection(
                    id=str(uuid.uuid4()),
                    parent_section_id=section.id,
                    sequence_number=seq_num,
                    title=sub_data.get("title", f"Subsection {seq_num}"),
                    page_start=sub_data.get("page_start", section.page_start),
                    page_end=sub_data.get("page_end", section.page_end),
                )
                # Validate page ranges
                subsection.page_start = max(
                    subsection.page_start, section.page_start
                )
                subsection.page_end = min(subsection.page_end, section.page_end)
                section.subsections.append(subsection)

        except Exception as exc:
            logger.warning("Subsection analysis failed for %s: %s", section.title, exc)

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

    Each summary includes:
    - overview: What the section covers
    - key_topics: Main concepts/themes
    - key_metrics: Numbers, statistics, measurements
    - key_findings: Important conclusions/results
    - notable_facts: Specific facts that might answer questions
    """
    if not sections:
        return sections

    logger.info("Generating enhanced summaries for %d sections", len(sections))

    for section in sections:
        # Generate summary for primary section
        section_pages = pages[section.page_start - 1 : section.page_end]
        section.summary = generate_section_summary_json(
            section_pages, section.title, section.page_start, section.page_end, auth_token
        )

        # Generate summaries for subsections
        for subsection in section.subsections:
            sub_pages = pages[subsection.page_start - 1 : subsection.page_end]
            subsection.summary = generate_section_summary_json(
                sub_pages,
                subsection.title,
                subsection.page_start,
                subsection.page_end,
                auth_token,
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
    section_content = "\n\n---PAGE BREAK---\n\n".join(pages[:20])
    section_content = section_content[:40000]  # Token limit

    system_prompt, tool_def, user_template = _load_prompt("generate_section_summary_json")
    default_summary = {
        "overview": f"Summary of {title}",
        "key_topics": [],
        "key_metrics": {},
        "key_findings": [],
        "notable_facts": [],
    }
    if not user_template or not tool_def:
        logger.warning("Summary prompt missing, using default summary for %s", title)
        return default_summary

    try:
        user_prompt = user_template.format(
            title=title,
            page_start=page_start,
            page_end=page_end,
            section_content=section_content,
        )
    except Exception as exc:
        logger.warning("Summary prompt formatting failed for %s: %s", title, exc)
        return default_summary

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        response, _ = _call_llm(
            auth_token,
            messages,
            model=config.MODEL_SMALL,
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
        logger.warning("Summary generation returned no tool call for %s", title)
    except Exception as exc:
        logger.warning("Summary generation failed for %s: %s", title, exc)
    return default_summary


def build_document_summary(
    metadata: DocumentMetadata,
    sections: List[Section],
    page_count: int,
) -> str:
    """
    Build complete document summary with metadata header and all section summaries.
    """
    parts = []

    # Metadata header
    parts.append("# Document Metadata")
    if metadata.title:
        parts.append(f"Title: {metadata.title}")
    if metadata.authors:
        parts.append(f"Authors: {', '.join(metadata.authors)}")
    if metadata.publication_date:
        parts.append(f"Date: {metadata.publication_date}")
    if metadata.publication_venue:
        parts.append(f"Venue: {metadata.publication_venue}")
    parts.append(f"Pages: {page_count}")
    parts.append("")

    # Abstract if available
    if metadata.abstract:
        parts.append("# Abstract")
        parts.append(metadata.abstract)
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
                metrics = "; ".join(section.summary["key_metrics"])
                parts.append(f"**Key Metrics:** {metrics}")

            if section.summary.get("key_findings"):
                for finding in section.summary["key_findings"]:
                    parts.append(f"- {finding}")

            if section.summary.get("notable_facts"):
                parts.append("**Notable Facts:**")
                for fact in section.summary["notable_facts"]:
                    parts.append(f"- {fact}")

        # Subsection summaries
        for sub in section.subsections:
            parts.append(
                f"\n### {section.sequence_number}.{sub.sequence_number} {sub.title} (pages {sub.page_start}-{sub.page_end})"
            )

            if sub.summary:
                if sub.summary.get("overview"):
                    parts.append(f"**Overview:** {sub.summary['overview']}")

                if sub.summary.get("key_topics"):
                    topics = ", ".join(sub.summary["key_topics"])
                    parts.append(f"**Key Topics:** {topics}")

                if sub.summary.get("key_metrics"):
                    metrics = "; ".join(sub.summary["key_metrics"])
                    parts.append(f"**Key Metrics:** {metrics}")

                if sub.summary.get("key_findings"):
                    for finding in sub.summary["key_findings"]:
                        parts.append(f"- {finding}")

        parts.append("")

    return "\n".join(parts)


def generate_document_fields(
    metadata: DocumentMetadata,
    sections: List[Section],
    auth_token: str,
) -> Tuple[str, str]:
    """
    Generate document description and usage fields using tool calling.

    Returns:
        Tuple of (document_description, document_usage)
        - description: Brief 2-3 sentence description of what the document is
        - usage: Comprehensive paragraph with all details for LLM document selection
    """
    # Build context for the LLM
    section_titles = [s.title for s in sections]
    topics = []
    for s in sections:
        if s.summary and s.summary.get("key_topics"):
            topics.extend(s.summary["key_topics"])
    unique_topics = list(set(topics))[:15]

    # Build section summaries for usage field
    section_summaries = []
    for s in sections:
        if s.summary:
            summary_parts = []
            if s.summary.get("overview"):
                summary_parts.append(s.summary["overview"])
            if s.summary.get("key_findings"):
                summary_parts.append(
                    f"Key findings: {', '.join(s.summary['key_findings'][:3])}"
                )
            if summary_parts:
                section_summaries.append(f"{s.title}: {' '.join(summary_parts)}")

    # Load prompt from database
    system_prompt, tool_def, user_template = _load_prompt("generate_catalog_fields")
    if not user_template or not tool_def:
        logger.warning("Catalog fields prompt missing, using fallback")
        return f"Document: {metadata.title or 'Unknown'}", ""

    # Format user prompt
    try:
        user_prompt = user_template.format(
            title=metadata.title or "Unknown",
            authors=", ".join(metadata.authors) if metadata.authors else "Unknown",
            publication_date=metadata.publication_date or "Unknown",
            venue=metadata.publication_venue or "Unknown",
            section_count=len(sections),
            section_titles="\n".join(f"- {t}" for t in section_titles[:20]),
            topics=", ".join(unique_topics),
            section_summaries="\n".join(section_summaries[:10]),
        )
    except Exception as exc:
        logger.warning("Catalog fields prompt formatting failed: %s", exc)
        return f"Document: {metadata.title or 'Unknown'}", ""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        response, _ = _call_llm(
            auth_token,
            messages,
            model=config.MODEL_SMALL,
            temperature=0.3,
            tools=[tool_def],
            tool_choice={"type": "function", "function": {"name": "generate_catalog_fields"}},
        )

        # Extract tool call arguments
        message = response.choices[0].message
        args = _parse_tool_arguments(message)
        if args:
            description = args.get("description", "").strip()
            usage = args.get("usage", "").strip()
            return description, usage

        # Fallback if no tool call
        logger.warning("No tool call in response, using content as description")
        content = message.content or ""
        return content.strip(), ""

    except Exception as exc:
        logger.warning("Document fields generation failed: %s", exc)
        fallback_desc = f"Document: {metadata.title or 'Unknown'}"
        return fallback_desc, ""


def generate_summary_embedding(
    document_summary: str,
    auth_token: str,
) -> Optional[List[float]]:
    """Generate embedding for the document summary."""
    if not document_summary:
        return None

    try:
        # Truncate if needed
        text = document_summary[:32000]
        embeddings, _ = _create_embedding(
            auth_token,
            [text],
            model=config.MODEL_EMBEDDING,
        )
        return embeddings[0]
    except Exception as exc:
        logger.warning("Summary embedding generation failed: %s", exc)
        return None


def generate_chunks(pages: List[str], sections: List[Section]) -> List[Chunk]:
    """Generate chunks with proper section/subsection linkage and page counts."""
    if not pages:
        return []

    # Build page-to-section/subsection maps
    page_section_map: Dict[int, Section] = {}
    page_subsection_map: Dict[int, Subsection] = {}

    for section in sections:
        for page_num in range(section.page_start, section.page_end + 1):
            page_section_map[page_num] = section

        for subsection in section.subsections:
            for page_num in range(subsection.page_start, subsection.page_end + 1):
                page_subsection_map[page_num] = subsection

    chunks = []
    for page_num, content in enumerate(pages, start=1):
        if not content.strip():
            continue

        section = page_section_map.get(page_num)
        subsection = page_subsection_map.get(page_num)

        # Build hierarchy path
        if section and subsection:
            hierarchy_path = f"{section.title} > {subsection.title}"
        elif section:
            hierarchy_path = section.title
        else:
            hierarchy_path = ""

        chunk = Chunk(
            id=str(uuid.uuid4()),
            primary_section_id=section.id if section else None,
            subsection_id=subsection.id if subsection else None,
            chunk_number=page_num - 1,  # 0-indexed
            page_number=page_num,
            raw_content=content,
            hierarchy_path=hierarchy_path,
            primary_section_number=section.sequence_number if section else None,
            primary_section_name=section.title if section else None,
            subsection_number=subsection.sequence_number if subsection else None,
            subsection_name=subsection.title if subsection else None,
            primary_section_page_count=section.page_count if section else None,
            subsection_page_count=subsection.page_count if subsection else None,
        )
        chunks.append(chunk)

    logger.info("Generated %d chunks", len(chunks))
    return chunks


def generate_embeddings(chunks: List[Chunk], auth_token: str) -> List[Chunk]:
    """Generate embeddings for all chunks."""
    if not chunks:
        return chunks

    logger.info("Generating embeddings for %d chunks", len(chunks))

    # Batch embedding
    for i in range(0, len(chunks), EMBEDDING_BATCH_SIZE):
        batch = chunks[i : i + EMBEDDING_BATCH_SIZE]
        texts = [c.raw_content[:32000] for c in batch]  # Truncate long texts

        try:
            embeddings, _ = _create_embedding(
                auth_token,
                texts,
                model=config.MODEL_EMBEDDING,
            )

            for j, embedding in enumerate(embeddings):
                batch[j].embedding = embedding

        except Exception as exc:
            logger.error("Embedding batch %d failed: %s", i // EMBEDDING_BATCH_SIZE, exc)

    embedded_count = sum(1 for c in chunks if c.embedding is not None)
    logger.info("Generated %d/%d embeddings", embedded_count, len(chunks))

    return chunks


def format_pages_for_prompt(pages: List[str], start_page: int = 1) -> str:
    """Format pages for LLM prompt."""
    formatted = []
    for i, page in enumerate(pages):
        page_num = start_page + i
        content = page[:8000] if len(page) > 8000 else page
        formatted.append(f"--- PAGE {page_num} ---\n{content}\n")
    return "\n".join(formatted)
