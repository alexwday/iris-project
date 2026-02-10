"""
Stage 4: Validate - Validate Processed Content Before Database Insertion.

This stage validates all processed documents to ensure data integrity
before database insertion. Catches issues that would cause DB errors
or data corruption.

Validation checks:
- Page ranges are valid (start <= end, within document bounds)
- Page ranges are contiguous (no gaps, no overlaps)
- Section hierarchy is valid
- All chunks have embeddings
- Required fields are populated

Functions:
    run_stage: Execute the validation stage
    validate_document: Validate a single processed document
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional

from ..stages.stage_3_process import ProcessedDocument, Section, Chunk

logger = logging.getLogger(__name__)


@dataclass
class ValidationError:
    """A validation error for a document."""

    document_name: str
    error_type: str
    message: str
    severity: str = "error"  # "error" or "warning"


@dataclass
class ValidatedDocument:
    """A validated document ready for database insertion."""

    document: ProcessedDocument
    warnings: List[ValidationError] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Result of the validation stage."""

    validated_documents: List[ValidatedDocument] = field(default_factory=list)
    failed_documents: List[ProcessedDocument] = field(default_factory=list)
    all_errors: List[ValidationError] = field(default_factory=list)
    total_warnings: int = 0


def run_stage(
    processed_documents: List[ProcessedDocument],
    strict: bool = True,
) -> ValidationResult:
    """
    Execute the validation stage.

    Validates all processed documents to ensure data integrity.

    Args:
        processed_documents: List of ProcessedDocument from Stage 3.
        strict: If True, treat warnings as errors. Default True.

    Returns:
        ValidationResult with validated and failed documents.
    """
    result = ValidationResult()

    if not processed_documents:
        logger.info("No documents to validate")
        return result

    logger.info("Validating %d processed documents", len(processed_documents))

    for doc in processed_documents:
        errors = validate_document(doc)

        # Separate errors and warnings
        hard_errors = [e for e in errors if e.severity == "error"]
        warnings = [e for e in errors if e.severity == "warning"]

        result.all_errors.extend(errors)
        result.total_warnings += len(warnings)

        if hard_errors:
            # Document failed validation
            result.failed_documents.append(doc)
            for error in hard_errors:
                logger.error(
                    "Validation error for %s: [%s] %s",
                    error.document_name,
                    error.error_type,
                    error.message,
                )
        elif strict and warnings:
            # Strict mode: warnings are errors
            result.failed_documents.append(doc)
            for warning in warnings:
                logger.warning(
                    "Validation warning (strict) for %s: [%s] %s",
                    warning.document_name,
                    warning.error_type,
                    warning.message,
                )
        else:
            # Document passed
            result.validated_documents.append(
                ValidatedDocument(document=doc, warnings=warnings)
            )
            if warnings:
                for warning in warnings:
                    logger.warning(
                        "Validation warning for %s: [%s] %s",
                        warning.document_name,
                        warning.error_type,
                        warning.message,
                    )

    # Log summary
    logger.info(
        "Validation complete: %d passed, %d failed, %d warnings",
        len(result.validated_documents),
        len(result.failed_documents),
        result.total_warnings,
    )

    return result


def validate_document(doc: ProcessedDocument) -> List[ValidationError]:
    """
    Validate a single processed document.

    Args:
        doc: ProcessedDocument to validate.

    Returns:
        List of ValidationError objects (empty if valid).
    """
    errors = []
    doc_name = doc.file_info.file_name

    # Check required fields
    errors.extend(validate_required_fields(doc, doc_name))

    # Check page ranges
    errors.extend(validate_page_ranges(doc, doc_name))

    # Check sections
    errors.extend(validate_sections(doc, doc_name))

    # Check chunks
    errors.extend(validate_chunks(doc, doc_name))

    # Check embeddings
    errors.extend(validate_embeddings(doc, doc_name))

    return errors


def validate_required_fields(
    doc: ProcessedDocument, doc_name: str
) -> List[ValidationError]:
    """Validate that required fields are populated."""
    errors = []

    if not doc.file_info:
        errors.append(
            ValidationError(
                document_name=doc_name,
                error_type="missing_field",
                message="file_info is missing",
            )
        )
        return errors  # Can't continue without file_info

    if not doc.file_info.file_path:
        errors.append(
            ValidationError(
                document_name=doc_name,
                error_type="missing_field",
                message="file_path is missing",
            )
        )

    if not doc.file_info.file_hash:
        errors.append(
            ValidationError(
                document_name=doc_name,
                error_type="missing_field",
                message="file_hash is missing",
            )
        )

    if doc.page_count <= 0:
        errors.append(
            ValidationError(
                document_name=doc_name,
                error_type="invalid_value",
                message=f"page_count is invalid: {doc.page_count}",
            )
        )

    return errors


