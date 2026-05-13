#!/usr/bin/env bash
# paper_analyze.sh — Extract structured information from an academic paper PDF
# Usage: ./paper_analyze.sh <pdf-file> [--arxiv-url <url>]
# Output: JSON to stdout

set -o pipefail

PDF_FILE=""
ARXIV_URL=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --arxiv-url) ARXIV_URL="$2"; shift 2 ;;
    *) PDF_FILE="$1"; shift ;;
  esac
done

# ── Handle arXiv URL ──
if [ -n "$ARXIV_URL" ] && [ -z "$PDF_FILE" ]; then
  # Convert arXiv URL to PDF URL if needed
  # e.g., https://arxiv.org/abs/2501.12345 → https://arxiv.org/pdf/2501.12345.pdf
  ARXIV_PDF_URL=$(echo "$ARXIV_URL" | sed 's|/abs/|/pdf/|' | sed 's|$|.pdf|')
  PDF_FILE="/tmp/arxiv_paper_$$.pdf"

  if command -v curl &>/dev/null; then
    curl -sL -o "$PDF_FILE" "$ARXIV_PDF_URL" 2>/dev/null
  elif command -v wget &>/dev/null; then
    wget -q -O "$PDF_FILE" "$ARXIV_PDF_URL" 2>/dev/null
  else
    cat <<'EOF'
{"status":"error","error":"Neither curl nor wget is available. Cannot download arXiv PDF."}
EOF
    exit 1
  fi

  if [ ! -s "$PDF_FILE" ]; then
    cat <<'EOF'
{"status":"error","error":"Failed to download PDF from arXiv. Check the URL and try again."}
EOF
    rm -f "$PDF_FILE"
    exit 1
  fi
fi

if [ -z "$PDF_FILE" ] || [ ! -f "$PDF_FILE" ]; then
  cat <<'EOF'
{"status":"error","error":"No PDF file provided. Usage: paper_analyze.sh <pdf-file> [--arxiv-url <url>]"}
EOF
  exit 1
fi

# ── Check Python + pdfplumber ──
PYTHON=""
for py in python3 python; do
  if command -v "$py" &>/dev/null; then
    PYTHON="$py"
    break
  fi
done

if [ -z "$PYTHON" ]; then
  cat <<'EOF'
{"status":"error","error":"Python 3 is not installed. Install Python 3 to use paper analysis: https://python.org"}
EOF
  exit 1
fi

# Check for pdfplumber
$PYTHON -c "import pdfplumber" 2>/dev/null
HAS_PDFPLUMBER=$?

if [ $HAS_PDFPLUMBER -ne 0 ]; then
  cat <<'EOF'
{"status":"error","error":"pdfplumber is not installed. Install it with: pip install pdfplumber"}
EOF
  exit 1
fi

# ── Python Extraction Script ──
export PDF_FILE
$PYTHON << 'PYEOF'
import json
import re
import sys
import os

pdf_path = os.environ.get("PDF_FILE", sys.argv[1] if len(sys.argv) > 1 else "")

try:
    import pdfplumber
except ImportError:
    print(json.dumps({"status": "error", "error": "pdfplumber not installed. Run: pip install pdfplumber"}))
    sys.exit(1)

try:
    pdf = pdfplumber.open(pdf_path)
except Exception as e:
    print(json.dumps({"status": "error", "error": f"Cannot open PDF: {str(e)}"}))
    sys.exit(1)

# ── Extract Full Text ──
all_text = ""
all_pages = []
for i, page in enumerate(pdf.pages):
    text = page.extract_text()
    if text:
        all_text += text + "\n"
        all_pages.append({"page": i + 1, "text": text})
pdf.close()

if not all_text.strip():
    print(json.dumps({"status": "error", "error": "No extractable text found in PDF. It may be a scanned document (image-only)."}))
    sys.exit(1)

# ── Extract Metadata ──
metadata = {
    "title": "",
    "authors": [],
    "year": None,
    "arxiv_id": None
}

# Try to get title from first non-empty line
lines = [l.strip() for l in all_text.split('\n') if l.strip()]
if lines:
    # First substantial line is often the title
    for line in lines[:20]:
        if len(line) > 20 and not line.startswith('arXiv') and not line.lower().startswith('copyright'):
            metadata["title"] = line[:200]
            break

# Look for arXiv ID
arxiv_match = re.search(r'arXiv:(\d{4}\.\d{4,5})', all_text)
if arxiv_match:
    metadata["arxiv_id"] = arxiv_match.group(1)

# Look for year in first 500 chars
year_match = re.search(r'(20\d{2})', all_text[:500])
if year_match:
    metadata["year"] = int(year_match.group(1))

# ── Extract Abstract ──
abstract = ""
abstract_patterns = [
    r'(?i)abstract[\.\s—–-]*(.+?)(?=\n\s*\d+[\.\s]+(?:Introduction|Background|Related))',
    r'(?i)abstract[\.\s—–-]*(.+?)(?=\n\s*(?:1|I)[\.\s]+)',
]
for pattern in abstract_patterns:
    match = re.search(pattern, all_text, re.DOTALL)
    if match:
        abstract = match.group(1).strip()[:2000]
        break

