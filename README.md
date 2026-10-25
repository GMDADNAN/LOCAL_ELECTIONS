# 🗳️ Kurnool Ward 9 - Photo Electoral Roll Search Application

A web application designed for fast, accurate searching across electoral rolls for Kurnool Municipal Corporation (Ward No. 9).

## ✨ Features
- **Phonetic Search Engine**: Search Telugu voter and relation names using natural English (e.g. `Afroz` matches `అఫ్రోజ్`, `Shaik` matches `షేక్`, `Mohammed` matches `మహమ్మద్`).
- **Polling Booth Mapping**: Automatic booth assignment based on Ward Serial ranges:
  - Polling Booth 1: 1 – 920
  - Polling Booth 2: 921 – 1801
  - Polling Booth 3: 1802 – 2738
  - Polling Booth 4: 2739 – 3628
  - Polling Booth 5: 3629 – 4544
  - Polling Booth 6: 4545 – 5462
  - Polling Booth 7: 5463 – 6352
  - Polling Booth 8: 6353 – 7347
- **Voter Photos**: Integrated voter photographs displayed next to each record with fallback avatar.
- **House Number Normalization**: Seamlessly matches house numbers regardless of `/` or `-` separators (e.g. `32-192-K-14` matches `32/192-K-14`).
- **Flexible Filters**: Filter by "All Fields" or exact "Ward Serial Number".
- **Responsive Single-Page UI**: Modern interface with instant card rendering, badges, and status counters.

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- `pip install -r requirements.txt`

### Running Locally
Double-click `START_APP.bat` or run:
```bash
python app.py
```
Then open [http://localhost:5000](http://localhost:5000) in your browser.

## 📂 Project Structure
- `app.py` - Flask backend with phonetic index, REST APIs, and inline SPA frontend.
- `extract_pdf.py` - Script to extract voter records from electoral roll PDF.
- `voter_data.json` - Processed JSON dataset of voters (names, relation, age, gender, house no, voter ID, serials).
- `photos/` - Extracted voter photos named by ward serial number (`{ward_serial}.jpg`).
- `START_APP.bat` - One-click launcher for Windows.
