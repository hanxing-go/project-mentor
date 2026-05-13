#!/usr/bin/env python3
# ast_skeleton.py — Extract code skeleton from a codebase (imports, signatures, exports only)
# Usage: python ast_skeleton.py <project-path> [--extensions go,py,ts] [--skip-tests] [--max-file-lines 5000]
# Output: JSON to stdout
#
# Cross-platform Python port of ast_skeleton.sh.
# Uses stdlib only — no tree-sitter dependency (regex extraction always used).

import sys
import os
import json
import re
import argparse
from pathlib import Path


EXCLUDE_DIRS = {
    'node_modules', 'vendor', '.git', 'venv', '.venv',
    'target', '__pycache__', 'dist', 'build', '.next',
    '.nuxt', '.cache', 'coverage',
}

TEST_DIR_PATTERNS = {'test', 'tests', '__tests__', 'spec'}
TEST_FILE_SUFFIXES = {'.test.go', '_test.go', 'test.py', '_test.py',
                       'test.rs', '.test.ts', '.spec.ts', '.spec.tsx',
                       '.test.js', '.test.jsx', '.spec.js', '.spec.jsx'}

DEFAULT_EXTENSIONS = {'go', 'py', 'rs', 'ts', 'tsx', 'js', 'jsx', 'mjs',
                      'java', 'rb', 'swift', 'kt', 'c', 'cpp', 'h', 'hpp'}

EXT_TO_LANG = {
    'go': 'Go', 'py': 'Python', 'rs': 'Rust',
    'ts': 'TypeScript', 'tsx': 'TypeScript',
    'js': 'JavaScript', 'jsx': 'JavaScript', 'mjs': 'JavaScript',
    'java': 'Java', 'rb': 'Ruby', 'swift': 'Swift', 'kt': 'Kotlin',
    'c': 'C/C++', 'cpp': 'C/C++', 'h': 'C/C++', 'hpp': 'C/C++',
}


def parse_args():
    parser = argparse.ArgumentParser(description='Extract AST skeleton from a codebase')
    parser.add_argument('project_path', help='Path to project directory')
    parser.add_argument('--extensions', help='Comma-separated list of extensions (e.g. go,py,ts)')
    parser.add_argument('--skip-tests', action='store_true', default=True)
    parser.add_argument('--no-skip-tests', action='store_true', default=False)
    parser.add_argument('--max-file-lines', type=int, default=5000)
    return parser.parse_args()


def is_test_file(rel_path):
    parts = set(Path(rel_path).parts)
    if parts & TEST_DIR_PATTERNS:
        return True
    name = os.path.basename(rel_path).lower()
    if any(name.endswith(suf.lstrip('*').lstrip('.')) for suf in TEST_FILE_SUFFIXES):
        return True
    if 'test' in name or 'spec' in name:
        return True
    return False


def discover_files(project_path, extensions, skip_tests, max_lines):
    found = []
    for dirpath, dirnames, filenames in os.walk(project_path):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        rel_dir = os.path.relpath(dirpath, project_path)
        parts = set(Path(rel_dir).parts)
        if parts & EXCLUDE_DIRS:
            continue

        for fname in filenames:
            ext = os.path.splitext(fname)[1].lstrip('.')
            if ext not in extensions:
                continue

            full_path = os.path.join(dirpath, fname)
            rel_path = os.path.relpath(full_path, project_path)

            if skip_tests and is_test_file(rel_path):
                continue

            found.append((full_path, rel_path, ext))

    return found[:500]


def extract_go(lines):
    imports = []
    exports = []
    functions = []
    classes = []
    interfaces = []
    package = None

    import_block = False
    for i, line in enumerate(lines, 1):
        # Package
        if package is None:
            m = re.match(r'^package\s+(\w+)', line)
            if m:
                package = m.group(1)

        # Imports
        if re.match(r'^import\s*\(', line):
            import_block = True
            continue
        if import_block:
            if re.match(r'^\s*\)', line):
                import_block = False
                continue
            m = re.search(r'"([^"]+)"', line)
            if m:
                imports.append(m.group(1))
            continue
        m = re.match(r'^\s*import\s+"([^"]+)"', line)
        if m:
            imports.append(m.group(1))

        # Functions
        m = re.match(r'^func\s+(?:\([^)]*\)\s+)?(\w+)\(', line)
        if m:
            functions.append({'line': i, 'signature': line.strip()})

        # Types (struct/interface)
        m = re.match(r'^type\s+(\w+)\s+(struct|interface)\s*\{', line)
        if m:
            if m.group(2) == 'interface':
                interfaces.append({'line': i, 'name': m.group(1)})
            classes.append({'line': i, 'name': f"type {m.group(1)} {m.group(2)}"})

        # Exports (capitalized top-level declarations)
        m = re.match(r'^(func|type|var|const)\s+([A-Z]\w*)', line)
        if m:
            exports.append({'line': i, 'declaration': line.strip()})

    return {
        'package': package,
        'imports': imports,
        'exports': exports,
        'classes': classes,
        'functions': functions,
        'interfaces': interfaces,
    }


def extract_python(lines):
    imports = []
    exports = []
    functions = []
    classes = []
    interfaces = []

    for i, line in enumerate(lines, 1):
        # Imports
        m = re.match(r'^(import\s+\w+|from\s+[\w.]+\s+import\s+)', line)
        if m:
            imports.append({'line': i, 'statement': line.strip()})

        # Functions
        m = re.match(r'^\s*def\s+(\w+)\(', line)
        if m:
            functions.append({'line': i, 'signature': line.strip()})

        # Classes
        m = re.match(r'^\s*class\s+(\w+)', line)
        if m:
            classes.append({'line': i, 'name': m.group(1)})

        # Exports (__all__)
        if '__all__' in line:
            exports.append({'line': i, 'declaration': line.strip()})

    return {
        'package': None,
        'imports': imports,
        'exports': exports,
        'classes': classes,
        'functions': functions,
        'interfaces': interfaces,
    }


