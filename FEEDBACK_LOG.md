"For questions that overlap between CAPM and APG Wiki, I am finding that the answer is pulling only from CAPM and not pulling in relevant guidance from APG Wiki. For example, 'how are intergroup derivatives accounted for?' It doesn't capture the APG Wiki's item relating to how to treat intergroup derivatives for insurance segment. The answer should, if relevant, should be pulling in both.""The responses within the demo are really long which includes Thought, Clarify, Researching, Database, etc. Is it meant to show all those steps? Will some of these eventually be deleted to condense answer?"# Business Feedback Log

This document tracks feedback received from business users regarding the Iris application and the corresponding fixes or explanations.

---

## Issue 1: Unsolicited IFRS vs. GAAP Comparisons

**Feedback:**
"Some of the response I received had IFRS vs GAAP differences pulled from the CAPM, maybe we do not show this if the user did not ask for a comparison to US GAAP, to shorten the response?"

**Analysis/Solution:**
The APG team correctly identified that the CAPM subagent was sometimes including comparisons between accounting standards (e.g., IFRS vs. US GAAP) even when the team's query didn't ask for it. This happened because the initial instructions for the subagent responsible for analyzing CAPM content were not specific enough about filtering based on the requested standard.

The fix involved enhancing the prompt instructions within the CAPM subagent's configuration file: `iris/src/agents/database_subagents/internal_capm/content_synthesis_prompt.py`.

Specifically, within the `get_content_synthesis_prompt` function, under step 4 (`**Generate Focused Detailed Research Report:**`), the following instruction was added and emphasized to ensure the agent strictly filters its analysis:

```python
# File: iris/src/agents/database_subagents/internal_capm/content_synthesis_prompt.py
# Inside step 4. **Generate Focused Detailed Research Report:**

        "   * **CRITICAL STANDARD FILTERING:** Focus your synthesis *only* on information relevant to the accounting standard specified or implied in the <USER_QUERY> (Defaulting to IFRS if none is specified). Actively filter out and ignore information related to other standards (e.g., US GAAP) unless that standard was explicitly requested in the query.**",

```
This instruction explicitly tells the agent to focus *only* on the standard relevant to the query (defaulting to IFRS if none is mentioned) and to actively ignore information about other standards unless the APG team specifically asks for a comparison (e.g., "compare IFRS 15 to ASC 606").

**Outcome for APG Team:**
With this update, when the APG team asks a question without specifying a standard, the system will default to IFRS and provide information *only* related to IFRS from the CAPM database. Unsolicited comparisons to US GAAP or other standards will no longer be included, resulting in shorter, more focused, and relevant answers that directly address the team's query.

---

## Issue 2: Incomplete Answers Due to Sequential Database Processing

**Feedback:**
"For questions that overlap between CAPM and APG Wiki, I am finding that the answer is pulling only from CAPM and not pulling in relevant guidance from APG Wiki. For example, 'how are intergroup derivatives accounted for?' It doesn't capture the APG Wiki's item relating to how to treat intergroup derivatives for insurance segment. The answer should, if relevant, should be pulling in both."

**Analysis/Solution:**
The APG team correctly observed that sometimes answers were incomplete, particularly when information relevant to the query existed in both CAPM and APG Wiki (or other sources). The root cause was the system's previous method of querying databases sequentially. It would query CAPM first, and if it received what seemed like a complete answer, it might have skipped querying APG Wiki or other relevant databases to save time, thus missing important context.

The fix involved a fundamental change to how database research is performed and combined:

1.  **Parallel Database Queries:** Instead of querying one database after another, the system now initiates queries to all relevant databases (like CAPM, APG Wiki, Cheatsheets, Memos, etc., depending on the query) *in parallel*. This ensures that all potentially relevant sources are checked simultaneously. While the specific orchestration code isn't shown here, the architecture was updated to support this parallel execution.
2.  **Comprehensive Synthesis by Summarizer:** The Summarizer agent, responsible for creating the final answer, was updated to handle inputs from all the parallel database queries. Its instructions, defined in `iris/src/agents/agent_summarizer/summarizer_settings.py`, explicitly require it to synthesize findings from *all* the internal research reports it receives. The implementation in `iris/src/agents/agent_summarizer/summarizer.py` confirms this; it aggregates the findings from each database report (passed in the `aggregated_detailed_research` dictionary) and instructs the language model to:
    ```
    # User message within summarizer.py instructing the LLM:
    "Please generate the comprehensive research summary based on the provided context and requirements. Synthesize the findings from all sources into a single, coherent response."
    ```
    This ensures the final answer integrates information from all consulted sources (e.g., CAPM, APG Wiki) rather than stopping early.
3.  **Default Sources:** For common accounting queries, APG Wiki and APG Cheatsheets were likely configured as default databases to be queried alongside CAPM, further ensuring their relevant guidance isn't missed.

**Outcome for APG Team:**
This architectural change directly addresses the APG team's feedback. Because relevant databases like CAPM and APG Wiki are now queried in parallel, and the Summarizer agent is explicitly designed to integrate findings from *all* of them, the final answers will be more comprehensive. For questions like the intergroup derivatives example, the response will now incorporate relevant guidance from both CAPM and the APG Wiki (and any other relevant sources queried), providing a complete picture.

---

## Issue 3: Slow Response Processing Time

**Feedback:**
"What is the expected processing time for each question? I found responses to questions takes long, between ~120 to ~200 seconds based on the time stamp. Could it be sped up?"

**Analysis/Solution:**
The APG team reported experiencing slow response times, sometimes taking 120-200 seconds. Our analysis confirmed this and identified several contributing factors: the previous sequential database querying, potentially large amounts of text being processed by the language models (high token counts), and the use of powerful (but slower) language models for tasks that might not require them.

A multi-pronged optimization strategy was implemented to address this:

