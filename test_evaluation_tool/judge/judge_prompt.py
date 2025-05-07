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

You will use the function `extract_evaluation` to provide your evaluation in a structured format. For percentage scores, convert any 0-5 scores to 0-100% (e.g., 4/5 = 80%).

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

You are synthesizing the results from multiple test evaluations of an AI assistant named IRIS. Each test evaluation contains structured assessments of IRIS's performance across various dimensions, including percentage scores.

## Your Task

Based on the collection of test evaluations provided, generate a comprehensive summary that highlights:

1. Overall Performance: 
   - Calculate the average overall percentage score across all tests
   - Synthesize the general performance of IRIS across all tests

2. Database Selection Accuracy: 
   - Calculate the average database selection percentage score
   - Calculate what percentage of tests had correct database selection
   - Summarize how accurately IRIS selected the appropriate database for queries

3. Document Selection Accuracy: 
   - Calculate the average document selection percentage score
   - Calculate what percentage of tests had correct document selection
   - Summarize how effectively IRIS identified and retrieved relevant documents

4. Answer Accuracy: 
   - Calculate the average answer accuracy percentage score
   - Summarize the overall quality of IRIS's responses to questions

5. Key Strengths: 
   - Areas where IRIS consistently performed well
   - Components with the highest average percentage scores

6. Key Weaknesses: 
   - Areas where IRIS struggled or needs improvement
   - Components with the lowest average percentage scores

7. Comprehensive Quantitative Summary: 
   - Include all percentage-based metrics in a table format
   - Provide a clear overall score for each major component
   - Calculate confidence intervals where possible

## Test Evaluations

{evaluation_results}

## Response Guidelines

Structure your response as a formal assessment report with clear sections for each area mentioned above. 

1. Begin with an "Executive Summary" that provides the key metrics and findings at a glance
   - This should be 3-5 paragraphs of concise, well-structured text
   - Include a high-level overview of overall performance
   - Highlight 2-3 key strengths and 2-3 key areas for improvement
   - End with 1-2 specific, actionable recommendations
2. Include percentage scores for all metrics
3. Use tables to present numerical data clearly
4. Include both qualitative insights and quantitative measures
5. Focus on actionable findings that could guide future improvements to the system
6. After the executive summary, provide detailed sections for each evaluation dimension
"""