def extract_typescript(lines):
    imports = []
    exports = []
    functions = []
    classes = []
    interfaces = []

    for i, line in enumerate(lines, 1):
        # Imports
        if re.match(r'^(import\s+|(?:const|let|var)\s+.*require\()', line):
            imports.append({'line': i, 'statement': line.strip()})

        # Functions
        if re.search(r'(?:function\s+\w+|\w+\s*=\s*(?:async\s*)?\(.*\)\s*=>)', line):
            functions.append({'line': i, 'signature': line.strip()})

        # Classes
        m = re.match(r'^\s*class\s+(\w+)', line)
        if m:
            classes.append({'line': i, 'name': m.group(1)})

        # Interfaces (TS only)
        m = re.match(r'^\s*(?:export\s+)?interface\s+(\w+)', line)
        if m:
            interfaces.append({'line': i, 'name': m.group(1)})

        # Exports
        if re.match(r'^export\s+(?:default\s+)?(?:function|class|const|let|var|interface|type|enum)', line):
            exports.append({'line': i, 'declaration': line.strip()})

    return {
        'package': None,
        'imports': imports,
        'exports': exports,
        'classes': classes,
        'functions': functions,
        'interfaces': interfaces,
    }


def extract_rust(lines):
    imports = []
    exports = []
    functions = []
    classes = []
    interfaces = []

    for i, line in enumerate(lines, 1):
        # Use declarations
        m = re.match(r'^use\s+(.+);', line)
        if m:
            imports.append(m.group(1).strip())

        # Functions
        m = re.match(r'^\s*(?:pub\s+)?(?:async\s+)?fn\s+(\w+)\(', line)
        if m:
            functions.append({'line': i, 'signature': line.strip()})

        # Structs / Enums / Traits
        m = re.match(r'^\s*(?:pub\s+)?(struct|enum|trait)\s+(\w+)', line)
        if m:
            classes.append({'line': i, 'name': f"{m.group(1)} {m.group(2)}"})

    return {
        'package': None,
        'imports': imports,
        'exports': exports,
        'classes': classes,
        'functions': functions,
        'interfaces': interfaces,
    }


def extract_java(lines):
    imports = []
    exports = []
    functions = []
    classes = []
    interfaces = []

    for i, line in enumerate(lines, 1):
        # Imports
        m = re.match(r'^import\s+(.+);', line)
        if m:
            imports.append(m.group(1).strip())

        # Methods (simplified)
        m = re.match(r'^\s*(?:public|private|protected|static|\s)+\S+\s+(\w+)\s*\(', line)
        if m:
            functions.append({'line': i, 'signature': line.strip()})

        # Classes / Interfaces / Enums
        m = re.match(r'^\s*(?:public\s+)?(?:abstract\s+)?(?:final\s+)?(class|interface|enum)\s+(\w+)', line)
        if m:
            if m.group(1) == 'interface':
                interfaces.append({'line': i, 'name': m.group(2)})
            classes.append({'line': i, 'name': f"{m.group(1)} {m.group(2)}"})

    return {
        'package': None,
        'imports': imports,
        'exports': exports,
        'classes': classes,
        'functions': functions,
        'interfaces': interfaces,
    }


EXTRACTORS = {
    'go': extract_go,
    'py': extract_python,
    'ts': extract_typescript,
    'tsx': extract_typescript,
    'js': extract_typescript,
    'jsx': extract_typescript,
    'mjs': extract_typescript,
    'rs': extract_rust,
    'java': extract_java,
}


def main():
    args = parse_args()
    project_path = args.project_path

    if not os.path.isdir(project_path):
        print(json.dumps({'status': 'error', 'error': 'No valid project directory provided.'}))
        sys.exit(1)

    if args.extensions:
        extensions = set(args.extensions.split(','))
    else:
        extensions = DEFAULT_EXTENSIONS

    skip_tests = not args.no_skip_tests

    files = discover_files(project_path, extensions, skip_tests, args.max_file_lines)

    files_found = len(files)
    files_analyzed = 0
    files_skipped = 0
    modules = []

    for full_path, rel_path, ext in files:
        try:
            with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
        except (OSError, PermissionError):
            files_skipped += 1
            continue

        line_count = len(lines)
        if line_count > args.max_file_lines or line_count == 0:
            files_skipped += 1
            continue

        files_analyzed += 1
        lang = EXT_TO_LANG.get(ext, 'unknown')

        extractor = EXTRACTORS.get(ext)
        if extractor:
            extracted = extractor(lines)
        else:
            extracted = {
                'package': None, 'imports': [], 'exports': [],
                'classes': [], 'functions': [], 'interfaces': [],
            }

        modules.append({
            'file': rel_path.replace('\\', '/'),
            'language': lang,
            'lines': line_count,
            'package': extracted['package'],
            'imports': extracted['imports'],
            'exports': extracted['exports'],
            'classes': extracted['classes'],
            'functions': extracted['functions'],
            'interfaces': extracted['interfaces'],
        })

    output = {
        'status': 'success',
        'method': 'regex',
        'files_found': files_found,
        'files_analyzed': files_analyzed,
        'files_skipped': files_skipped,
        'modules': modules,
    }
    print(json.dumps(output, ensure_ascii=False))


if __name__ == '__main__':
    main()
