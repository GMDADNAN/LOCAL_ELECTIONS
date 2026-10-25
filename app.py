"""
Flask backend for PDF Voter Search Application
Includes Polling Booth mapping and Voter Photo rendering.
"""
from flask import Flask, jsonify, request, render_template_string, send_file
from flask_cors import CORS
import json
import os
import re

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "voter_data.json")
PHOTOS_DIR = os.path.join(BASE_DIR, "photos")

# Booth ranges:
# pooling booth 1 : 1 - 920
# pooling booth 2 : 921- 1801
# pooling booth 3 : 1802 - 2738
# pooling booth 4 : 2739 - 3628
# pooling booth 5 : 3629 - 4544
# pooling booth 6 : 4545 - 5462
# pooling booth 7 : 5463 - 6352
# pooling booth 8 : 6353 - 7347
BOOTH_RANGES = [
    (1, 920, 1),
    (921, 1801, 2),
    (1802, 2738, 3),
    (2739, 3628, 4),
    (3629, 4544, 5),
    (4545, 5462, 6),
    (5463, 6352, 7),
    (6353, 7347, 8),
]

def get_booth_num(ward_serial):
    try:
        ws = int(ward_serial)
        for lo, hi, b in BOOTH_RANGES:
            if lo <= ws <= hi:
                return b
    except (ValueError, TypeError):
        pass
    return None

def get_booth_label(ward_serial):
    b = get_booth_num(ward_serial)
    return f"Polling Booth {b}" if b else "Polling Booth —"

# Load voter data at startup
voters = []

# Direct Telugu to natural English phonetics
TELUGU_VOWELS = {
    'అ': 'a', 'ఆ': 'a', 'ఇ': 'i', 'ఈ': 'i', 'ఉ': 'u', 'ఊ': 'u',
    'ఋ': 'ri', 'ౠ': 'ri', 'ఌ': 'li', 'ౡ': 'li',
    'ఎ': 'e', 'ఏ': 'e', 'ఐ': 'ai', 'ఒ': 'o', 'ఓ': 'o', 'ఔ': 'au',
}
TELUGU_CONSONANTS = {
    'క': 'k', 'ఖ': 'k', 'గ': 'g', 'ఘ': 'g', 'ఙ': 'n',
    'చ': 'ch', 'ఛ': 'ch', 'జ': 'j', 'ఝ': 'j', 'ఞ': 'n',
    'ట': 't', 'ఠ': 't', 'డ': 'd', 'ఢ': 'd', 'ణ': 'n',
    'త': 't', 'థ': 't', 'ద': 'd', 'ధ': 'd', 'న': 'n',
    'ప': 'p', 'ఫ': 'f', 'బ': 'b', 'భ': 'b', 'మ': 'm',
    'య': 'y', 'ర': 'r', 'ల': 'l', 'వ': 'v', 'శ': 's',
    'ష': 's', 'స': 's', 'హ': 'h', 'ళ': 'l', 'క్ష': 'ksh', 'ఱ': 'r'
}
TELUGU_MATRAS = {
    'ా': 'a', 'ి': 'i', 'ీ': 'i', 'ు': 'u', 'ూ': 'u',
    'ృ': 'ri', 'ౄ': 'ri', 'ె': 'e', 'ే': 'e', 'ై': 'ai',
    'ొ': 'o', 'ో': 'o', 'ౌ': 'au'
}

def clean_telugu_name(text):
    if not text:
        return ""
    # Deduplicate consecutive matras (e.g. ోో -> ో, ీీ -> ీ, ేే -> ే, ాా -> ా, ుు -> ు, ూూ -> ూ)
    text = re.sub(r'([\u0c3e-\u0c4d])\1+', r'\1', text)
    
    # Merge detached single virama consonant with previous word:
    # e.g. "అఫ్రో జ్" -> "అఫ్రోజ్", "ఇమ్రా న్" -> "ఇమ్రాన్", "ఆఫ్రీ న్" -> "ఆఫ్రీన్"
    words = text.split()
    merged = []
    for w in words:
        if merged and re.fullmatch(r'[క-హ]్', w):
            merged[-1] = merged[-1] + w
        elif merged and w in ['సాద్', 'కాశ్', 'శాంత్', 'వీణ్', 'మోద్'] and merged[-1] == 'ప్ర':
            merged[-1] = merged[-1] + w
        else:
            merged.append(w)
    return ' '.join(merged)