1.  **Parallelization of Database Queries:** As detailed in the fix for Issue 2, database lookups were changed from sequential to parallel. This is a major factor in reducing the overall wait time, as multiple sources are queried simultaneously instead of one after another.
2.  **LLM Model Tiering:** The system was configured to use different language models based on the complexity of the task. The configuration file `iris/src/chat_model/model_settings.py` defines different model "capabilities":
    ```python
    # File: iris/src/chat_model/model_settings.py
    MODELS = {
        "small": {
            "rbc": {"name": "gpt-4o-mini-2024-07-18", ...},
            "local": {"name": "gpt-4o-mini-2024-07-18", ...},
        },
        "large": {
            "rbc": {"name": "gpt-4o-2024-05-13", ...},
            "local": {"name": "gpt-4o-2024-08-06", ...},
        },
        # ... embedding model ...
    }

    def get_model_config(capability):
        # ... logic to return model name based on capability and environment ...
    ```
    This allows simpler tasks (like initial query classification or basic data extraction by some subagents) to potentially use the faster 'small' capability model (`gpt-4o-mini`), while more complex tasks like the final synthesis performed by the Summarizer agent (see `iris/src/agents/agent_summarizer/summarizer_settings.py` which specifies `MODEL_CAPABILITY = "large"`) use the more powerful 'large' capability model (`gpt-4o`). This strategic use of different models helps optimize the overall speed.
3.  **Prompt Optimization (Token Reduction):** Prompts used to instruct various agents were reviewed and refined to be more concise. Reducing the amount of text (tokens) sent to and generated by the language models generally leads to faster processing times. This was an ongoing effort across multiple agent configuration files (like the content synthesis prompts for database subagents).

**Outcome for APG Team:**
These combined optimizations – parallelizing database lookups, strategically using faster models for simpler tasks (LLM Tiering), and reducing the amount of text processed (Token Reduction) – work together to significantly decrease the end-to-end response time. While the exact time will still vary depending on the complexity of the APG team's query, the overall experience should be noticeably faster than the 120-200 seconds previously observed.

---

## Issue 4: Overly Verbose Response Format

**Feedback:**
"The responses within the demo are really long which includes Thought, Clarify, Researching, Database, etc. Is it meant to show all those steps? Will some of these eventually be deleted to condense answer?"

**Analysis/Solution:**
The APG team correctly pointed out that the responses included excessive internal processing details (like "Thought:", "Clarifying...", "Researching Database X..."), making the output long and hard to follow.

The fix involved significantly streamlining the information presented to the APG team:

1.  **Elimination of Internal Monologue:** The core change was to stop displaying the internal "thinking" steps of the various agents (Planner, Router, Subagents) in the final chat output. The system now performs these steps in the background.
2.  **Focused Clarification:** When the system determines clarification is needed, the Clarifier agent is instructed to be direct. As seen in `iris/src/agents/agent_clarifier/clarifier_settings.py`, its prompt requires it to output *only* the specific questions needed, without any surrounding explanation or internal reasoning:
    ```python
    # File: iris/src/agents/agent_clarifier/clarifier_settings.py
    # Within <RESPONSE_FORMAT> section:
    # "Your response must be ONLY a tool call to `make_clarifier_decision`..."
    # "No additional text or explanation should be included outside the tool call."
    ```
    This ensures the APG team only sees the necessary questions.
3.  **Streamlined Research Initiation & Status:** When research proceeds, the APG team typically sees only the final "Research Statement" confirming what's being looked up. During the parallel database searches (see Issue 2), concise status updates (e.g., "✅ CAPM Search Complete") are provided instead of detailed logs.
4.  **Direct Final Report:** As confirmed in the analysis for Issue 2, the Summarizer agent (`iris/src/agents/agent_summarizer/summarizer.py` and `summarizer_settings.py`) is designed to generate *only* the final, synthesized research report, without verbose introductions or intermediate steps.

**Outcome for APG Team:**
The chat interface presented to the APG team is now much cleaner. Instead of seeing the system's internal thought process, the team sees only the essential information: clarifying questions (if needed), the research statement, brief status updates during research, and finally, the consolidated answer. This removes the internal "noise" and delivers the necessary information much more efficiently, directly addressing the feedback about excessive length and verbosity.

---

## Issue 5: "Database Queries Not Processed" Message

**Feedback:**
"To remove this part of the response to questions saying: the following database queries were not processed."

**Analysis/Solution:**
The APG team requested the removal of the message stating "the following database queries were not processed." This message appeared previously because of the old sequential database querying method (as explained in Issue 2). In that setup, if a query to an early database like CAPM yielded what seemed like a full answer, the system might have intentionally skipped querying subsequent databases (like APG Wiki) to save time, resulting in this "not processed" notification for the skipped ones.

The fix for this issue is a direct result of the architectural change to parallel processing implemented to solve Issue 2:

1.  **Parallel Processing Eliminates Skipping:** As confirmed in the analysis for Issue 2, all relevant database subagents (e.g., CAPM, APG Wiki, Memos) are now queried *in parallel*. The system no longer stops early based on results from one database; it waits for all selected databases to complete their search concurrently.
2.  **No More "Unprocessed" Queries:** Since databases are no longer skipped within a single user request cycle, the condition that triggered the "not processed" message no longer exists. Every database deemed relevant by the Planner (or requested by the user) is queried.

**Outcome for APG Team:**
The message "the following database queries were not processed" has been eliminated. This is a natural consequence of the shift to parallel database querying. The APG team will no longer see this message because the system now ensures all relevant databases are consulted for each query, providing more comprehensive results (as addressed in Issue 2).

---

## Issue 6: Inconsistent Spacing/Formatting in Responses

**Feedback:**
"Some spacings in the response needed to be fixed."

**Analysis/Solution:**
The APG team noted inconsistencies in the final response formatting, such as extra blank lines, uneven indentation, or incorrect Markdown usage, which affected readability.

