import markdown
import os

def convert_md_to_html_with_style(md_content):
    # Basic CSS for better Word copy-pasting
    # Includes styles for tables, code blocks, and general typography
    # Added MathJax CDN for LaTeX rendering
    html_style = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Document</title>
<script type="text/javascript" async
  src="https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.7/MathJax.js?config=TeX-MML-AM_CHTML">
</script>
<style>
    body {
        font-family: sans-serif;
        line-height: 1.6;
        margin: 20px;
    }
    h1, h2, h3, h4, h5, h6 {
        margin-top: 1.5em;
        margin-bottom: 0.5em;
        line-height: 1.3;
    }
    p {
        margin-bottom: 1em;
    }
    table {
        border-collapse: collapse;
        margin-bottom: 1em;
        width: auto; /* Changed from 100% to auto for better Word compatibility */
        border: 1px solid #ddd; /* Added border for table */
    }
    th, td {
        border: 1px solid #ddd;
        padding: 8px;
        text-align: left;
    }
    th {
        background-color: #f2f2f2;
    }
    pre {
        background-color: #f8f8f8;
        border: 1px solid #ddd;
        padding: 10px;
        overflow-x: auto;
        font-family: monospace;
        white-space: pre-wrap; /* Allow wrapping for long lines in code blocks */
        word-wrap: break-word; /* Break long words if necessary */
    }
    code {
        font-family: monospace;
        background-color: #f0f0f0; /* Light background for inline code */
        padding: 2px 4px;
        border-radius: 3px;
    }
    blockquote {
        border-left: 4px solid #ddd;
        padding-left: 10px;
        color: #555;
        margin-left: 0;
    }
    ul, ol {
        margin-bottom: 1em;
        padding-left: 20px;
    }
    img {
        max-width: 100%;
        height: auto;
    }
    /* MathJax specific styling if needed, though default usually works well */
    .MathJax_Display { 
        display: block; 
        text-align: center; 
        margin: 1em 0; 
        overflow-x: auto; /* Add scroll for very wide equations */
    }
</style>
</head>
<body>
"""
    # Convert markdown to HTML using extensions for tables, fenced code blocks, and math
    # mdx_math configuration: enable_dollar_delimiter for inline math like $...$
    # and use_gitlab_delimiters for block math like ```math ... ```
    html_body = markdown.markdown(
        md_content, 
        extensions=[
            'markdown.extensions.tables', 
            'markdown.extensions.fenced_code',
            'pymdownx.arithmatex'  # Using arithmatex as it's a common choice in pymdown-extensions for math
        ],
        extension_configs={
            'pymdownx.arithmatex': {
                'generic': True # Enables both $...$ and $$...$$ for math
            }
        }
    )
    
    html_full = f"{html_style}{html_body}</body></html>"
    return html_full

def main():
    input_dir = "docs/model_documentation/"
    output_dir = "docs/model_documentation_word_friendly/"

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")

    md_files = [f for f in os.listdir(input_dir) if f.endswith(".md")]

    if not md_files:
        print(f"No Markdown files found in {input_dir}")
        return

    print(f"Found {len(md_files)} Markdown files to convert.")

    for md_file_name in md_files:
        md_file_path = os.path.join(input_dir, md_file_name)
        html_file_name = os.path.splitext(md_file_name)[0] + ".html"
        html_file_path = os.path.join(output_dir, html_file_name)

        try:
            with open(md_file_path, 'r', encoding='utf-8') as f_md:
                md_content = f_md.read()
            
            html_content = convert_md_to_html_with_style(md_content)
            
            with open(html_file_path, 'w', encoding='utf-8') as f_html:
                f_html.write(html_content)
            
            print(f"Successfully converted '{md_file_path}' to '{html_file_path}'")
        except Exception as e:
            print(f"Error converting file {md_file_path}: {e}")

if __name__ == "__main__":
    main()