def telugu_to_english(text):
    """Convert Telugu script into readable phonetic English."""
    text = clean_telugu_name(text)
    res = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c in TELUGU_VOWELS:
            res.append(TELUGU_VOWELS[c])
            i += 1
        elif c in TELUGU_CONSONANTS:
            cons = TELUGU_CONSONANTS[c]
            if i + 1 < n and text[i+1] == '్':
                res.append(cons)
                i += 2
            elif i + 1 < n and text[i+1] in TELUGU_MATRAS:
                res.append(cons + TELUGU_MATRAS[text[i+1]])
                i += 2
            elif i + 1 < n and text[i+1] == 'ం':
                if i + 2 >= n or text[i+2] == ' ':
                    res.append(cons + 'am')
                else:
                    res.append(cons + 'an')
                i += 2
            else:
                res.append(cons + 'a')
                i += 1
        elif c == 'ం':
            if i + 1 >= n or text[i+1] == ' ':
                res.append('m')
            else:
                res.append('n')
            i += 1
        elif c in TELUGU_MATRAS:
            res.append(TELUGU_MATRAS[c])
            i += 1
        else:
            res.append(c)
            i += 1
    return ''.join(res).strip()

def simplify_phonetic(text):
    """Normalize English/Romanized text for flexible phonetic matching."""
    s = str(text).lower()
    s = re.sub(r'\b(md|m\.d\.)\b', 'endi', s)
    s = re.sub(r'\b(mohd|mohammed|muhammad|mohammad)\b', 'mahamad', s)
    s = re.sub(r'\b(shaik|sheikh|shaikh|shek|sek)\b', 'sek', s)
    s = re.sub(r'\b(syed|sayyad|sayed|saiyad)\b', 'sayad', s)
    s = re.sub(r'\b(khaja|khaza|qaja|qaza)\b', 'kaja', s)
    s = re.sub(r'\b(basha|pasha|baasha)\b', 'basa', s)
    s = re.sub(r'\b(hussain|hussein|husein|hussin)\b', 'husein', s)
    s = re.sub(r'\b(ahmed|ahmad|ahamad)\b', 'ahmad', s)
    s = re.sub(r'\b(begum|beegum|begam)\b', 'begam', s)
    s = re.sub(r'\b(khan)\b', 'kan', s)
    s = re.sub(r'\b(raees|rayees|raiss|rayis|raiz|raij)\b', 'rayis', s)
    s = re.sub(r'\b(raisa|rayisa)\b', 'rayisa', s)

    s = s.replace('ayee', 'ai').replace('aye', 'ai').replace('ayi', 'ai').replace('aee', 'ai')
    s = s.replace('ee', 'i').replace('oo', 'u').replace('ou', 'u')
    s = s.replace('ay', 'ai').replace('ey', 'ai')

    s = s.replace('sh', 's')
    s = s.replace('khs', 'ksh').replace('x', 'ksh')
    s = s.replace('rahman', 'rahaman')
    s = s.replace('fahmida', 'fahamida')
    s = s.replace('ph', 'f').replace('w', 'v')
    
    # Map z -> j because Telugu uses 'జ' (j) for all 'z'
    s = s.replace('z', 'j')

    s = s.replace('th', 't').replace('dh', 'd').replace('bh', 'b').replace('gh', 'g').replace('kh', 'k')
    s = s.replace('ck', 'k').replace('q', 'k')
    s = s.replace('rao', 'ravu')
    s = re.sub(r'(.)\1+', r'\1', s)
    s = re.sub(r'[^a-z0-9 ]', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def get_skeleton(word):
    return re.sub(r'[aeiou]', '', word)

def word_match(qw, tw):
    # 1. Exact or prefix match of full word
    if qw == tw:
        return True
    if len(qw) >= 4 and tw.startswith(qw):
        return True
    if len(tw) >= 4 and qw.startswith(tw):
        return True
        
    qw_skel = get_skeleton(qw)
    tw_skel = get_skeleton(tw)
    
    if not qw_skel or not tw_skel:
        return False
        
    # 2. Exact consonant skeleton match
    if qw_skel == tw_skel:
        return True
        
    # 3. Handle p <-> f interchange (aproj <-> afroj)
    if qw_skel.replace('p', 'f') == tw_skel.replace('p', 'f'):
        return True

    # 4. Handle s <-> sh <-> ch <-> z <-> j
    qw_norm = qw_skel.replace('p', 'f').replace('z', 'j').replace('s', 'j')
    tw_norm = tw_skel.replace('p', 'f').replace('z', 'j').replace('s', 'j')
    if qw_norm == tw_norm:
        return True
        
    return False

def matches_query(query, text_eng_norm):
    q_norm = simplify_phonetic(query)
    q_words = [w for w in q_norm.split() if w]
    if not q_words or not text_eng_norm:
        return False
    if q_norm in text_eng_norm:
        return True
    target_words = text_eng_norm.split()
    for qw in q_words:
        if not any(word_match(qw, tw) for tw in target_words):
            return False
    return True

def load_data():
    global voters
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            voters = json.load(f)
        print(f"Loaded {len(voters)} voter records. Building English phonetic index & booth mapping...")
        for v in voters:
            v['clean_voter_name'] = clean_telugu_name(v.get('voter_name', ''))
            v['clean_relation_name'] = clean_telugu_name(v.get('relation_name', ''))
            v['eng_name'] = telugu_to_english(v.get('voter_name', ''))
            v['eng_relation'] = telugu_to_english(v.get('relation_name', ''))
            v['_v_eng'] = simplify_phonetic(v['eng_name'])
            v['_r_eng'] = simplify_phonetic(v['eng_relation'])
            v['booth_num'] = get_booth_num(v.get('ward_serial', ''))
            v['booth'] = get_booth_label(v.get('ward_serial', ''))
        print("Index ready with booth mapping.")
    else:
        print("WARNING: voter_data.json not found. Run extract_pdf.py first.")

def normalize(text):
    """Lowercase, strip, and unify - and / separators for comparison."""
    return str(text).lower().strip().replace('/', '-')

def search_voters(query, field_filter='all'):
    query = query.strip()
    if not query:
        return []

    query_lower = normalize(query)
    is_eng = any('a' <= c <= 'z' or 'A' <= c <= 'Z' for c in query)
    results = []

    exact_results = []
    partial_results = []

    for voter in voters:
        match = False
        matched_fields = []

        if field_filter == 'ward_serial':
            ws = normalize(voter.get('ward_serial', ''))
            if query_lower == ws:
                exact_results.append({**voter, 'matched_fields': ['ward_serial']})
            elif query_lower in ws:
                partial_results.append({**voter, 'matched_fields': ['ward_serial']})
            continue
        else:
            searchable = {
                'voter_name':          voter.get('voter_name', ''),
                'clean_voter_name':    voter.get('clean_voter_name', ''),
                'relation_name':       voter.get('relation_name', ''),
                'clean_relation_name': voter.get('clean_relation_name', ''),
                'voter_id':            voter.get('voter_id', ''),
                'house_number':        voter.get('house_number', ''),
                'age':                 voter.get('age', ''),
                'ward_serial':         voter.get('ward_serial', ''),
                'assembly_serial':     voter.get('assembly_serial', ''),
            }

            for field, value in searchable.items():
                if query_lower in normalize(value):
                    match = True
                    base_field = field.replace('clean_', '')
                    if base_field not in matched_fields:
                        matched_fields.append(base_field)

            # If English search term, check phonetic transliteration for names
            if is_eng:
                if 'voter_name' not in matched_fields and matches_query(query, voter.get('_v_eng', '')):
                    match = True
                    matched_fields.append('voter_name')
                if 'relation_name' not in matched_fields and matches_query(query, voter.get('_r_eng', '')):
                    match = True
                    matched_fields.append('relation_name')

        if match:
            result = dict(voter)
            result['matched_fields'] = matched_fields
            results.append(result)

    if field_filter == 'ward_serial':
        return exact_results if exact_results else partial_results

    return results


# ─────────────────────────────────────────────────────
#  HTML Template (Single-Page Application)
# ─────────────────────────────────────────────────────
HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🗳️ Voter Search — Ward 9, Kurnool</title>
<style>
  :root {
    --primary: #1a56db;
    --primary-dark: #1e40af;
    --accent: #f59e0b;
    --success: #10b981;
    --danger: #ef4444;
    --bg: #f1f5f9;
    --card: #ffffff;
    --text: #1e293b;
    --muted: #64748b;
    --border: #e2e8f0;
    --highlight: #fef3c7;
    --shadow: 0 4px 6px -1px rgba(0,0,0,.1), 0 2px 4px -1px rgba(0,0,0,.06);
    --radius: 12px;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Segoe UI', system-ui, sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
  }

  /* ── Header ── */
  .header {
    background: linear-gradient(135deg, #1a56db 0%, #0f3460 100%);
    color: white;
    padding: 24px 32px;
    display: flex;
    align-items: center;
    gap: 16px;
    box-shadow: var(--shadow);
  }
  .header-icon { font-size: 2.5rem; }
  .header-title { font-size: 1.5rem; font-weight: 700; letter-spacing: -.5px; }
  .header-sub { font-size: .9rem; opacity: .85; margin-top: 2px; }
  .header-badge {
    margin-left: auto;
    background: rgba(255,255,255,.2);
    padding: 6px 14px;
    border-radius: 20px;
    font-size: .85rem;
    font-weight: 600;
  }

  /* ── Search Panel ── */
  .search-panel {
    max-width: 960px;
    margin: 32px auto;
    padding: 0 16px;
  }
  .search-box {
    background: var(--card);
    border-radius: var(--radius);
    padding: 24px;
    box-shadow: var(--shadow);
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
  .search-row {
    display: flex;
    gap: 12px;
    align-items: center;
  }
  .search-input-wrap {
    flex: 1;
    position: relative;
  }
  .search-icon {
    position: absolute;
    left: 16px;
    top: 50%;
    transform: translateY(-50%);
    font-size: 1.2rem;
    color: var(--muted);
    pointer-events: none;
  }
  #searchInput {
    width: 100%;
    padding: 14px 16px 14px 48px;
    border: 2px solid var(--border);
    border-radius: 10px;
    font-size: 1rem;
    transition: border-color .2s;
    outline: none;
    color: var(--text);
  }
  #searchInput:focus { border-color: var(--primary); }
  #searchInput::placeholder { color: var(--muted); }

  .btn-search {
    padding: 14px 28px;
    background: var(--primary);
    color: white;
    border: none;
    border-radius: 10px;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: background .2s, transform .1s;
    white-space: nowrap;
  }
  .btn-search:hover { background: var(--primary-dark); }
  .btn-search:active { transform: scale(.97); }
  .btn-clear {
    padding: 14px 18px;
    background: transparent;
    border: 2px solid var(--border);
    border-radius: 10px;
    font-size: .95rem;
    cursor: pointer;
    color: var(--muted);
    transition: all .2s;
  }
  .btn-clear:hover { border-color: var(--danger); color: var(--danger); }

  .filter-row {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    align-items: center;
  }
  .filter-label { font-size: .85rem; color: var(--muted); font-weight: 500; }
  .filter-btn {
    padding: 6px 14px;
    border-radius: 20px;
    border: 2px solid var(--border);
    background: white;
    cursor: pointer;
    font-size: .82rem;
    font-weight: 500;
    transition: all .15s;
    color: var(--text);
  }
  .filter-btn:hover { border-color: var(--primary); color: var(--primary); }
  .filter-btn.active {
    background: var(--primary);
    color: white;
    border-color: var(--primary);
  }

  /* ── Results ── */
  .results-area { max-width: 960px; margin: 0 auto 40px; padding: 0 16px; }
  .results-meta {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
    font-size: .9rem;
    color: var(--muted);
  }
  .results-count { font-weight: 700; color: var(--primary); font-size: 1rem; }

  .cards-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(420px, 1fr));
    gap: 16px;
  }

  .voter-card {
    background: var(--card);
    border-radius: var(--radius);
    padding: 18px;
    box-shadow: var(--shadow);
    border-left: 5px solid var(--primary);
    transition: transform .15s, box-shadow .15s;
    animation: fadeIn .25s ease;
  }
  .voter-card:hover { transform: translateY(-2px); box-shadow: 0 10px 25px rgba(0,0,0,.12); }

  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
  }

  .card-header {
    display: flex;
    align-items: flex-start;
    gap: 14px;
    margin-bottom: 14px;
  }

  /* ── Photo Thumbnail Box ── */
  .voter-photo-box {
    width: 72px;
    height: 90px;
    border-radius: 8px;
    overflow: hidden;
    flex-shrink: 0;
    background: #e2e8f0;
    box-shadow: 0 2px 4px rgba(0,0,0,.08);
    border: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
  }
  .voter-photo-img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }

  .voter-avatar {
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.5rem;
    font-weight: 700;
  }
  .avatar-male   { background: #dbeafe; color: #1d4ed8; }
  .avatar-female { background: #fce7f3; color: #be185d; }
  .avatar-other  { background: #e0e7ff; color: #6366f1; }

  .voter-main-name {
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--text);
    line-height: 1.3;
  }
  .voter-id-badge {
    display: inline-block;
    background: #eff6ff;
    color: var(--primary);
    border-radius: 6px;
    padding: 3px 8px;
    font-size: .78rem;
    font-weight: 700;
    letter-spacing: .5px;
    border: 1px solid #bfdbfe;
  }

  .booth-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: #fef3c7;
    color: #92400e;
    font-size: .78rem;
    font-weight: 700;
    padding: 3px 9px;
    border-radius: 6px;
    border: 1px solid #fde68a;
  }

  .card-body { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 12px; }
  .info-item {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .info-label { font-size: .72rem; color: var(--muted); text-transform: uppercase; letter-spacing: .5px; font-weight: 600; }
  .info-value { font-size: .9rem; color: var(--text); font-weight: 500; }

  .card-footer {
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid var(--border);
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    align-items: center;
  }
  .tag {
    padding: 3px 10px;
    border-radius: 20px;
    font-size: .73rem;
    font-weight: 600;
  }
  .tag-booth { background: #fef3c7; color: #92400e; border: 1px solid #fde68a; }
  .tag-ward { background: #dcfce7; color: #15803d; }
  .tag-assembly { background: #f3e8ff; color: #7e22ce; }
  .tag-matched { background: #f0fdf4; color: #166534; border: 1px solid #bbf7d0; }

  mark {
    background: var(--highlight);
    color: inherit;
    border-radius: 3px;
    padding: 0 2px;
  }

  /* ── Loading / Empty states ── */
  .state-box {
    text-align: center;
    padding: 60px 20px;
    color: var(--muted);
  }
  .state-icon { font-size: 4rem; margin-bottom: 16px; }
  .state-title { font-size: 1.2rem; font-weight: 600; margin-bottom: 8px; color: var(--text); }
  .state-sub { font-size: .9rem; }

  .spinner {
    display: inline-block;
    width: 36px;
    height: 36px;
    border: 4px solid var(--border);
    border-top-color: var(--primary);
    border-radius: 50%;
    animation: spin .7s linear infinite;
    margin-bottom: 16px;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* ── Status bar ── */
  .status-bar {
    background: var(--card);
    border-top: 1px solid var(--border);
    padding: 8px 32px;
    font-size: .8rem;
    color: var(--muted);
    display: flex;
    gap: 16px;
  }
  .status-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: var(--success); margin-right: 6px; }

  @media (max-width: 600px) {
    .search-row { flex-direction: column; }
    .btn-search { width: 100%; }
    .cards-grid { grid-template-columns: 1fr; }
    .card-body { grid-template-columns: 1fr; }
    .header { flex-wrap: wrap; }
  }
</style>
</head>
<body>

<div class="header">
  <div class="header-icon">🗳️</div>
  <div>
    <div class="header-title">Voter Search — Kurnool Municipal Corporation</div>
    <div class="header-sub">Ward No. 9 · Photo Electoral Roll · Polling Booths 1 to 8 · Assembly: 137-Kurnool / 138-Panyam</div>
  </div>
  <div class="header-badge" id="totalBadge">Loading…</div>
</div>

<div class="search-panel">
  <div class="search-box">
    <div class="search-row">
      <div class="search-input-wrap">
        <span class="search-icon">🔍</span>
        <input type="text" id="searchInput"
               placeholder="Search by name, voter ID, house number, ward serial, age…"
               autocomplete="off" spellcheck="false">
      </div>
      <button class="btn-search" onclick="doSearch()">Search</button>
      <button class="btn-clear" onclick="clearSearch()" title="Clear">✕</button>
    </div>

    <div class="filter-row">
      <span class="filter-label">Filter by:</span>
      <button class="filter-btn active" data-field="all" onclick="setFilter(this)">All Fields</button>
      <button class="filter-btn" data-field="ward_serial" onclick="setFilter(this)">Ward Serial Number</button>
    </div>
  </div>
</div>

<div class="results-area">
  <div id="resultsContainer">
    <div class="state-box">
      <div class="state-icon">🔍</div>
      <div class="state-title">Search the Voter List</div>
      <div class="state-sub">Type a name, voter ID, house number or ward serial above and click Search.</div>
    </div>
  </div>
</div>

<div class="status-bar">
  <span><span class="status-dot"></span>Server Running</span>
  <span id="statusInfo">Ready</span>
</div>

<script>
let currentField = 'all';
let totalVoters = 0;
let lastQuery = '';

// ── Fetch total count on load ──
fetch('/api/count')
  .then(r => r.json())
  .then(d => {
    totalVoters = d.count;
    document.getElementById('totalBadge').textContent = `${totalVoters.toLocaleString()} Voters`;
    document.getElementById('statusInfo').textContent = `${totalVoters.toLocaleString()} voter records loaded`;
  });

// ── Filter buttons ──
function setFilter(btn) {
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  currentField = btn.dataset.field;
  if (lastQuery) doSearch();
}

// ── Search ──
function doSearch() {
  const query = document.getElementById('searchInput').value.trim();
  if (!query) { clearSearch(); return; }
  lastQuery = query;

  const container = document.getElementById('resultsContainer');
  container.innerHTML = '<div class="state-box"><div class="spinner"></div><div class="state-title">Searching…</div></div>';

  fetch(`/api/search?q=${encodeURIComponent(query)}&field=${currentField}`)
    .then(r => r.json())
    .then(data => renderResults(data, query))
    .catch(() => {
      container.innerHTML = '<div class="state-box"><div class="state-icon">⚠️</div><div class="state-title">Error</div><div class="state-sub">Could not connect to server.</div></div>';
    });
}

function clearSearch() {
  document.getElementById('searchInput').value = '';
  lastQuery = '';
  document.getElementById('resultsContainer').innerHTML = `
    <div class="state-box">
      <div class="state-icon">🔍</div>
      <div class="state-title">Search the Voter List</div>
      <div class="state-sub">Type a name, voter ID, house number or ward serial above and click Search.</div>
    </div>`;
}

// ── Render results ──
function renderResults(results, query) {
  const container = document.getElementById('resultsContainer');
  if (!results.length) {
    container.innerHTML = `
      <div class="state-box">
        <div class="state-icon">😔</div>
        <div class="state-title">No Results Found</div>
        <div class="state-sub">No voters matched "<strong>${esc(query)}</strong>". Try a different search term.</div>
      </div>`;
    return;
  }

  const genderClass = g => {
    if (!g) return 'avatar-other';
    const gl = g.toLowerCase();
    if (gl.includes('పు') || gl.includes('male') || gl === 'm') return 'avatar-male';
    if (gl.includes('స్') || gl.includes('female') || gl === 'f') return 'avatar-female';
    return 'avatar-other';
  };
  const genderLabel = g => {
    if (!g) return '—';
    const gl = g.toLowerCase();
    if (gl.includes('పు')) return 'Male';
    if (gl.includes('స్')) return 'Female';
    return g;
  };

  const fieldLabels = {
    voter_name: 'Name',
    relation_name: 'Father/Husband',
    voter_id: 'Voter ID',
    house_number: 'House No.',
    age: 'Age',
    ward_serial: 'Ward Serial',
    assembly_serial: 'Assembly Serial',
  };

  const highlight = (text, q) => {
    if (!text || !q) return esc(text || '—');
    const regex = new RegExp(`(${escReg(q)})`, 'gi');
    return esc(text).replace(regex, '<mark>$1</mark>');
  };

  const cards = results.map(v => {
    const initials = (v.voter_name || '?').charAt(0).toUpperCase();
    const matchedTags = (v.matched_fields || []).map(f =>
      `<span class="tag tag-matched">✓ ${fieldLabels[f] || f}</span>`
    ).join('');

    const boothLabel = v.booth || (v.booth_num ? `Polling Booth ${v.booth_num}` : 'Polling Booth —');
    const wardSerialStr = String(v.ward_serial || '').trim();

    return `
    <div class="voter-card">
      <div class="card-header">
        <div class="voter-photo-box">
          <img src="/api/photo/${esc(wardSerialStr)}"
               alt="Voter Photo"
               class="voter-photo-img"
               loading="lazy"
               onerror="this.style.display='none';this.nextElementSibling.style.display='flex';">
          <div class="voter-avatar ${genderClass(v.gender)}" style="display:none;">${initials}</div>
        </div>
        <div style="flex:1;min-width:0;">
          <div class="voter-main-name">${highlight(v.voter_name, query)}</div>
          ${v.eng_name ? `<div style="font-size:0.82rem;color:var(--muted);text-transform:capitalize;margin-top:1px;">${highlight(v.eng_name, query)}</div>` : ''}
          <div style="display:flex;gap:6px;align-items:center;margin-top:6px;flex-wrap:wrap;">
            <span class="voter-id-badge">${esc(v.voter_id || '—')}</span>
            <span class="booth-badge">🏛️ ${esc(boothLabel)}</span>
          </div>
        </div>
      </div>
      <div class="card-body">
        <div class="info-item">
          <span class="info-label">Father / Husband</span>
          <span class="info-value">${highlight(v.relation_name, query)}${v.eng_relation ? `<div style="font-size:0.75rem;color:var(--muted);text-transform:capitalize;">(${highlight(v.eng_relation, query)})</div>` : ''}</span>
        </div>
        <div class="info-item">
          <span class="info-label">House Number</span>
          <span class="info-value">${highlight(v.house_number, query)}</span>
        </div>
        <div class="info-item">
          <span class="info-label">Age</span>
          <span class="info-value">${esc(v.age || '—')}</span>
        </div>
        <div class="info-item">
          <span class="info-label">Gender</span>
          <span class="info-value">${genderLabel(v.gender)}</span>
        </div>
      </div>
      <div class="card-footer">
        <span class="tag tag-booth">🏛️ ${esc(boothLabel)}</span>
        <span class="tag tag-ward">Ward Serial: ${esc(v.ward_serial || '—')}</span>
        <span class="tag tag-assembly">Asm: ${esc(v.assembly_serial || '—')}</span>
        ${matchedTags}
      </div>
    </div>`;
  }).join('');

  container.innerHTML = `
    <div class="results-meta">
      <span>Showing <span class="results-count">${results.length.toLocaleString()}</span> result${results.length !== 1 ? 's' : ''} for "<strong>${esc(query)}</strong>"</span>
      <span style="color:var(--muted)">of ${totalVoters.toLocaleString()} total voters</span>
    </div>
    <div class="cards-grid">${cards}</div>`;

  document.getElementById('statusInfo').textContent = `${results.length} results for "${query}"`;
}

// ── Utilities ──
function esc(s) {
  return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function escReg(s) {
  return String(s).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// ── Enter key support ──
document.getElementById('searchInput').addEventListener('keydown', e => {
  if (e.key === 'Enter') doSearch();
});

</script>
</body>
</html>
"""

# Initialize voter data at module level for WSGI servers
load_data()

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/api/count')
def count():
    return jsonify({'count': len(voters)})

@app.route('/api/photo/<serial>')
def get_photo(serial):
    safe_serial = re.sub(r'[^0-9]', '', str(serial))
    photo_path = os.path.join(PHOTOS_DIR, f"{safe_serial}.jpg")
    if os.path.exists(photo_path):
        return send_file(photo_path, mimetype='image/jpeg', max_age=86400)
    return ('', 404)

@app.route('/api/search')
def search():
    query = request.args.get('q', '').strip()
    field = request.args.get('field', 'all')
    if not query:
        return jsonify([])
    results = search_voters(query, field)
    return jsonify(results)

if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    load_data()
    print("\n[APP] Voter Search App running at: http://localhost:5000\n")
    app.run(host='0.0.0.0', port=5000, debug=False)