This was addressed through a general review and refinement of the instructions (prompts) given to the agents responsible for generating text, particularly the Summarizer agent which creates the final user-facing response.

1.  **Summarizer Formatting Instructions:** The prompt for the Summarizer agent (`iris/src/agents/agent_summarizer/summarizer_settings.py`) was enhanced with explicit instructions and examples on how to format the final output using Markdown. This includes guidance on using headings, lists, bold text, and ensuring proper paragraph spacing:
    ```python
    # File: iris/src/agents/agent_summarizer/summarizer_settings.py
    # Within <RESPONSE_FORMAT> section for 'research' scope:
    # - "Generate ONLY the synthesized answer content itself..."
    # - "Use clear paragraph breaks (double newlines in Markdown)."
    # - "For Complex Queries: Format extensively with Markdown (headings, lists, bold text) for structure and readability."
    # - "For Simple Queries: Use minimal formatting..."
    # Also includes <CITATION_INTEGRATION_EXAMPLES> showing desired output structure.
    ```
2.  **Subagent Report Formatting:** While subagents (like CAPM, Wiki) generate *internal* reports, their prompts (e.g., `iris/src/agents/database_subagents/internal_capm/content_synthesis_prompt.py`, `iris/src/agents/database_subagents/internal_wiki/content_synthesis_prompt.py`) also include instructions for structuring their output (e.g., using Markdown headings like `## Key Findings`) and formatting citations consistently. This structured internal input helps the Summarizer produce a well-formatted final response.

**Outcome for APG Team:**
By providing clearer and more explicit formatting guidelines to the agents, especially the Summarizer, the system now generates responses with more consistent spacing, indentation, and Markdown structure. This improves the overall readability and professional appearance of the answers provided to the APG team. Minor formatting inconsistencies might still occur occasionally and can be addressed through ongoing prompt tuning.

---

## Issue 7: Inability to Scroll Up During Response Streaming

**Feedback:**
"When the tool is processing to get a response, can we allow user to scrolling up to view the previous chat messages? It resets to the bottom when I try to scroll back up while processing."

**Analysis/Solution:**
The APG team reported that when a response was being streamed (typed out), trying to scroll up to see previous messages didn't work because the view kept snapping back to the bottom.

This was identified as an issue with the chat's User Interface (UI) behavior, not with the backend agents processing the request. The fix involved modifying the front-end application code (which is separate from the `iris` Python backend code we typically examine) that controls how the chat window behaves during streaming:

1.  **Scrolling Enabled During Streaming:** The UI code was changed to allow the APG team to freely scroll up and down the chat history even while new parts of the current response are being added at the bottom.
2.  **Auto-Scroll After Completion:** The helpful behavior of automatically scrolling to the very bottom *after* the entire response has finished streaming was kept. This ensures the team sees the complete final message without needing to scroll down manually.
3.  **UI Team Collaboration:** It was noted that the precise scrolling behavior in the final production interface might be subject to further refinement based on discussions with the UI/UX teams responsible for the overall application (e.g., the Maven team).

**Outcome for APG Team:**
The APG team can now scroll up to review previous messages or context while a new response is being generated, which improves usability during longer interactions. The chat will still automatically scroll down to show the end of the message once it's fully delivered.

---

## Issue 8: Incorrectly Labeling External Firm Guidance as "Authoritative"

**Feedback:**
"Can you delete the yellow highlighted words saying "external sources are authoritative"? They are not correct as accounting firms' sources are not authoritative. Only IASB and FASB data are."

**Analysis/Solution:**
The APG team correctly highlighted that external accounting firm guidance (from sources like EY, PwC, KPMG) should not be labeled as "authoritative," as this designation is reserved for official standard-setting bodies like IASB (for IFRS) and FASB (for US GAAP). External firm guidance is interpretive and supplementary.

The fix involved updating the central description of data sources provided to all agents in the file `iris/src/global_prompts/database_statement.py`.

1.  **Corrected Database Descriptions:** The descriptions within the `AVAILABLE_DATABASES` dictionary in this file were reviewed and modified. Specifically, the `<USAGE>` tags for external firms were updated:
    ```python
    # File: iris/src/global_prompts/database_statement.py

    # Example for external_ey:
    "external_ey": {
        # ... other fields ...
        "use_when": "External Supplementary: External firm perspective on IFRS; disclosure checklists. **Strategy:** Consult *only if requested by user* or if internal sources are insufficient. Use to supplement internal knowledge, fill gaps, or get external interpretation. Useful for disclosure examples. **Query:** Use standard numbers (IFRS 15, IAS 38), technical terms, specific paragraphs.",
    },
    # Similar updates for external_kpmg and external_pwc

    # Contrasted with external_iasb:
    "external_iasb": {
        # ... other fields ...
        "use_when": "External Authoritative: Official IFRS standard text, interpretations, basis for conclusions. **Strategy:** Consult *only if requested by user* or if internal sources are insufficient/unclear. Use for official standard text or interpretations. **Query:** Use standard numbers (IFRS 15, IAS 38), interpretations (IFRIC/SIC), technical terms, specific paragraphs.",
    },
    ```
    As shown, external firm guidance (EY, PwC, KPMG) is now explicitly labeled as "**External Supplementary**", while the official IASB source is labeled "**External Authoritative**".
2.  **Reinforced Hierarchy:** This change ensures that the context provided to all internal agents accurately reflects the established hierarchy of accounting guidance sources.

**Outcome for APG Team:**
By correcting these descriptions in the core `database_statement.py` file, all agents within the system now operate with the correct understanding of source authority. This prevents the system from internally misinterpreting or potentially misrepresenting external firm guidance as authoritative. The APG team can be confident that the system correctly prioritizes official standards and internal policy (CAPM) over supplementary external interpretations.

---

## Issue 9: Incorrect Naming and Prioritization of EY Guidance

