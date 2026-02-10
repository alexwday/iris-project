# structure_guidance_chapters

**Model:** doc_refresh
**Layer:** stage_3
**Version:** 2.0.0
**Description:** Guidance text for detecting chapter-based structure

---

## System Prompt

*No system prompt defined*

## User Prompt

```
For CHAPTERS structure:
- What to look for: Explicit chapter headers (Chapter X, Part X, numbered divisions with roman numerals or named parts)
- Only capture: Chapter-level headers (NOT sections within chapters like 1.1, 2.1)
- Target section size: Varies by document (no fixed target, but max 100 pages per chapter)
- Naming convention: Use exact chapter titles as written (e.g., "Chapter 1: Introduction", "Part II: Analysis", "Module 3")
```

## Tool Definition

*No tool definition*
