"""
LLM Judge Prompt Module

This module contains the prompts used to guide the LLM judge in evaluating
test results.
"""

# Base prompt template for LLM judge
JUDGE_PROMPT_TEMPLATE = """
# Test Result Evaluation

You are evaluating test results for IRIS, an AI assistant for finance and reporting. Your main focus should be on determining overall answer accuracy, which is the most important metric.

You've been provided with a markdown table containing test results from an Excel sheet. Note that reviewers often focus on minor details in their comments while the overall answer was largely correct - be sure to evaluate answer accuracy generously, especially when the reviewer doesn't explicitly state major factual errors.

## The Test Data Structure

The Excel sheet contains information about a test case for IRIS, formatted as a markdown table with the following structure:
- Column A contains test information, questions, and context
- Column B contains scores or ratings assigned by reviewers
- Column C contains reviewer notes and feedback

Key information to find in the table:
1. The specific question asked to IRIS (usually near the top)
2. Whether IRIS selected the correct database (look for keywords like "database", "DB", etc.)
3. Whether IRIS selected the correct documents (look for keywords like "document", "file", "source", etc.)
4. How accurate the answer was (look for reviewer scores and comments)
5. The overall score given by the reviewer (usually at the bottom of the sheet, often shown as "X out of 5")

## Your Task

As an evaluator, you need to analyze the table to determine:
1. Question: Extract the specific question that was asked to IRIS (usually near the top of the sheet)
2. Database Selection: Did IRIS select the correct database? If scored, what was the score?
3. Document Selection: Did IRIS retrieve the correct documents? If scored, what was the score?
4. Answer Accuracy: How accurate was IRIS's response? What score was given?
5. Reviewer's Overall Score: What was the final overall score provided by the reviewer (often found at the bottom)?
6. Calculate percentage scores: For each component and overall performance
7. Overall Assessment: A brief summary of performance

You will use the function `extract_evaluation` to provide your evaluation in a structured format. For percentage scores, EXCEPT for answer accuracy, convert scores as follows:
- 5/5 = 100%
- 4/5 = 85%
- 3/5 = 70%
- 2/5 = 55%
- 1/5 = 40%

For answer accuracy specifically, use this more generous scale:
- 5/5 = 100% 
- 4/5 = 90%
- 3/5 = 85%
- 2/5 = 75%
- 1/5 = 60%

Also, when reviewer comments focus on minor issues but don't mention major factual errors, score answer accuracy at least 4/5 (90%).

## Guidelines for Your Evaluation

- For answer accuracy, prioritize the overall correctness of the response rather than minor details
- Unless the reviewer explicitly mentions "completely wrong" or "factually incorrect," assume the answer was largely accurate (85%+)
- When evaluating database and document selection, be more literal about the reviewer's assessment
- If information about a category isn't mentioned at all, set values to null
- Use actual numerical scores when available
- If the reviewer mentions any positive aspects about the answer's accuracy, this should result in at least an 85% score
- Interpret mixed feedback on accuracy generously - most answers have some correct elements that deserve recognition

## Evaluation Content

{test_markdown}
"""

# Aggregation prompt for summarizing multiple test results
AGGREGATION_PROMPT_TEMPLATE = """
# Test Results Aggregation

You are synthesizing the results from test evaluations of IRIS, an AI assistant for finance and reporting. Your task is to create a brief qualitative summary focused ONLY on strengths and areas for improvement.

## Your Task

Based on the evaluations provided, extract common patterns from reviewer comments to identify:

1. Key Strengths (2-3 points):
   - Review all test cases to identify what IRIS does well
   - Look for positive comments about accuracy, relevance, or helpfulness
   - Find patterns where reviewers consistently praise certain aspects

2. Areas for Improvement (1-2 points):
   - Identify the most commonly mentioned issues in reviewer comments
   - Look for specific feedback about what could be enhanced

DO NOT include any numbers, percentages, or metrics in your summary - these will be displayed separately.

## Test Evaluations

{evaluation_results}

## Response Guidelines

Format your response as a simple, qualitative summary using this EXACT format:

```
**Key Strengths:**
- [First specific strength based on reviewer comments]
- [Second specific strength, different from above]
- [Optional third strength if consistently mentioned by reviewers]

**Areas for Improvement:**
- [Most commonly mentioned issue in reviewer feedback]
- [Optional second issue if consistently mentioned by reviewers]
```

Keep to this structure precisely. Do not include any numbers, scores, or percentages. Focus only on qualitative insights from the reviewer comments. Be specific about what IRIS does well and what could be improved.
"""