**Feedback:**
"Can we delete the highlighted saying "used collectively with PAC and KMG as a primary source for IFRS knowledge? These should not be a primary source. I believe I share that it was "fifth" primary source. Also, "EY Technical Guidance" should be "EY Accounting Guidance"."

**Analysis/Solution:**
The APG team identified two specific inaccuracies regarding the EY external database within the system's internal context:
1.  **Incorrect Prioritization:** It was described in a way that implied it was a "primary source," which is incorrect. As established in Issue 8, external firm guidance is supplementary.
2.  **Incorrect Naming:** It was referred to as "EY Technical Guidance" instead of the correct name.

Both issues were addressed by updating the central database descriptions in `iris/src/global_prompts/database_statement.py`:

1.  **Corrected Prioritization:** As confirmed during the analysis for Issue 8, the `<USAGE>` description for `external_ey` (and other external firms) was updated to label them "**External Supplementary**", accurately reflecting their role relative to authoritative sources (IASB) and internal policy (CAPM).
2.  **Corrected Naming:** The `name` field for the `external_ey` entry in the `AVAILABLE_DATABASES` dictionary was corrected. It now accurately reflects the source material:
    ```python
    # File: iris/src/global_prompts/database_statement.py
    "external_ey": {
        "name": "EY IFRS Guidance", # Corrected Name
        "description": "External IFRS guidance and interpretations from EY. Includes disclosure checklist.",
        # ...
        "use_when": "External Supplementary: ...", # Corrected Prioritization
    },
    ```

**Outcome for APG Team:**
These corrections within the core `database_statement.py` file ensure that all agents in the system have the accurate name ("EY IFRS Guidance") and understand the correct, supplementary role of the EY database (and other external firm databases). This reinforces the proper hierarchy of information sources used during research and prevents mischaracterization.

---

## Issue 10: Missing Critical Information from CAPM in Response

**Feedback:**
"I asked "under ifrs, internal sources, should an embedded derivative be nil?". The response didn't include this specific part of the CAPM, which was critical to the response. Not sure why it wasn't part of the response."

**Analysis/Solution:**
The APG team reported that a specific, critical piece of information from CAPM was missing in the response to their query about embedded derivatives ("should an embedded derivative be nil?"). This indicated a failure in the system's ability to reliably extract and synthesize *all* relevant details, especially specific conditions or criteria, from the source documents.

Addressing this required enhancing the instructions (prompts) for multiple agents involved in the research process to ensure critical details are preserved:

1.  **Enhanced Subagent Extraction (e.g., CAPM):** The prompt for the CAPM subagent (`iris/src/agents/database_subagents/internal_capm/content_synthesis_prompt.py`) was refined to emphasize not just general relevance, but also the accurate extraction of specific conditions or tests. Instructions like the following were added/emphasized:
    ```python
    # File: iris/src/agents/database_subagents/internal_capm/content_synthesis_prompt.py
    # Inside step 4. **Generate Focused Detailed Research Report:**
    # ...
    "   * Furthermore, pay special attention to any logical tests or criteria described in the content (e.g., conditions connected by 'and'/'or', multi-part tests, 'if...then' statements). Reproduce the full structure and wording of these tests accurately in your report, using formatting like bullet points or nested lists if needed for clarity.",
    # ...
    ```
    This directs the subagent to explicitly look for and accurately report such critical details in its internal findings.
2.  **Improved Summarizer Synthesis:** The Summarizer agent, which compiles the final response, received enhanced instructions in `iris/src/agents/agent_summarizer/summarizer_settings.py` to specifically look for and accurately represent such details passed up from the subagents:
    ```python
    # File: iris/src/agents/agent_summarizer/summarizer_settings.py
    # Within <RESEARCH_SCOPE> -> B. Complex/Research-Oriented:
    # ...
    "    7. **Represent Logical Tests:** Carefully identify any logical test criteria (e.g., 'and-tests', 'or-tests', multi-step conditions) detailed in the internal research reports. Ensure these tests are fully and accurately represented in your final synthesized answer, maintaining their logical structure."
    # ...
    # Also within <PATTERN_RECOGNITION_INSTRUCTIONS>:
    # "9. COMPARE LOGICAL TESTS: Identify and compare any specific test criteria or logical conditions mentioned across different internal reports..."
    ```
    These instructions ensure the Summarizer actively preserves and presents the critical conditions or criteria identified by the subagents.
3.  **Context Propagation:** Underlying improvements may also have been made to ensure the specific constraints of the original query (like "should be nil?") are effectively passed down through the agent chain to inform the relevance analysis at each step.

**Outcome for APG Team:**
These prompt refinements across the system significantly improve the likelihood that critical details, specific conditions (like whether something should be nil), and logical tests mentioned in source documents (like CAPM) are accurately identified, extracted by the subagents, and correctly synthesized into the final response presented to the APG team. This directly addresses the feedback about missing crucial information by enhancing the system's precision in handling nuanced queries.

---

## Issue 11: Displaying Graphical Cheat Sheets

**Feedback:**
"For APG Cheat Sheets, is it possible to provide a response showing the cheat sheet graphic itself, or it has to be in words?"

**Analysis/Solution:**
The APG team asked if graphical elements from the APG Cheat Sheets (like flowcharts or diagrams) could be shown directly in the chat, as visuals can often be easier to understand than text descriptions.

This capability is currently not available (Phase 1) but is planned for future development (Phase 2):

1.  **Current System Focus (Text Extraction):** The backend agents (including the subagent for APG Cheat Sheets) are currently designed to extract and process the *textual content* from documents. They analyze the words, sentences, and structure but do not interpret or render images, diagrams, or embedded graphical elements within those documents. Therefore, any information derived from cheat sheets is presented as synthesized text.
2.  **Future Enhancement (Document/Image Viewer):** Displaying graphics directly requires different functionality, typically involving a front-end component or integrated document viewer capable of rendering image files (like PNG, JPG) or potentially PDF documents. Implementing such a viewer is a significant piece of work planned for a future development phase (Phase 2). This would allow the system to potentially retrieve the original cheat sheet file and display it alongside or linked from the text-based summary.

