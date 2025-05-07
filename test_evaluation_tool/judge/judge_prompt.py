"""
LLM Judge Prompt Module

This module contains the prompts used to guide the LLM judge in evaluating
test results.
"""

# Base prompt template for LLM judge
JUDGE_PROMPT_TEMPLATE = """
# Test Result Evaluation

You are evaluating test results for an AI assistant named IRIS. You've been provided with a markdown table containing test results from an Excel sheet.

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

## Your Task

As an evaluator, you need to analyze the table to determine:
1. Database Selection: Did IRIS select the correct database?
2. Document Selection: Did IRIS retrieve the correct documents?
3. Answer Accuracy: How accurate was IRIS's response?
4. Overall Assessment: A brief summary of performance

You will use the function `extract_evaluation` to provide your evaluation in a structured format.

## Guidelines for Your Evaluation

- Look for explicit evidence in the reviewer notes
- If information about a category isn't mentioned, set values to null
- Use actual numerical scores when available
- Provide brief but specific comments based on the reviewer notes
- Be objective and focus on facts stated in the reviewer notes

## Evaluation Content

{test_markdown}
"""

# Aggregation prompt for summarizing multiple test results
AGGREGATION_PROMPT_TEMPLATE = """
# Test Results Aggregation

You are synthesizing the results from multiple test evaluations of an AI assistant named IRIS. Each test evaluation contains structured assessments of IRIS's performance across various dimensions.

## Your Task

Based on the collection of test evaluations provided, generate a comprehensive summary that highlights:

1. Overall Performance: Synthesize the general performance of IRIS across all tests
2. Database Selection Accuracy: How accurately IRIS selected the appropriate database for queries
3. Document Selection Accuracy: How effectively IRIS identified and retrieved relevant documents
4. Answer Accuracy: The overall quality of IRIS's responses to questions
5. Key Strengths: Areas where IRIS consistently performed well
6. Key Weaknesses: Areas where IRIS struggled or needs improvement
7. Quantitative Summary: Provide numerical summaries where possible (e.g., percentage of correct database selections)

## Test Evaluations

{evaluation_results}

## Response Guidelines

Structure your response as a formal assessment report with clear sections for each area mentioned above. Include both qualitative insights and quantitative measures where possible. Focus on actionable findings that could guide future improvements to the system.
"""