# internal_capm/description_condensation_prompt.py
"""
Prompt templates for condensing detailed CAPM document descriptions.

This module contains prompts used to guide the LLM in generating
concise, plain-text descriptions from detailed markdown descriptions.
"""


def get_description_condensation_prompt(original_description: str) -> str:
    """
    Generate a prompt for condensing a detailed CAPM document description.

    Args:
        original_description (str): The original detailed description with markdown

    Returns:
        str: The formatted prompt for the LLM
    """
    prompt = f"""# TASK
You are helping to create concise, plain-text descriptions for CAPM (Central Accounting Policy Manual) documents.
The original descriptions are detailed and use markdown formatting, which doesn't display well in a list view.
Your task is to create a condensed, plain-text description (no markdown) that captures the essence of the document.

## Original Description
```
{original_description}
```

## Instructions
1. Create a concise description (50-100 words) that summarizes the key purpose and content of the document
2. Use plain text only - no markdown, no bullet points, no special formatting
3. Focus on what information the document contains and what it's used for
4. Maintain a professional, neutral tone
5. Avoid technical jargon unless necessary for understanding the document's purpose

# OUTPUT
Provide ONLY the condensed description with no additional text, explanations, or formatting.
"""
    return prompt