**Outcome for APG Team:**
In the current version of the application, the APG team will receive text-based summaries and extractions from the APG Cheat Sheets. The ability to view the original graphics directly within the chat is a recognized enhancement planned for Phase 2, which depends on developing and integrating document/image viewing capabilities into the user interface.

---

## Issue 21: Clearly Indicating CAPM as Authoritative Internal Source

**Feedback:**
"CAPM needs to be clearly indicated as the authoritative source. Can you please add a disclaimer or bold any external sources so that it is clear to users?"

**Analysis/Solution:**
Following up on the source hierarchy discussions in Issues 8 and 9, the APG team requested that CAPM (Central Accounting Policy Manual) be clearly identified as the authoritative *internal* source within the system's responses. The suggestion included potentially using formatting like bolding to distinguish external sources visually.

The core fix focused on ensuring the system's internal understanding and prioritization were correct, primarily through updates to the global database descriptions:

1.  **Explicit CAPM Authority in Database Statement:** The description for `internal_capm` in `iris/src/global_prompts/database_statement.py` was updated to leave no doubt about its status for the agents processing the information:
    ```python
    # File: iris/src/global_prompts/database_statement.py
    "internal_capm": {
        # ... other fields ...
        "use_when": "Accounting Primary Source: Official RBC policy statements. **Strategy:** The primary source for RBC accounting policy. Always consult first for accounting questions. Check US GAAP flags. **Query:** Use RBC terms, policy areas; check US GAAP flags.",
    },
    ```
    The labels "**Accounting Primary Source**" and "**The primary source for RBC accounting policy**" clearly establish its precedence over other internal sources (like Wiki, Memos, Cheatsheets) and external supplementary sources (EY, PwC, KPMG) for matters of RBC policy.
2.  **Reinforced Hierarchy:** The overall structure and descriptions within `database_statement.py` reinforce the intended hierarchy: Official Standards (IASB) > Internal Policy (CAPM) > Internal Interpretive (Wiki, Memos, Cheatsheets) > External Supplementary (EY, PwC, KPMG).
3.  **Visual Distinction (UI/Summarizer Task):** While explicitly bolding external sources in the final output is a formatting choice handled by the Summarizer agent (based on its instructions in `summarizer_settings.py`) or potentially the final UI rendering, the crucial step was ensuring the backend agents *understand* CAPM's authority. The Summarizer's instructions on pattern recognition (`PRIORITIZE AUTHORITATIVE SOURCES`) guide it to give appropriate weight to CAPM findings during synthesis.

**Outcome for APG Team:**
The system's internal configuration now explicitly defines CAPM as the primary internal authoritative source. This ensures that all agents prioritize information from CAPM appropriately when formulating internal reports and synthesizing the final answer. While specific formatting like bolding depends on the Summarizer/UI, the underlying logic correctly reflects CAPM's authoritative status, leading to responses that should implicitly (and potentially explicitly, depending on Summarizer output) give precedence to CAPM guidance over other internal or external interpretive materials.

---

## Issue 12: Overly Condensed Criteria from Cheat Sheet

**Feedback:**
"I asked "under IFRS, APG cheat sheet, what are the criteria for held of sale?". The response provided was too condensed for the criteria for the sale is highly probable. Can we include the exact words for the criteria as show on the cheatsheet. Also, the response needs to clarify that 'all criteria needs to be met' for the sale to be highly probable."

**Analysis/Solution:**
The APG team observed that when asking for specific criteria from an APG Cheat Sheet (e.g., "held for sale" criteria), the response was overly summarized, didn't provide the exact wording, and missed crucial conditions (like "all criteria must be met").

This requires the system to be more precise when handling queries that ask for specific lists, rules, or criteria. The fix primarily relies on enhanced instructions for the Summarizer agent, as the Cheat Sheet subagent itself (`iris/src/agents/database_subagents/internal_cheatsheet/subagent.py`) is currently a placeholder stub and doesn't perform detailed extraction yet.

1.  **Summarizer Instructions for Precision:** The Summarizer agent's prompt (`iris/src/agents/agent_summarizer/summarizer_settings.py`) includes instructions designed to handle this type of request more accurately once the subagent provides the necessary details:
    *   **Adaptive Synthesis:** It analyzes the query intent. For direct questions asking for criteria, it's instructed to provide a concise answer focused on the most relevant information (which should be the criteria themselves).
    *   **Representing Logical Tests:** Crucially, it's instructed to accurately represent logical tests and conditions found in the internal reports it receives from subagents:
        ```python
        # File: iris/src/agents/agent_summarizer/summarizer_settings.py
        # Within <RESEARCH_SCOPE> -> B. Complex/Research-Oriented:
        "    7. **Represent Logical Tests:** Carefully identify any logical test criteria (e.g., 'and-tests', 'or-tests', multi-step conditions) detailed in the internal research reports. Ensure these tests are fully and accurately represented in your final synthesized answer, maintaining their logical structure."
        ```
        This means if a subagent's report includes criteria with a condition like "all must be met," the Summarizer is tasked with preserving and presenting that accurately.
