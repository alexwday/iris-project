"""
Select 5 good test questions per document for retrieval testing.

Excludes meta-data type questions (word counts, page counts, author names, etc.)
Prioritizes text-only questions, then multimodal-t questions.
"""

import json
from pathlib import Path
from typing import List, Dict, Any


def load_qa_pairs(folder_path: Path) -> List[Dict[str, Any]]:
    """Load QA pairs from a docbench folder."""
    jsonl_files = list(folder_path.glob("*_qa.jsonl"))
    if not jsonl_files:
        return []

    qa_pairs = []
    with open(jsonl_files[0], 'r') as f:
        for line in f:
            if line.strip():
                qa_pairs.append(json.loads(line))
    return qa_pairs


def get_pdf_name(folder_path: Path) -> str:
    """Get the PDF filename from a docbench folder."""
    pdf_files = list(folder_path.glob("*.pdf"))
    if pdf_files:
        return pdf_files[0].name
    return ""


def is_good_question(qa: Dict[str, Any]) -> bool:
    """Check if a question is a good test question (not metadata)."""
    # Exclude meta-data type questions
    if qa.get("type") == "meta-data":
        return False

    # Also exclude questions that look like metadata even if not tagged
    question = qa.get("question", "").lower()
    bad_patterns = [
        "how many time",
        "how many times",
        "how many pages",
        "how many words",
        "word count",
        "page count",
        "which page",
        "on page",
        "who is the author",
        "who is the first author",
        "who is the last author",
        "author of the paper",
        "published in",
        "publication date",
        "publication year",
    ]
    for pattern in bad_patterns:
        if pattern in question:
            return False

    return True


def select_questions(qa_pairs: List[Dict[str, Any]], n: int = 5) -> List[Dict[str, Any]]:
    """Select n good questions, prioritizing text-only then multimodal-t."""
    good_qs = [qa for qa in qa_pairs if is_good_question(qa)]

    # Separate by type
    text_only = [qa for qa in good_qs if qa.get("type") == "text-only"]
    multimodal = [qa for qa in good_qs if qa.get("type") == "multimodal-t"]

    # Priority: text-only first, then multimodal
    selected = []
    for qa in text_only:
        if len(selected) >= n:
            break
        selected.append(qa)

    for qa in multimodal:
        if len(selected) >= n:
            break
        selected.append(qa)

    return selected


def main():
    docbench_path = Path(__file__).parent.parent.parent / "testing" / "docbench_data" / "data"

    # Documents we processed (folders 0-19)
    doc_folders = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]

    all_selected = []

    print("=" * 80)
    print("QA PAIR SELECTION FOR RETRIEVAL TESTING")
    print("=" * 80)
    print()

    for folder_id in doc_folders:
        folder_path = docbench_path / str(folder_id)
        pdf_name = get_pdf_name(folder_path)
        qa_pairs = load_qa_pairs(folder_path)

        selected = select_questions(qa_pairs, n=5)

        print(f"Document: {pdf_name} (folder {folder_id})")
        print(f"  Total QA pairs: {len(qa_pairs)}")
        print(f"  Good questions: {len([q for q in qa_pairs if is_good_question(q)])}")
        print(f"  Selected: {len(selected)}")

        for i, qa in enumerate(selected, 1):
            print(f"    {i}. [{qa['type']}] {qa['question'][:70]}...")
            all_selected.append({
                "folder_id": folder_id,
                "document_name": pdf_name,
                "question": qa["question"],
                "answer": qa["answer"],
                "type": qa["type"],
                "evidence": qa.get("evidence", "")
            })
        print()

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total documents: {len(doc_folders)}")
    print(f"Total selected questions: {len(all_selected)}")

    # Count by type
    by_type = {}
    for qa in all_selected:
        t = qa["type"]
        by_type[t] = by_type.get(t, 0) + 1
    print(f"By type: {by_type}")

    # Save to JSON for retrieval testing
    output_path = Path(__file__).parent / "selected_qa_pairs.json"
    with open(output_path, 'w') as f:
        json.dump(all_selected, f, indent=2)
    print(f"\nSaved to: {output_path}")


if __name__ == "__main__":
    main()
