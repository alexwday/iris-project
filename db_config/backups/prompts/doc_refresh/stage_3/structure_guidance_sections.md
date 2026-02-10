# structure_guidance_sections

**Model:** doc_refresh
**Layer:** stage_3
**Version:** 2.0.0
**Description:** Guidance text for detecting section-based structure

---

## System Prompt

*No system prompt defined*

## User Prompt

```
For SECTIONS structure (academic papers, reports):
- What to look for: Top-level numbered sections ("1 Introduction", "2 Methods") and standalone headers ("Abstract", "References", "Appendix", "Acknowledgments")
- Only capture: Level-1 sections (NOT subsections like "1.1", "2.1" - those will be detected later)
- Target section size: Varies by document (no fixed target, but max 100 pages per section)
- Naming convention: Use exact section titles as written (e.g., "Abstract", "1 Introduction", "2 Background", "References")
```

## Tool Definition

*No tool definition*
