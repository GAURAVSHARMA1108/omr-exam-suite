import re
from typing import List, Dict, Any

def parse_bulk_questions(text: str) -> List[Dict[str, Any]]:
    """
    Parses natural language/formatted text into structured questions with options and answers.
    Supports varied numbering formats, A/B/C/D patterns, and Answer/Ans/Correct markers.
    """
    if not text or not text.strip():
        return []

    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    raw_blocks: List[List[str]] = []
    current_block: List[str] = []

    # Detect start of a new question
    # Matches: "1.", "1)", "Q1.", "Q1:", "Question 1:", "1 - ", etc.
    q_start_pattern = re.compile(
        r'^(?:Q(?:uestion)?\s*[\d]+[:\.\)]|[\d]+[\.\)\:\-]\s+)', 
        re.IGNORECASE
    )

    for line in lines:
        if q_start_pattern.match(line) and current_block:
            raw_blocks.append(current_block)
            current_block = [line]
        else:
            current_block.append(line)

    if current_block:
        raw_blocks.append(current_block)

    parsed_questions: List[Dict[str, Any]] = []

    opt_pattern = re.compile(r'^(?:\(?([A-Ea-e])\)|\b([A-Ea-e])[\.\:\-])\s*(.*)$')
    ans_pattern = re.compile(r'^(?:Ans(?:wer)?|Correct(?:\s*Option)?|Key)[\s\:\-\=]+(?:\(?([A-Ea-e])\)?|(.*))', re.IGNORECASE)

    for idx, block in enumerate(raw_blocks, start=1):
        q_text_lines: List[str] = []
        options_dict: Dict[str, str] = {}
        correct_opt = "A" # fallback default
        current_opt_key = None

        first_line = block[0]
        # Strip leading question number/prefix
        cleaned_first_line = re.sub(r'^(?:Q(?:uestion)?\s*[\d]+[:\.\)]\s*|[\d]+[\.\)\:\-]\s*)', '', first_line).strip()
        q_text_lines.append(cleaned_first_line)

        for line in block[1:]:
            ans_match = ans_pattern.match(line)
            if ans_match:
                key_found = ans_match.group(1) or ans_match.group(2)
                if key_found:
                    # Look for single letter A-E in key_found
                    single_char = re.search(r'[A-Ea-e]', key_found)
                    if single_char:
                        correct_opt = single_char.group(0).upper()
                continue

            opt_match = opt_pattern.match(line)
            if opt_match:
                letter = (opt_match.group(1) or opt_match.group(2)).upper()
                opt_content = opt_match.group(3).strip()
                current_opt_key = letter
                options_dict[letter] = opt_content
            elif current_opt_key and current_opt_key in options_dict:
                # Continuation of option text
                options_dict[current_opt_key] += " " + line
            else:
                # Still part of question prompt / description
                q_text_lines.append(line)

        # Standardize options into list [A, B, C, D]
        letters = sorted(options_dict.keys())
        if not letters:
            # Fallback if no explicit options found in block: create standard default options
            options_list = ["Option A", "Option B", "Option C", "Option D"]
        else:
            options_list = [options_dict[k] for k in letters]

        parsed_questions.append({
            "question_number": idx,
            "question_text": " ".join(q_text_lines).strip(),
            "options": options_list,
            "correct_option": correct_opt.upper()
        })

    return parsed_questions