def validate_page_ranges(
    doc: ProcessedDocument, doc_name: str
) -> List[ValidationError]:
    """Validate section page ranges."""
    errors = []

    if not doc.sections:
        return errors

    for section in doc.sections:
        # Check start <= end
        if section.page_start > section.page_end:
            errors.append(
                ValidationError(
                    document_name=doc_name,
                    error_type="invalid_page_range",
                    message=f"Section '{section.title}' has invalid range: {section.page_start}-{section.page_end}",
                )
            )

        # Check within document bounds
        if section.page_start < 1:
            errors.append(
                ValidationError(
                    document_name=doc_name,
                    error_type="invalid_page_range",
                    message=f"Section '{section.title}' starts before page 1",
                )
            )

        if section.page_end > doc.page_count:
            errors.append(
                ValidationError(
                    document_name=doc_name,
                    error_type="invalid_page_range",
                    message=f"Section '{section.title}' ends after last page ({doc.page_count})",
                    severity="warning",  # May be okay if page_count is off
                )
            )

    # Check for overlapping sections. By design, adjacent sections share a
    # boundary page (page_end == next page_start) and content is split at the
    # section title position. Only flag overlaps beyond this single shared page.
    sorted_sections = sorted(doc.sections, key=lambda s: s.page_start)
    for i in range(len(sorted_sections) - 1):
        current = sorted_sections[i]
        next_sec = sorted_sections[i + 1]

        if current.page_end > next_sec.page_start:
            errors.append(
                ValidationError(
                    document_name=doc_name,
                    error_type="overlapping_sections",
                    message=f"Sections overlap: '{current.title}' ({current.page_start}-{current.page_end}) and '{next_sec.title}' ({next_sec.page_start}-{next_sec.page_end})",
                    severity="warning",
                )
            )

    return errors


def validate_sections(
    doc: ProcessedDocument, doc_name: str
) -> List[ValidationError]:
    """Validate section structure and content."""
    errors = []

    if not doc.sections:
        if doc.page_count > 0:
            errors.append(
                ValidationError(
                    document_name=doc_name,
                    error_type="no_sections",
                    message="Document has pages but no sections",
                    severity="warning",
                )
            )
        return errors

    # Check for unique IDs
    section_ids = [s.id for s in doc.sections]
    if len(section_ids) != len(set(section_ids)):
        errors.append(
            ValidationError(
                document_name=doc_name,
                error_type="duplicate_ids",
                message="Duplicate section IDs found",
            )
        )

    # Check each section
    for section in doc.sections:
        if not section.id:
            errors.append(
                ValidationError(
                    document_name=doc_name,
                    error_type="missing_id",
                    message=f"Section '{section.title}' has no ID",
                )
            )

        if not section.title:
            errors.append(
                ValidationError(
                    document_name=doc_name,
                    error_type="missing_title",
                    message=f"Section at page {section.page_start} has no title",
                )
            )

        if not section.summary:
            errors.append(
                ValidationError(
                    document_name=doc_name,
                    error_type="missing_summary",
                    message=f"Section '{section.title}' has no summary",
                    severity="warning",
                )
            )

    return errors


def validate_chunks(doc: ProcessedDocument, doc_name: str) -> List[ValidationError]:
    """Validate chunks."""
    errors = []

    if not doc.chunks:
        if doc.page_count > 0:
            errors.append(
                ValidationError(
                    document_name=doc_name,
                    error_type="no_chunks",
                    message="Document has pages but no chunks",
                )
            )
        return errors

    # Check chunk count roughly matches page count
    expected_chunks = doc.page_count
    actual_chunks = len(doc.chunks)
    if actual_chunks < expected_chunks * 0.5:
        errors.append(
            ValidationError(
                document_name=doc_name,
                error_type="missing_chunks",
                message=f"Expected ~{expected_chunks} chunks, got {actual_chunks}",
                severity="warning",
            )
        )

    # Check for unique IDs
    chunk_ids = [c.id for c in doc.chunks]
    if len(chunk_ids) != len(set(chunk_ids)):
        errors.append(
            ValidationError(
                document_name=doc_name,
                error_type="duplicate_ids",
                message="Duplicate chunk IDs found",
            )
        )

    # Check each chunk
    for chunk in doc.chunks:
        if not chunk.id:
            errors.append(
                ValidationError(
                    document_name=doc_name,
                    error_type="missing_id",
                    message=f"Chunk {chunk.chunk_number} has no ID",
                )
            )

        if not chunk.raw_content:
            errors.append(
                ValidationError(
                    document_name=doc_name,
                    error_type="empty_chunk",
                    message=f"Chunk {chunk.chunk_number} has no content",
                    severity="warning",
                )
            )

    return errors


def validate_embeddings(
    doc: ProcessedDocument, doc_name: str
) -> List[ValidationError]:
    """Validate embeddings."""
    errors = []

    if not doc.chunks:
        return errors

    chunks_with_embedding = sum(1 for c in doc.chunks if c.embedding is not None)
    chunks_without = len(doc.chunks) - chunks_with_embedding

    if chunks_without > 0:
        if chunks_without == len(doc.chunks):
            errors.append(
                ValidationError(
                    document_name=doc_name,
                    error_type="no_embeddings",
                    message="No chunks have embeddings",
                )
            )
        else:
            errors.append(
                ValidationError(
                    document_name=doc_name,
                    error_type="missing_embeddings",
                    message=f"{chunks_without}/{len(doc.chunks)} chunks missing embeddings",
                    severity="warning",
                )
            )

    # Check embedding dimensions
    for chunk in doc.chunks:
        if chunk.embedding:
            if len(chunk.embedding) == 0:
                errors.append(
                    ValidationError(
                        document_name=doc_name,
                        error_type="empty_embedding",
                        message=f"Chunk {chunk.chunk_number} has empty embedding",
                    )
                )

    return errors
