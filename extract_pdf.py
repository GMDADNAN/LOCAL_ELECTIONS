"""
One-time script to extract all voter data from the PDF and save as JSON.
Run this once before starting the app.
"""
import pymupdf
import json
import re
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

PDF_PATH = r"D:\Zubair_mamu\MLA_PDF\9_highlighted_updated_with_photos.pdf"
OUTPUT_JSON = os.path.join(os.path.dirname(__file__), "voter_data.json")


def clean(text):
    """Strip leading/trailing whitespace, colons, and stray label fragments."""
    text = str(text).strip()
    # Remove leading colon or 'పేరు :' label artifacts
    text = re.sub(r'^[:\s]+', '', text)
    text = re.sub(r'^పేరు\s*:\s*', '', text)
    return text.strip()


def extract_voters():
    print(f"Opening PDF: {PDF_PATH}")
    doc = pymupdf.open(PDF_PATH)
    total_pages = doc.page_count
    print(f"Total pages: {total_pages}")

    voters = []
    current_voter = {}

    # Pages 1-9 are index/summary pages; voter records start from page 10 (index 9)
    VOTER_START_PAGE = 9  # 0-indexed

    def save_current():
        if current_voter and current_voter.get('voter_name'):
            voters.append(dict(current_voter))

    for page_num in range(VOTER_START_PAGE, total_pages):
        page = doc[page_num]
        text = page.get_text("text")
        lines = [l.strip() for l in text.split('\n') if l.strip()]

        i = 0
        while i < len(lines):
            line = lines[i]

            # ── New voter record ──────────────────────────────────────────────
            if 'వార్డు.ఓ.జా.వ.సం.' in line:
                save_current()
                current_voter = {}
                num_match = re.search(r'\d+', line.split('వార్డు.ఓ.జా.వ.సం.')[-1])
                if num_match:
                    current_voter['ward_serial'] = num_match.group()
                i += 1
                continue

            # ── Assembly serial ───────────────────────────────────────────────
            if 'అ.ఓ.జా.వ.సం' in line:
                # e.g. "అ.ఓ.జా.వ.సం .137 - 1 - 5"
                val = re.sub(r'అ\.ఓ\.జా\.వ\.సం\s*\.?', '', line).strip().strip(':').strip()
                current_voter['assembly_serial'] = val
                i += 1
                continue

            # ── Voter name ───────────────────────────────────────────────────
            if 'ఓటరు పేరు' in line:
                # Value may be on same line after ':' or on next line
                val = line.split(':', 1)[-1].strip() if ':' in line else ''
                # Accumulate continuation lines
                while i + 1 < len(lines) and not any(kw in lines[i + 1] for kw in [
                    'తండ్రి', 'భర్త', 'వయస్సు', 'లింగము', 'ఇంటి',
                    'ఓటరు ఐడి', 'కార్డు', 'Photo',
                    'వార్డు.ఓ.జా.వ.సం', 'అ.ఓ.జా.వ.సం', 'SEC ANDHRA'
                ]):
                    i += 1
                    val = (val + ' ' + lines[i]).strip()
                current_voter['voter_name'] = clean(val)
                i += 1
                continue

            # ── Father / Husband name ────────────────────────────────────────
            if 'తండ్రి' in line or 'భర్త పేరు' in line:
                current_voter['relation_type'] = 'father' if 'తండ్రి' in line else 'husband'
                val = line.split(':', 1)[-1].strip() if ':' in line else ''
                while i + 1 < len(lines) and not any(kw in lines[i + 1] for kw in [
                    'వయస్సు', 'లింగము', 'ఇంటి', 'ఓటరు ఐడి', 'కార్డు', 'Photo',
                    'వార్డు.ఓ.జా.వ.సం', 'అ.ఓ.జా.వ.సం', 'తండ్రి', 'భర్త', 'SEC ANDHRA'
                ]):
                    i += 1
                    val = (val + ' ' + lines[i]).strip()
                current_voter['relation_name'] = clean(val)
                i += 1
                continue

            # ── Age ──────────────────────────────────────────────────────────
            if 'వయస్సు' in line:
                val = line.split(':', 1)[-1].strip() if ':' in line else ''
                if not val and i + 1 < len(lines):
                    i += 1
                    val = lines[i].strip()
                # Keep only the numeric part
                num = re.search(r'\d+', val)
                current_voter['age'] = num.group() if num else val
                i += 1
                continue

            # ── Gender ───────────────────────────────────────────────────────
            if 'లింగము' in line:
                val = line.split(':', 1)[-1].strip() if ':' in line else ''
                if not val and i + 1 < len(lines):
                    i += 1
                    val = lines[i].strip()
                # Normalise to English
                if 'పు' in val:
                    current_voter['gender'] = 'Male'
                elif 'స్' in val:
                    current_voter['gender'] = 'Female'
                else:
                    current_voter['gender'] = clean(val)
                i += 1
                continue

            # ── House number ─────────────────────────────────────────────────
            if 'ఇంటి సంఖ్య' in line:
                val = line.split(':', 1)[-1].strip() if ':' in line else ''
                if not val and i + 1 < len(lines):
                    i += 1
                    val = lines[i].strip()
                current_voter['house_number'] = clean(val)
                i += 1
                continue

            # ── Voter ID card ─────────────────────────────────────────────────
            if 'ఓటరు ఐడి' in line or 'కార్డు నెం' in line:
                val = line.split(':', 1)[-1].strip() if ':' in line else ''
                if not val and i + 1 < len(lines):
                    i += 1
                    val = lines[i].strip()
                # If ID split across lines, collect it
                if val and re.match(r'^[A-Z]{3}\d+', val):
                    current_voter['voter_id'] = val.strip()
                elif i + 1 < len(lines) and re.match(r'^[A-Z]{3}\d+', lines[i + 1].strip()):
                    i += 1
                    current_voter['voter_id'] = lines[i].strip()
                else:
                    current_voter['voter_id'] = clean(val)
                i += 1
                continue

            i += 1

    # Save last record
    save_current()

    # Final clean-up: only keep records that have a voter name
    cleaned = [v for v in voters if v.get('voter_name')]

    print(f"\nTotal voters extracted: {len(cleaned)}")

    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)

    print(f"Saved to: {OUTPUT_JSON}")
    return cleaned


if __name__ == '__main__':
    extract_voters()
