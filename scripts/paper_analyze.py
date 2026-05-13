#!/usr/bin/env python3
# paper_analyze.py — Parse an academic paper PDF or arXiv listing and extract structured data
# Usage: python paper_analyze.py <pdf-file>
#        python paper_analyze.py --arxiv-url <url>
#        python paper_analyze.py --arxiv-id <id>
# Output: JSON to stdout
#
# Cross-platform Python port of paper_analyze.sh.
# Requires: pdfplumber (pip install pdfplumber) for PDF parsing.
# Falls back to arXiv API metadata-only mode when pdfplumber is not available.

import sys
import os
import json
import re
import argparse
import urllib.request
import urllib.error
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description='Analyze an academic paper')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('pdf_file', nargs='?', help='Path to a PDF file')
    group.add_argument('--arxiv-url', help='arXiv URL (e.g. https://arxiv.org/abs/1706.03762)')
    group.add_argument('--arxiv-id', help='arXiv ID (e.g. 1706.03762)')
    return parser.parse_args()


def has_pdfplumber():
    try:
        __import__('pdfplumber')
        return True
    except ImportError:
        return False


def extract_arxiv_id(url_or_id):
    # Match patterns like: 1706.03762, arxiv.org/abs/1706.03762, arxiv.org/pdf/1706.03762.pdf
    m = re.search(r'(\d{4}\.\d{4,5})(?:\.pdf)?', url_or_id)
    if m:
        return m.group(1)
    # New format: arxiv.org/abs/2106.xxxxx
    m = re.search(r'(\d{4}\.\d{4,5})', url_or_id)
    if m:
        return m.group(1)
    return None


def fetch_arxiv_metadata(arxiv_id):
    """Fetch paper metadata from arXiv API (no PDF download needed)."""
    url = f'http://export.arxiv.org/api/query?id_list={arxiv_id}&max_results=1'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'project-mentor/2.0'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            xml_data = resp.read().decode('utf-8')
    except urllib.error.URLError as e:
        return {'status': 'error', 'error': f'Failed to fetch arXiv metadata: {e}'}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}

    # Parse arXiv Atom XML
    ns = {
        'atom': 'http://www.w3.org/2005/Atom',
        'arxiv': 'http://arxiv.org/schemas/atom',
    }
    try:
        root = ET.fromstring(xml_data)
        entry = root.find('atom:entry', ns)
        if entry is None:
            return {'status': 'error', 'error': 'No entry found in arXiv response'}

        title = entry.find('atom:title', ns)
        title_text = title.text.strip() if title is not None else ''

        summary = entry.find('atom:summary', ns)
        abstract = summary.text.strip() if summary is not None else ''

        published = entry.find('atom:published', ns)
        year = published.text[:4] if published is not None else ''

        authors = []
        for author in entry.findall('atom:author', ns):
            name = author.find('atom:name', ns)
            if name is not None:
                authors.append(name.text)

        # ArXiv categories
        categories = []
        for cat in entry.findall('atom:category', ns):
            term = cat.get('term', '')
            if term:
                categories.append(term)

        pdf_link = ''
        for link in entry.findall('atom:link', ns):
            if link.get('title') == 'pdf':
                pdf_link = link.get('href', '')
                break

        return {
            'status': 'success',
            'source': 'arxiv_api',
            'metadata': {
                'title': title_text,
                'authors': authors,
                'year': year,
                'arxiv_id': arxiv_id,
                'categories': categories,
            },
            'abstract': abstract,
            'pdf_url': pdf_link,
            'sections': [],
            'innovations': [],
            'formulas': [],
            'experiments': [],
        }
    except ET.ParseError as e:
        return {'status': 'error', 'error': f'Failed to parse arXiv response: {e}'}


def extract_formulas(text):
    """Extract LaTeX formulas from paper text."""
    formulas = []
    # Display math: $$...$$ or \[...\]
    for i, m in enumerate(re.finditer(r'\$\$(.+?)\$\$|\\\[(.+?)\\\]', text, re.DOTALL)):
        latex = m.group(1) or m.group(2)
        formulas.append({
            'number': str(i + 1),
            'latex': latex.strip()[:200],
            'description': '',
            'section_ref': '',
        })
    return formulas


def extract_sections(text):
    """Heuristic section extraction from paper text."""
    sections = []
    section_pattern = re.compile(
        r'(?:^|\n)\s*(?:(\d+(?:\.\d+)*)\s+)?([A-Z][A-Za-z\s\-]+)\s*\n',
        re.MULTILINE,
    )
    for m in section_pattern.finditer(text):
        num = m.group(1) or ''
        title = m.group(2).strip()
        if len(title.split()) <= 8 and not title.startswith('Figure') and not title.startswith('Table'):
            sections.append({'number': num, 'title': title, 'summary': ''})
    return sections[:20]


