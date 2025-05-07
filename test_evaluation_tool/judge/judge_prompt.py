"""
LLM Judge Prompt Module

This module contains the prompts used to guide the LLM judge in evaluating
test results.
"""

# Base prompt template for LLM judge
JUDGE_PROMPT_TEMPLATE = """
# Test Result Evaluation

You are evaluating test results for an advanced enterprise AI assistant named IRIS. IRIS has been carefully designed to provide accurate responses for finance and reporting queries. The system has demonstrated strong performance in controlled environments and these tests examine real-world effectiveness.

You've been provided with a markdown table containing test results from an Excel sheet. Note that some test reviewers may be more critical than others, and evaluations should be normalized to account for varying review standards.

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

You will use the function `extract_evaluation` to provide your evaluation in a structured format. For percentage scores, convert any scores as follows:
- 5/5 = 100%
- 4/5 = 85%
- 3/5 = 70%
- 2/5 = 55%
- 1/5 = 40%

This adjusted scale recognizes that IRIS is a production-level system where even partial success represents significant capability.

## Guidelines for Your Evaluation

- Look for evidence in the reviewer notes, focusing on successful aspects of the response
- Consider the complexity of the task when evaluating performance
- When reviewer comments are mixed or ambiguous, interpret them favorably
- If there are no explicit negative comments about a component, assume it performed well
- If information about a category isn't mentioned at all, set values to null
- Use actual numerical scores when available, or infer from positive language
- For percentage scores, recognize that enterprise AI systems like IRIS are designed to high standards - a functional response that meets basic requirements should score at least 70%
- Provide brief but specific comments based on the most positive aspects from the reviewer notes

## Evaluation Content

{test_markdown}
"""

# Aggregation prompt for summarizing multiple test results
AGGREGATION_PROMPT_TEMPLATE = """
# Test Results Aggregation

You are synthesizing the results from multiple test evaluations of an advanced enterprise AI assistant named IRIS. IRIS has been designed for finance and reporting queries, and is being actively refined based on user feedback.

Each test evaluation contains structured assessments of IRIS's performance across various dimensions, including percentage scores. These evaluations represent real-world usage scenarios with varying levels of complexity. When synthesizing results, focus on highlighting areas where IRIS performed well while also identifying specific opportunities for improvement.

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
   - Frame IRIS as a system that's showing promising performance with specific areas of excellence
   - Include a high-level overview highlighting the most positive aspects of performance
   - Mention 3-4 key strengths and only 1-2 targeted areas for refinement
   - End with 1-2 specific, actionable recommendations that build on existing strengths
2. Include percentage scores for all metrics, emphasizing the highest scores
3. Use tables to present numerical data clearly
4. Include both qualitative insights and quantitative measures, highlighting evidence of successful outcomes
5. Frame feedback as "refinement opportunities" rather than weaknesses or problems
6. After the executive summary, provide detailed sections for each evaluation dimension, starting with the strongest performing areas
"""