# structure_guidance_sections

**Model:** doc_refresh
**Layer:** stage_3
**Version:** 1.0.0
**Description:** Guidance for detecting sections in section-structured documents

---

## System Prompt

*No system prompt defined*

## User Prompt

```
For SECTIONS structure (academic papers, reports):
- Find ONLY top-level numbered sections: "1 Introduction", "2 Methods", "3 Results"
- Do NOT include subsections like "1.1", "2.1", "2.2" - those will be detected later
- Also find standalone headers: "Abstract", "References", "Appendix", "Acknowledgments"
- Example level 1 sections: Abstract, 1 Introduction, 2 Background, 3 Methods, 4 Experiments, 5 Results, 6 Conclusion, References
```

## Tool Definition

*No tool definition*