def extract_innovations(text):
    """Extract innovation claims from abstract and introduction."""
    innovations = []
    # Look for contribution-like sentences
    contrib_patterns = [
        r'(?:propose|introduce|present|develop|novel|new)\s+(?:a\s+)?[\w\-\s]+(?:method|approach|framework|architecture|model|technique|mechanism|system)',
        r'(?:contribution|key\s+innovation|main\s+idea).*?(?:is|are|:)\s*(.+?)(?:\.|$)',
        r'(?:we)\s+(?:propose|introduce|present|develop)\s+(.+?)(?:\.|;|$)',
    ]
    for pattern in contrib_patterns:
        for m in re.finditer(pattern, text[:5000], re.IGNORECASE):
            claim = m.group(0).strip()
            if len(claim) > 15:
                innovations.append({
                    'claim': claim[:200],
                    'section_ref': '',
                    'formula_ref': None,
                })
    return innovations[:8]


def extract_experiments(text):
    """Extract experiment/dataset references from paper text."""
    experiments = []
    # Look for dataset names and experiment sections
    dataset_pattern = re.compile(
        r'(?:dataset|benchmark|evaluat|experiment).*?(?:on|using|with)\s+([\w\-]+)',
        re.IGNORECASE,
    )
    for m in dataset_pattern.finditer(text[:10000]):
        name = m.group(1).strip()
        if name.lower() not in ('the', 'a', 'our', 'this', 'several', 'both', 'two', 'three'):
            experiments.append({
                'name': name,
                'dataset': '',
                'metrics': [],
                'config_location': '',
                'confidence': 'speculative',
            })
    return experiments[:8]


def parse_pdf_with_pdfplumber(pdf_path):
    """Parse PDF using pdfplumber (requires pip install pdfplumber)."""
    if not has_pdfplumber():
        return {'status': 'error', 'error': 'pdfplumber not installed. Run: pip install pdfplumber'}

    import pdfplumber

    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = ''
            pages_analyzed = min(len(pdf.pages), 20)
            for page in pdf.pages[:pages_analyzed]:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + '\n'
    except Exception as e:
        return {'status': 'error', 'error': f'Failed to parse PDF: {e}'}

    if not text.strip():
        return {'status': 'error', 'error': 'PDF appears to be scanned (no text layer found).'}

    # Try to find title (first substantial line)
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    title = lines[0] if len(lines) > 0 and len(lines[0]) > 10 else ''

    sections = extract_sections(text)
    formulas = extract_formulas(text)
    innovations = extract_innovations(text)
    experiments = extract_experiments(text)

    return {
        'status': 'success',
        'source': 'pdf',
        'pages_analyzed': pages_analyzed,
        'metadata': {
            'title': title[:200],
            'authors': [],
            'year': '',
            'arxiv_id': '',
        },
        'abstract': text[:2000],
        'sections': sections,
        'innovations': innovations,
        'formulas': formulas,
        'experiments': experiments,
    }


def download_arxiv_pdf(arxiv_id):
    """Download PDF from arXiv. Returns path to temp file or None."""
    pdf_url = f'https://arxiv.org/pdf/{arxiv_id}.pdf'
    try:
        req = urllib.request.Request(pdf_url, headers={'User-Agent': 'project-mentor/2.0'})
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = resp.read()
        tmp = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
        tmp.write(data)
        tmp.close()
        return tmp.name
    except Exception:
        return None


def main():
    args = parse_args()

    # Determine arxiv ID
    arxiv_id = None
    if args.arxiv_url:
        arxiv_id = extract_arxiv_id(args.arxiv_url)
    elif args.arxiv_id:
        arxiv_id = extract_arxiv_id(args.arxiv_id)

    # Case 1: ArXiv URL/ID provided
    if arxiv_id:
        # First get metadata from arXiv API (no PDF needed)
        result = fetch_arxiv_metadata(arxiv_id)
        if result.get('status') == 'error':
            print(json.dumps(result, ensure_ascii=False))
            sys.exit(1)

        # Try PDF download + parse for full extraction
        if has_pdfplumber():
            pdf_path = download_arxiv_pdf(arxiv_id)
            if pdf_path:
                pdf_result = parse_pdf_with_pdfplumber(pdf_path)
                os.unlink(pdf_path)
                if pdf_result.get('status') == 'success':
                    result['sections'] = pdf_result.get('sections', [])
                    result['innovations'] = pdf_result.get('innovations', [])
                    result['formulas'] = pdf_result.get('formulas', [])
                    result['experiments'] = pdf_result.get('experiments', [])
                    result['source'] = 'arxiv_pdf'
                    result['pages_analyzed'] = pdf_result.get('pages_analyzed', 0)
        else:
            result['note'] = 'pdfplumber not installed — metadata only. Run: pip install pdfplumber for full text extraction.'

        print(json.dumps(result, ensure_ascii=False))
        return

    # Case 2: Local PDF file
    if args.pdf_file:
        if not os.path.isfile(args.pdf_file):
            print(json.dumps({'status': 'error', 'error': f'File not found: {args.pdf_file}'}, ensure_ascii=False))
            sys.exit(1)
        result = parse_pdf_with_pdfplumber(args.pdf_file)
        print(json.dumps(result, ensure_ascii=False))
        return

    # No input
    print(json.dumps({
        'status': 'error',
        'error': 'No input provided. Usage: paper_analyze.py <pdf-file> | --arxiv-url <url> | --arxiv-id <id>',
    }, ensure_ascii=False))
    sys.exit(1)


if __name__ == '__main__':
    main()