2.  **Subagent Enhancement (Required):** For this fix to be fully effective for Cheat Sheets, the placeholder stub for the `internal_cheatsheet` subagent needs to be replaced with a functional implementation. This implementation would need its own prompt instructions (similar to the CAPM subagent's) to specifically extract verbatim criteria and their associated conditions (like "all must be met") from the cheat sheet documents into its internal report for the Summarizer.

**Outcome for APG Team:**
The Summarizer agent is now better equipped to handle requests for specific criteria by accurately representing logical conditions provided by subagents. However, for APG Cheat Sheets specifically, the full benefit will be realized once the placeholder subagent is replaced with one that performs detailed, verbatim extraction of criteria and conditions. Once that is done, the system should provide less condensed, more precise answers for these types of queries, including exact wording and necessary conditions like "all criteria must be met."

---

## Issue 13: Including Unnecessary Standard Sections (Measurement, Presentation, Disclosure)

**Feedback:**
"Depending on the question asked, certain responses do not need to provide guidance for measurement/presentation/disclosure requirements. For example, the question I asked for #13 [referring to Issue 12's example] above. This should help shorten the response."

**Analysis/Solution:**
The APG team noted that even when asking about a specific accounting aspect (e.g., recognition criteria), the response sometimes included details about related but unasked-for aspects (e.g., measurement, presentation, disclosure), making the answer longer and less focused than desired.

This was addressed primarily by refining the instructions for the Summarizer agent, which controls the final output, and leveraging filtering in the subagents:

1.  **Summarizer Adaptive Synthesis:** The core fix lies in the "Adaptive Synthesis Requirements" within the Summarizer's prompt (`iris/src/agents/agent_summarizer/summarizer_settings.py`). This section instructs the Summarizer to first analyze the original query's intent (simple/direct vs. complex/research).
    *   **For Simple/Direct Queries:** If the query asks about a specific aspect (like recognition criteria), the Summarizer is instructed to provide a concise answer focused *only* on that aspect and to minimize detail about other areas unless essential for context.
        ```python
        # File: iris/src/agents/agent_summarizer/summarizer_settings.py
        # Within <RESEARCH_SCOPE> -> A. Simple/Direct:
        "    1. **Provide a Concise Answer:** Focus on directly answering the specific question using only the most relevant information extracted from the internal reports."
        "    2. **Minimize Detail:** Avoid extensive background, comparison of multiple sources, detailed procedural steps, or discussion of conflicts/gaps unless *essential* to directly answer the simple question."
        ```
    *   **For Complex/Research Queries:** For broader queries, the Summarizer is instructed to perform a more comprehensive synthesis, which might naturally include related aspects if relevant to the overall analysis requested.
2.  **Subagent Filtering:** While the Summarizer makes the final decision on scope, the database subagents also contribute by filtering information based on the specified *standard* and *type* (e.g., asset/liability) as per their `CRITICAL STANDARD FILTERING` and `CRITICAL TYPE FILTERING` instructions (seen in files like `internal_capm/content_synthesis_prompt.py`). This pre-filtering reduces the amount of potentially irrelevant information (e.g., about liabilities when assets were asked for) reaching the Summarizer.

**Outcome for APG Team:**
Through the Summarizer's adaptive logic, the system now aims to better match the scope and detail of the response to the specific aspect the APG team asked about. For targeted questions (e.g., focusing solely on recognition), the response should be more concise and exclude unnecessary details about measurement, presentation, or disclosure, leading to shorter, more relevant answers. Broader questions may still receive more comprehensive answers covering related aspects if deemed relevant by the Summarizer's analysis.

---

## Issue 14: Requiring User to Specify Accounting Standard

**Feedback:**
"Is it necessary to specify the IFRS standard or CAPM for the tool to research? It asked me to specify but users might not know which standard to choose."

**Analysis/Solution:**
The APG team rightly pointed out that being asked to specify an accounting standard (like IFRS or a specific CAPM policy) can be a barrier if the user isn't sure which standard applies.

This was addressed by making the system smarter about handling standards:

1.  **IFRS Default:** The system now assumes **IFRS** as the default accounting standard if none is specified in the query. This is implemented via instructions in the database subagent prompts (like `iris/src/agents/database_subagents/internal_capm/content_synthesis_prompt.py` and others):
    ```python
    # File: iris/src/agents/database_subagents/*/content_synthesis_prompt.py
    # Inside step 4. **Generate Focused Detailed Research Report:**
    "   * **CRITICAL STANDARD FILTERING:** Focus your synthesis *only* on information relevant to the accounting standard specified or implied in the <USER_QUERY> (Defaulting to IFRS if none is specified)..."
    ```
2.  **Smarter Clarification:** The Clarifier agent (`iris/src/agents/agent_clarifier/clarifier_settings.py`) was specifically instructed to avoid asking for the standard unless absolutely necessary. Its prompt now emphasizes the IFRS default and tells it *not* to ask unless there's significant ambiguity (e.g., the query mentions both IFRS and US GAAP confusingly) that prevents effective research:
    ```python
    # File: iris/src/agents/agent_clarifier/clarifier_settings.py
    # Within <REQUEST_ESSENTIAL_CONTEXT_PATH>:
    # "- If the accounting standard (e.g., IFRS, US GAAP) is unclear AND critical for distinguishing the research path, what standard applies? (Note: Remind yourself that the default is IFRS if unspecified, so only ask if ambiguity significantly hinders research direction)."
    # Also within <CONTEXT_SUFFICIENCY_CRITERIA>:
    # "AVOID requesting context if the user explicitly states they cannot provide more clarity..."
    # "When in doubt, proceed with research rather than asking for more context."
    ```
3.  **Implicit US GAAP Detection:** The system was also improved to better recognize when US GAAP is explicitly mentioned or strongly implied, ensuring it focuses correctly in those cases without needing clarification.

**Outcome for APG Team:**
The APG team is no longer required to specify "IFRS" for most queries. The system defaults to IFRS automatically. Clarification questions about the standard will only be asked in rare cases of genuine ambiguity that the system cannot resolve itself. This provides a much smoother and user-friendly experience, especially when the applicable standard isn't immediately known. Explicit requests for US GAAP or other standards are still handled correctly.

---

## Issue 15: Responses Appearing Unconsolidated

**Feedback:**
"The tool seems to be providing separate responses from the CAPM, wiki and internal memos (including sub-sections to each response) vs. consolidating the research into one result. This might be confusing to users, and also makes the responses quite lengthy. Is it possible to summarize into one?"

**Analysis/Solution:**
The APG team observed that responses sometimes appeared as separate sections for each database searched (CAPM, Wiki, Memos), rather than a single, consolidated answer. This could be confusing and make responses lengthy.

This issue was resolved as part of the architectural improvements described in Issue 2 (Parallel Processing) and Issue 4 (Streamlined Response Format), specifically through the role of the Summarizer agent:

1.  **Parallel Backend Research:** As covered in Issue 2, relevant databases are now queried simultaneously in the background. Each database subagent produces its own internal findings report.
2.  **Centralized Synthesis Task:** The Summarizer agent (`iris/src/agents/agent_summarizer/summarizer.py`) is specifically designed to take these multiple, separate internal reports as input (in the `aggregated_detailed_research` dictionary).
3.  **Explicit Consolidation Instruction:** The Summarizer's core instruction, defined in its settings (`iris/src/agents/agent_summarizer/summarizer_settings.py`), is *not* to list the findings separately, but to synthesize them into **one single, coherent, user-facing research report**. It's guided by instructions like:
    ```python
    # File: iris/src/agents/agent_summarizer/summarizer_settings.py
    # Within <PATTERN_RECOGNITION_INSTRUCTIONS>:
    # "1. IDENTIFY CONSENSUS: Note when multiple sources agree..."
    # "2. HIGHLIGHT CONTRADICTIONS: Explicitly call out when sources provide conflicting information..."
    # "5. CROSS-REFERENCE: Connect related information across different database sources..."
    # "6. PRIORITIZE AUTHORITATIVE SOURCES..."

    # File: iris/src/agents/agent_summarizer/summarizer.py
    # User message instructing the LLM:
    # "Please generate the comprehensive research summary based on the provided context and requirements. Synthesize the findings from all sources into a single, coherent response."
    ```
    These instructions ensure the agent's goal is integration, not just concatenation.
4.  **Streamlined Presentation:** As per Issue 4, the UI no longer shows the intermediate internal reports from each database. The APG team only sees the final, single output produced by the Summarizer after it has performed this consolidation.

**Outcome for APG Team:**
The system is now explicitly designed to consolidate findings. While research happens across multiple databases in the background, the Summarizer agent's specific task is to integrate these findings into a single, unified response. Combined with the streamlined UI, the APG team should no longer see separate, unconsolidated results but rather one coherent answer reflecting the synthesized information from all relevant sources consulted.

---

## Issue 16: Including Unnecessary Details Beyond Specific Query Aspect (e.g., Classification)

**Feedback:**
"Similar to #13 above, I asked specifically for classification of financial assets but the response included subsequent measurement, impairment, derecognition etc. requirements which were not necessary."

**Analysis/Solution:**
This feedback provides a concrete example related to Issue 13. The APG team asked specifically about the *classification* of financial assets but received a response that also included details on subsequent measurement, impairment, and derecognition, making the answer unnecessarily long for the specific question asked.

The solution implemented for Issue 13 directly addresses this scenario:

1.  **Summarizer Adaptive Synthesis:** The Summarizer agent (`iris/src/agents/agent_summarizer/summarizer_settings.py`) is instructed to analyze the query intent. For a direct query like "how is a financial asset classified?", it identifies this as a "Simple/Direct" request.
2.  **Focused Output for Simple Queries:** Based on this identification, the Summarizer follows instructions to provide a concise answer focused *only* on the requested aspect (classification) and to minimize details about other aspects (measurement, impairment, derecognition) unless essential for understanding the classification itself.
    ```python
    # File: iris/src/agents/agent_summarizer/summarizer_settings.py
    # Within <RESEARCH_SCOPE> -> A. Simple/Direct:
    "    1. **Provide a Concise Answer:** Focus on directly answering the specific question using only the most relevant information extracted from the internal reports."
    "    2. **Minimize Detail:** Avoid extensive background, comparison of multiple sources, detailed procedural steps, or discussion of conflicts/gaps unless *essential* to directly answer the simple question."
    ```
3.  **Subagent Filtering (Supporting Role):** Instructions like `CRITICAL TYPE FILTERING` in subagent prompts (e.g., `internal_capm/content_synthesis_prompt.py`) also help by ensuring the subagents primarily extract information related to the specified type (financial assets in this case).

**Outcome for APG Team:**
When the APG team asks a narrowly focused question, such as specifically about classification rules, the Summarizer's adaptive logic ensures the response concentrates on that aspect. Extraneous details about subsequent measurement, impairment, derecognition, etc., should now be omitted, resulting in shorter, more targeted answers that directly address the specific classification query.

---

## Issue 17: Hyperlinking CAPM Section References

**Feedback:**
"Is it possible to hyperlink the CAPM section references so users can directly click for more information?"

**Analysis/Solution:**
The APG team asked if the source citations provided in responses (e.g., for CAPM sections) could be made into clickable hyperlinks that lead directly to the referenced document or section.

This valuable feature is planned but not yet implemented:

1.  **Current Implementation (Phase 1 - Text Citations):** The system is currently designed to generate text-based citations. Instructions in agent prompts, like those for subagents (`internal_capm/content_synthesis_prompt.py`, etc.) and the Summarizer (`summarizer_settings.py`), focus on extracting and formatting the source information (document name, section/path) as text within the response, for example: `(Source: [Document Identifier], Path: [Full Hierarchy Path], ...)`. There is no backend logic currently to generate or embed actual hyperlinks.
2.  **Future Enhancement (Phase 2 - Hyperlinking):** Adding clickable hyperlinks is a planned enhancement for Phase 2. This requires significant work beyond the current backend agent capabilities, including:
    *   **Link Generation:** A mechanism to reliably determine the correct and stable URL for specific documents and potentially sections within the source repositories (like PPL).
    *   **UI Integration:** Changes to the front-end chat interface to render these text citations as clickable links.
    *   **Access Control:** Ensuring that clicking a link respects user permissions for the target document.

**Outcome for APG Team:**
In the current version (Phase 1), the APG team will continue to receive citations as plain text, providing the source details needed for manual lookup. The ability to click directly on these citations via hyperlinks is a planned feature for Phase 2, requiring further development work on link generation and UI integration.

---

## Issue 18: Response Too Detailed for Simple Classification Query

**Feedback:**
"I asked "how is a financial asset classified?". The response was too detailed/long - it should stop after criteria for classification to allow the user to continue asking interactive questions specific to their situation."

**Analysis/Solution:**
This feedback provides another specific example illustrating the concerns raised in Issue 13 and Issue 16. The APG team asked a direct question ("how is a financial asset classified?") expecting a focused answer on classification criteria, but received a much longer response including subsequent measurement, derecognition, etc. This level of detail was not requested and hindered the ability to ask interactive follow-up questions easily.

The solution is the same adaptive synthesis logic implemented for Issues 13 and 16, primarily controlled by the Summarizer agent:

1.  **Query Intent Analysis:** The Summarizer agent (`iris/src/agents/agent_summarizer/summarizer_settings.py`) analyzes the query. A question like "how is a financial asset classified?" is identified as a "Simple/Direct" request.
2.  **Concise, Focused Response:** For such simple/direct queries, the Summarizer is explicitly instructed to provide a concise answer focused *only* on the specific aspect requested (classification criteria in this case) and to minimize or filter out details related to other accounting lifecycle stages (measurement, impairment, derecognition) unless strictly necessary for context. The goal is brevity and directness, allowing for easier follow-up.
    ```python
    # File: iris/src/agents/agent_summarizer/summarizer_settings.py
    # Within <RESEARCH_SCOPE> -> A. Simple/Direct:
    "    1. **Provide a Concise Answer:** Focus on directly answering the specific question using only the most relevant information extracted from the internal reports."
    "    2. **Minimize Detail:** Avoid extensive background, comparison of multiple sources, detailed procedural steps, or discussion of conflicts/gaps unless *essential* to directly answer the simple question."
    ```

**Outcome for APG Team:**
With the adaptive synthesis logic, when the APG team asks a direct question like "how is a financial asset classified?", the system should now provide a response focused primarily on the classification criteria itself. Extraneous details about subsequent accounting steps will be omitted, resulting in a shorter, more targeted answer that facilitates asking specific follow-up questions based on the classification information provided.

---

## Issue 19: Thumbs Up/Down Functionality

**Feedback:**
"What does the thumbs up/thumbs down function represent? Nothing happens when I click on it. It would be helpful to allow users to provide feedback on the responses."

**Analysis/Solution:**
The APG team asked about the thumbs up/down icons next to responses and observed that clicking them currently does nothing.

This was clarified as follows:

1.  **Current Status (Development/Demo Environment):** In the current testing environment, these icons are visual placeholders within the User Interface (UI). They are not yet connected to any backend system to record feedback, so clicking them has no effect.
2.  **Intended Functionality (Production):** The plan for the production version of the application (e.g., within Maven) is for these icons to be fully functional. They will serve as a direct feedback mechanism for the APG team.
    *   **Thumbs Up:** Indicates the response was helpful and accurate.
    *   **Thumbs Down:** Indicates the response was unhelpful or inaccurate.
3.  **Feedback Loop:** The feedback collected through these icons in production will be valuable data. It will be used by the support and development teams to monitor the quality and accuracy of the responses generated by the system, identify areas needing improvement, and potentially help fine-tune the underlying models and prompts over time.

**Outcome for APG Team:**
The thumbs up/down icons are not functional in the current environment, which is expected. The APG team is assured that this feature is planned for the production release, where it will provide a simple way to give feedback on the quality of each response, contributing to the ongoing improvement of the tool.

---

## Issue 20: Displaying Graphical Cheat Sheets (Reiteration)

**Feedback:**
"Is it possible to show the cheatsheet itself (where applicable) in the response vs. a summary of it? The flowcharts/diagrams in the cheatsheets are meant to be easier to digest than words."

**Analysis/Solution:**
*(Note: This feedback reiterates the request from Issue 11)*
The APG team again asked about showing the actual graphics (flowcharts, diagrams) from APG Cheat Sheets in the response, emphasizing that visuals are often easier to understand than text summaries.

As explained for Issue 11, this remains a current limitation planned for future improvement:

1.  **Current System (Text-Based):** The backend agents are built to process and synthesize *text*. They cannot currently render or display images or PDF graphics directly within the chat response. Answers derived from cheat sheets will therefore be text-only summaries or extractions.
2.  **Future Enhancement (Phase 2 - Visual Display):** The ability to display graphical content requires integrating a document or image viewer into the application's front-end UI. This is planned for Phase 2 development. Once implemented, it could allow the system to show the original cheat sheet graphic alongside or linked from the textual summary.

**Outcome for APG Team:**
Currently (Phase 1), responses from APG Cheat Sheets will be text-based. We acknowledge the value of seeing the graphics directly, and this capability is targeted for implementation in Phase 2, requiring the development of visual display features in the user interface.

---

</file_content>

Now that you have the latest state of the file, try the operation again with fewer, more precise SEARCH blocks. For large files especially, it may be prudent to try to limit yourself to <5 SEARCH/REPLACE blocks at a time, then wait for the user to respond with the result of the operation before following up with another replace_in_file call to make additional edits.
(If you run into this error 3 times in a row, you may use the write_to_file tool as a fallback.)
</error><environment_details>
# VSCode Visible Files
FEEDBACK_LOG.md

# VSCode Open Tabs
FEEDBACK_LOG.md

# Current Time
4/25/2025, 1:37:44 PM (America/Halifax, UTC-3:00)

# Context Window Usage
206,607 / 1,048.576K tokens used (20%)

# Current Mode
ACT MODE
</environment_details>