# ── Extract Section Structure ──
sections = []
section_pattern = re.compile(
    r'(?:^|\n)\s*((?:\d+\.?\s*)+)([A-Z][A-Za-z\s\-]+)\s*\n',
    re.MULTILINE
)

for match in section_pattern.finditer(all_text):
    sec_num = match.group(1).strip()
    sec_title = match.group(2).strip()
    if len(sec_title) < 100 and sec_title.lower() not in ('abstract', 'references', 'acknowledgments', 'acknowledgements'):
        # Find where this section ends (next section or end of text)
        start = match.end()
        next_sec = section_pattern.search(all_text, start)
        end = next_sec.start() if next_sec else min(start + 3000, len(all_text))
        summary = all_text[start:end].strip()[:500]

        sections.append({
            "number": sec_num,
            "title": sec_title,
            "summary": summary
        })

# Limit to top 12 sections
sections = sections[:12]

# ── Extract Formulas ──
formulas = []
# LaTeX-style equations
eq_patterns = [
    r'\$\$([^$]+)\$\$',
    r'\\begin\{equation\}(.+?)\\end\{equation\}',
    r'\\\[(.+?)\\\]',
]
for pattern in eq_patterns:
    for match in re.finditer(pattern, all_text, re.DOTALL):
        latex = match.group(1).strip()[:200]
        # Find equation number nearby (within 100 chars before)
        before = all_text[max(0, match.start()-100):match.start()]
        num_match = re.search(r'\((\d+)\)', before)
        eq_num = num_match.group(1) if num_match else "?"
        formulas.append({
            "number": eq_num,
            "latex": latex,
            "description": "",
            "section_ref": ""
        })

# Deduplicate and limit
seen = set()
unique_formulas = []
for f in formulas:
    key = f["latex"][:50]
    if key not in seen:
        seen.add(key)
        unique_formulas.append(f)
formulas = unique_formulas[:15]

# ── Extract Claims / Innovations ──
innovations = []
# Look for contribution statements
contrib_match = re.search(
    r'(?i)(?:Our\s+(?:main\s+)?contributions?\s*(?:are|include|is|can be summarized))[:\s]*(.+?)(?=\n\s*(?:\d+[\.\s]|The\s+rest|We\s+(?:also|further|demonstrate|evaluate|organize|structure)))',
    all_text, re.DOTALL
)
if contrib_match:
    contrib_text = contrib_match.group(1)
    # Split into bullet points
    bullets = re.split(r'(?:•|\(?\d+\)|[-–—])\s*', contrib_text)
    for bullet in bullets:
        bullet = bullet.strip()
        if len(bullet) > 10:
            innovations.append({
                "claim": bullet[:500],
                "section_ref": "",
                "formula_ref": None
            })

# If no explicit contribution list, extract from abstract sentences
if not innovations and abstract:
    sentences = re.split(r'(?<=[.!?])\s+', abstract)
    for sent in sentences[:5]:
        sent_clean = sent.strip()
        if len(sent_clean) > 30:
            innovations.append({
                "claim": sent_clean[:500],
                "section_ref": "",
                "formula_ref": None
            })

innovations = innovations[:8]

# ── Extract Experiment Configurations ──
experiments = []
exp_section_match = re.search(
    r'(?i)(?:Experiments?|Experimental\s+(?:Setup|Results|Evaluation))\s*\n(.+?)(?=\n\s*(?:\d+[\.\s]+(?:Conclusion|Results|Discussion|Related|Future|Limitation)))',
    all_text, re.DOTALL
)
exp_text = ""
if exp_section_match:
    exp_text = exp_section_match.group(1)[:3000]

# Look for dataset names
dataset_matches = re.findall(r'(?:dataset|corpus|benchmark)[:\s]+([A-Za-z0-9\-]+)', exp_text, re.IGNORECASE)
for ds in dataset_matches[:3]:
    experiments.append({
        "name": f"Experiment on {ds}",
        "dataset": ds,
        "metrics": [],
        "config": {}
    })

# Look for metrics
metric_matches = re.findall(
    r'(?:accuracy|BLEU|ROUGE|F\d|precision|recall|perplexity|AUC|MSE|MAE|top-\d)',
    exp_text, re.IGNORECASE
)
if metric_matches and experiments:
    experiments[0]["metrics"] = list(set(m.lower() for m in metric_matches))[:5]

experiments = experiments[:3]

# ── Assemble Output ──
output = {
    "status": "success",
    "source": "pdf",
    "pages_analyzed": len(all_pages),
    "metadata": {
        "title": metadata["title"],
        "authors": metadata["authors"],
        "year": metadata["year"],
        "arxiv_id": metadata["arxiv_id"]
    },
    "abstract": abstract,
    "sections": sections,
    "innovations": innovations,
    "formulas": formulas,
    "experiments": experiments
}

print(json.dumps(output, ensure_ascii=False, indent=2))

PYEOF

# Clean up temp file if we downloaded it
if [ -n "$ARXIV_URL" ]; then
  rm -f "/tmp/arxiv_paper_$$.pdf"
fi
