"""
LLM Judge Prompt Module

This module contains the prompts used to guide the LLM judge in evaluating
test results.
"""

# Base prompt template for LLM judge
JUDGE_PROMPT_TEMPLATE = """
# Test Result Evaluation

You are evaluating the test results for an AI assistant named IRIS. The test results are presented in an Excel sheet that has been converted to markdown format, showing the complete structure of the original data.

## Test Sheet Structure

The Excel sheets typically follow this general structure:
- The test title is usually in cell A1
- Question number may appear around row A4
- The actual question is typically near row A5
- Database selection information will be indicated in rows following the question
- File/document selection information will also appear in subsequent rows
- Scoring information appears throughout columns B and C
- Column B generally contains scoring values
- Column C usually contains reviewer notes that explain the scores
- Scores and notes run throughout the sheet, not just in specific rows

## Your Task

Carefully examine the entire table to find relevant information, then analyze the reviewer's notes and feedback to extract structured insights about IRIS's performance. Provide your evaluation in the following structured format:

```json
{
  "database_selection": {
    "correct": true/false/null,
    "score": numerical score if available or null,
    "comments": "Brief explanation based on reviewer notes"
  },
  "document_selection": {
    "correct": true/false/null,
    "score": numerical score if available or null,
    "comments": "Brief explanation based on reviewer notes"
  },
  "answer_accuracy": {
    "score": numerical score if available (or estimate 1-5 based on comments),
    "comments": "Brief explanation based on reviewer notes"
  },
  "overall_assessment": "Short 1-2 sentence summary of the test result"
}
```

Focus on extracting information that explicitly appears in the reviewer notes. If information about a particular category is not mentioned, set the value to null.

For any score fields:
- Use the actual scores provided in the Excel if available
- If scores are not explicit but descriptions are available, estimate on a 1-5 scale:
  - 5: Perfect/Excellent response
  - 4: Good/Mostly correct
  - 3: Average/Partially correct
  - 2: Poor/Mostly incorrect
  - 1: Completely incorrect/Failed

## Test Result to Evaluate

{test_markdown}

## Response Guidelines

1. Provide only a valid JSON object containing your structured evaluation
2. Base your assessment ONLY on what is explicitly stated in the reviewer notes
3. Do not make assumptions beyond what is directly mentioned
4. Be objective and factual in your evaluation
5. Look through the ENTIRE table to find all relevant information
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