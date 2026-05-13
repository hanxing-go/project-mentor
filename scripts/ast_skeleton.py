#!/usr/bin/env python3
# ast_skeleton.py — Extract code skeleton from a codebase (imports, signatures, exports only)
# Usage: python ast_skeleton.py <project-path> [--extensions go,py,ts] [--skip-tests] [--max-file-lines 5000] [--max-files 500] [--summaries-only]
# Output: JSON to stdout
#
# Large project mode: Files are scored by importance (entry points, fan-in, roles).
# Boilerplate (DTOs, enums, configs) is de-prioritized.
# --summaries-only gives directory-level overview for any project size.
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

# Kinds that receive score penalty (low information density)
BOILERPLATE_KINDS = frozenset({
    'dto', 'vo', 'po', 'req', 'resp',
    'enum', 'mapper', 'constant', 'config', 'properties',
})

# Kinds that receive score bonus (architecturally significant)
BONUS_KINDS = frozenset({
    'service', 'controller', 'manager', 'handler', 'provider',
})

# Entry-point filenames that are ALWAYS entry regardless of location
ENTRY_POINT_ALWAYS = frozenset({
    'main.ts', 'main.tsx', 'main.js', 'main.jsx', 'main.mjs',
    'app.ts', 'app.tsx', 'app.js', 'app.jsx',
    'server.ts', 'server.js',
    '_app.tsx', '_app.ts',
    'application.java', 'main.java', 'app.java',
    'springbootapplication.java', 'servletinitializer.java',
    'main.go',
    'main.rs', 'lib.rs',
    'main.py', '__main__.py', 'app.py', 'server.py', 'manage.py',
    'train.py',
    'main.rb', 'app.rb',
    'main.swift', 'main.kt',
    'main.c', 'main.cpp',
})

# Entry by basename but ONLY when at project root (depth <= 2): barrel/index files
ENTRY_POINT_ROOT_ONLY = frozenset({
    'index.ts', 'index.tsx', 'index.js', 'index.jsx',
    '__init__.py',
})

# Suffix patterns for entry point files (case-insensitive)
ENTRY_POINT_SUFFIXES = (
    'application.java',
    'application.kt',
    'app.go',
)

# Classification rules: (language, scope) -> [(regex_pattern, kind), ...]
# Filename patterns (match against basename, case-insensitive)
_FILENAME_RULES = {
    'dto': [r'(?:dto|vo|po|req|request|resp|response|payload|schema)\.'],
    'enum': [r'(?:enum|enums)\.'],
    'mapper': [r'mapper\.'],
    'constant': [r'(?:constant|constants|property|properties|setting|settings)\.'],
    'config': [r'config\.'],
    'service': [r'service\.'],
    'controller': [r'controller\.'],
    'repository': [r'(?:repository|repo|dao|mapper)\.'],
    'model': [r'(?:entity|model|domain|models)\.'],
    'util': [r'(?:util|utils|helper|helpers)\.'],
    'interface': [r'(?:interface|interfaces|types|type|protocol|abc|abstract|base)\.'],
    'handler': [r'handler\.'],
    'middleware': [r'(?:middleware|guard|interceptor|decorator|filter)\.'],
    'error': [r'(?:exception|exceptions|error|errors)\.'],
}

# Path-based rules (match against directory names, case-insensitive)
_PATH_RULES = {
    'dto': [r'[/\\](?:dto|vo|request|response|payload|schema)s?[/\\]'],
    'enum': [r'[/\\](?:enums?)[/\\]'],
    'mapper': [r'[/\\](?:mappers?|dao)[/\\]'],
    'config': [r'[/\\](?:config|configuration|settings)[/\\]'],
    'service': [r'[/\\](?:services?)[/\\]'],
    'controller': [r'[/\\](?:controllers?|handlers?|views?)[/\\]'],
    'repository': [r'[/\\](?:repositories|repository|dao)[/\\]'],
    'model': [r'[/\\](?:models?|entities?|domain)[/\\]'],
    'util': [r'[/\\](?:utils?|helpers?)[/\\]'],
    'interface': [r'[/\\](?:interfaces?|protocols?|abc|abstract)[/\\]'],
    'middleware': [r'[/\\](?:middlewares?|guards?|interceptors?|decorators?|filters?)[/\\]'],
    'error': [r'[/\\](?:exceptions?|errors?)[/\\]'],
}

# Class-name-based inference rules (fallback when filename/path can't classify)
_INFERRED_RULES = [
    (r'service', 'service'),
    (r'controller', 'controller'),
    (r'handler', 'handler'),
    (r'repository|dao', 'repository'),
    (r'mapper', 'mapper'),
    (r'dto$|vo$|request$|response$|payload$|schema$', 'dto'),
    (r'config|settings|properties', 'config'),
    (r'enum$|enums$', 'enum'),
    (r'entity|model|domain', 'model'),
    (r'util$|utils$|helper$|helpers$', 'util'),
    (r'middleware|filter|interceptor|guard|decorator', 'middleware'),
    (r'exception|error$', 'error'),
    (r'interface$|^i[A-Z]', 'interface'),
    (r'module$', 'module'),
    (r'resolver$', 'resolver'),
    (r'provider$|factory$', 'provider'),
    (r'manager$', 'manager'),
]


def parse_args():
    parser = argparse.ArgumentParser(description='Extract AST skeleton from a codebase')
    parser.add_argument('project_path', help='Path to project directory')
    parser.add_argument('--extensions', help='Comma-separated list of extensions (e.g. go,py,ts)')
    parser.add_argument('--skip-tests', action='store_true', default=True)
    parser.add_argument('--no-skip-tests', action='store_true', default=False)
    parser.add_argument('--max-file-lines', type=int, default=5000)
    parser.add_argument('--max-files', type=int, default=500,
                        help='Max detailed file skeletons in modules output (0=unlimited, default 500)')
    parser.add_argument('--summaries-only', action='store_true', default=False,
                        help='Output only directory-level module_summaries, no per-file modules')
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


def discover_files(project_path, extensions, skip_tests):
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

    return found  # All files — scoring + truncation happens in main()


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

        # Classes (export / export default / abstract)
        m = re.match(r'^\s*(?:export\s+)?(?:default\s+)?(?:abstract\s+)?class\s+(\w+)', line)
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
    package = None

    for i, line in enumerate(lines, 1):
        # Package
        if package is None:
            m = re.match(r'^package\s+([\w.]+)\s*;', line)
            if m:
                package = m.group(1)

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
        'package': package,
        'imports': imports,
        'exports': exports,
        'classes': classes,
        'functions': functions,
        'interfaces': interfaces,
    }


def extract_cpp(lines):
    imports = []
    exports = []
    functions = []
    classes = []
    interfaces = []

    brace_depth = 0
    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # #include statements
        m = re.match(r'#include\s+(.+)', stripped)
        if m:
            imports.append(m.group(1).strip())
            continue

        # Skip preprocessor directives
        if re.match(r'#(?:define|ifdef|ifndef|if|else|endif|pragma|undef|error|warning)', stripped):
            continue

        # Namespaces (as package-like)
        m = re.match(r'namespace\s+(\w+)', stripped)
        if m:
            classes.append({'line': i, 'name': f'namespace {m.group(1)}'})

        # Class/struct/enum definitions
        m = re.match(r'(?:template\s*<[^>]*>\s*)?(?:class|struct|enum(?:\s+class)?)\s+(\w+)', stripped)
        if m and brace_depth == 0:
            classes.append({'line': i, 'name': f'{m.group(0).split()[0]} {m.group(1)}'})

        # Function definitions (heuristic: return_type func_name( at namespace/global scope)
        # Match: type name( | type* name( | type Class::method( | type::ns::func(
        m = re.match(
            r'(?:virtual\s+)?(?:static\s+)?(?:inline\s+)?(?:explicit\s+)?(?:const\s+)?'
            r'(?:[\w:]+(?:<[^>]*>)?[\s*&]+)+'
            r'(\w+(?:::\w+)*)\s*\([^)]*\)\s*(?:const\s*)?(?:override\s*)?\s*(?:\{|;)',
            stripped,
        )
        if m and brace_depth == 0:
            func_name = m.group(1)
            if func_name not in ('if', 'while', 'for', 'switch', 'return', 'sizeof', 'typeof'):
                functions.append({'line': i, 'signature': stripped[:120]})

        # Track brace depth to skip function bodies
        brace_depth += stripped.count('{') - stripped.count('}')

    return {
        'package': package,
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
    'c': extract_cpp,
    'cpp': extract_cpp,
    'h': extract_cpp,
    'hpp': extract_cpp,
}


def _is_root_level(rel_path):
    parts = Path(rel_path).parts
    # Root of project (1 part), or one dir down (2 parts),
    # or under src/ / lib/ / app/ / cmd/ / pkg/ at depth 2-3
    if len(parts) <= 2:
        return True
    if len(parts) == 3 and parts[0] in ('src', 'lib', 'app', 'internal', 'cmd', 'pkg'):
        return True
    return False


def classify_file(rel_path, language, extracted_data):
    filename = os.path.basename(rel_path).lower()

    # 1. Test check
    if is_test_file(rel_path):
        return 'test'

    # 2. Entry point check
    if filename in ENTRY_POINT_ALWAYS:
        return 'entry'
    if filename in ENTRY_POINT_ROOT_ONLY and _is_root_level(rel_path):
        return 'entry'
    if filename.endswith(ENTRY_POINT_SUFFIXES):
        return 'entry'

    # 3. Filename-based rules
    for kind, patterns in _FILENAME_RULES.items():
        for pattern in patterns:
            if re.search(pattern, filename):
                return kind

    # 4. Path-based rules (each directory component)
    parts = Path(rel_path).parts
    for part in parts:
        part_lower = part.lower()
        for kind, patterns in _PATH_RULES.items():
            for pattern in patterns:
                if re.search(pattern, part_lower):
                    return kind

    # 5. Class/interface name inference (fallback)
    for cls in extracted_data.get('classes', []):
        name = (cls.get('name', '') if isinstance(cls, dict) else str(cls)).lower()
        for pattern, kind in _INFERRED_RULES:
            if re.search(pattern, name):
                return kind
    for iface in extracted_data.get('interfaces', []):
        name = (iface.get('name', '') if isinstance(iface, dict) else str(iface)).lower()
        for pattern, kind in _INFERRED_RULES:
            if re.search(pattern, name):
                return kind

    return 'unknown'


def _resolve_import_to_file(import_stmt, importer_path, known_files):
    cleaned = import_stmt.strip().strip('\'"`;')
    if not cleaned:
        return None

    # Relative imports: ./foo, ../bar
    if cleaned.startswith('.'):
        importer_dir = os.path.dirname(importer_path).replace('\\\\', '/')
        resolved = os.path.normpath(os.path.join(importer_dir, cleaned)).replace('\\\\', '/')
        # Try exact match, then with common extensions
        for ext in ('', '.ts', '.tsx', '.js', '.jsx', '.mjs', '.py', '.go', '.rs', '.java', '.rb', '.swift', '.kt'):
            candidate = resolved + ext
            if candidate in known_files:
                return candidate
        # Try index files
        for ext in ('.ts', '.tsx', '.js', '.py'):
            candidate = resolved + '/index' + ext
            if candidate in known_files:
                return candidate
        candidate = resolved + '/__init__.py'
        if candidate in known_files:
            return candidate
        return None

    # Java-style: com.example.model.User -> com/example/model/User.java
    if '.' in cleaned:
        as_path = cleaned.replace('.', '/') + '.java'
        if as_path in known_files:
            return as_path

    # Go-style: "github.com/foo/bar" -> match by suffix
    for kf in known_files:
        if kf.endswith('/' + cleaned) or cleaned.endswith(kf):
            return kf

    return None


def build_import_map(all_modules):
    import_map = {}
    project_files = {m['file'] for m in all_modules}

    for module in all_modules:
        for imp in module.get('imports', []):
            if isinstance(imp, dict):
                stmt = imp.get('statement', '')
            else:
                stmt = str(imp)
            target = _resolve_import_to_file(stmt, module['file'], project_files)
            if target:
                import_map.setdefault(target, []).append(module['file'])

    return import_map


def compute_importance_score(module, import_map):
    score = 0
    filename = os.path.basename(module['file']).lower()

    if filename in ENTRY_POINT_ALWAYS or (filename in ENTRY_POINT_ROOT_ONLY and _is_root_level(module['file'])) or filename.endswith(ENTRY_POINT_SUFFIXES):
        score += 100

    importers = import_map.get(module['file'], [])
    score += len(importers) * 2

    kind = module.get('kind', 'unknown')
    if kind in BOILERPLATE_KINDS:
        score -= 50
    if kind in BONUS_KINDS:
        score += 30
    if kind == 'interface':
        score += 20

    if module.get('lines', 0) > 200:
        score += 10

    parts = Path(module['file']).parts
    if len(parts) <= 2:
        score += 20
    elif len(parts) == 3 and parts[0] in ('src', 'lib', 'app', 'internal', 'cmd', 'pkg'):
        score += 15

    module['importance_score'] = score
    module['fan_in'] = len(importers)
    return score


def build_module_summaries(modules):
    from collections import defaultdict

    dirs = defaultdict(lambda: {
        'files': [],
        'total_lines': 0,
        'languages': defaultdict(int),
        'kinds': defaultdict(int),
        'scores': [],
        'subdirs': set(),
    })

    for module in modules:
        rel_path = module['file']
        dirname = os.path.dirname(rel_path) or '.'

        entry = dirs[dirname]
        entry['files'].append(module)
        entry['total_lines'] += module.get('lines', 0)
        entry['languages'][module.get('language', 'unknown')] += 1
        entry['kinds'][module.get('kind', 'unknown')] += 1
        entry['scores'].append(module.get('importance_score', 0))

        if dirname != '.':
            parent = os.path.dirname(dirname) or '.'
            dirs[parent]['subdirs'].add(dirname)

    summaries = []
    for dirname, data in sorted(dirs.items()):
        # Skip directories with no direct files (only subdirectories)
        if len(data['files']) == 0:
            continue
        data['files'].sort(key=lambda m: m.get('importance_score', 0), reverse=True)

        top_exports = []
        top_classes = []
        top_functions = []
        for m in data['files'][:5]:
            for exp in m.get('exports', [])[:2]:
                name = exp.get('declaration', exp) if isinstance(exp, dict) else str(exp)
                top_exports.append(name[:80])
            for cls in m.get('classes', [])[:2]:
                name = cls.get('name', str(cls))
                top_classes.append(name)
            for fn in m.get('functions', [])[:2]:
                sig = fn.get('signature', str(fn))
                top_functions.append(sig[:80])

        lang_counts = data['languages']
        primary_lang = max(lang_counts, key=lang_counts.get) if lang_counts else 'unknown'
        scores = data['scores']

        summaries.append({
            'directory': dirname.replace('\\\\', '/'),
            'file_count': len(data['files']),
            'total_lines': data['total_lines'],
            'primary_language': primary_lang,
            'language_distribution': dict(lang_counts),
            'kind_distribution': dict(data['kinds']),
            'top_exports': top_exports[:10],
            'top_classes': top_classes[:10],
            'top_functions': top_functions[:10],
            'mean_importance_score': round(sum(scores) / len(scores), 1) if scores else 0,
            'max_importance_score': max(scores) if scores else 0,
            'subdirectories': sorted(data['subdirs']),
        })

    summaries.sort(key=lambda s: (s['directory'].count('/'), s['directory']))
    return summaries


def main():
    # Ensure UTF-8 output on Windows (avoids GBK encoding errors with Unicode in source)
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    args = parse_args()
    project_path = args.project_path

    if not os.path.isdir(project_path):
        print(json.dumps({'status': 'error', 'error': 'No valid project directory provided.'}))
        sys.exit(1)

    extensions = set(args.extensions.split(',')) if args.extensions else DEFAULT_EXTENSIONS
    skip_tests = not args.no_skip_tests
    max_files = args.max_files  # 0 means unlimited, None means not set

    # ---- STEP 1: Discover ALL files (no truncation here) ----
    file_entries = discover_files(project_path, extensions, skip_tests)
    total_found = len(file_entries)

    # ---- STEP 2: Extract ALL files ----
    all_modules = []
    files_analyzed = 0
    files_skipped = 0

    for full_path, rel_path, ext in file_entries:
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

        module = {
            'file': rel_path.replace('\\\\', '/'),
            'language': lang,
            'lines': line_count,
            'package': extracted['package'],
            'imports': extracted['imports'],
            'exports': extracted['exports'],
            'classes': extracted['classes'],
            'functions': extracted['functions'],
            'interfaces': extracted['interfaces'],
        }
        all_modules.append(module)

    # ---- STEP 3: Classify each file ----
    for module in all_modules:
        module['kind'] = classify_file(module['file'], module['language'], module)

    # ---- STEP 4: Build import map and compute fan-in ----
    import_map = build_import_map(all_modules)

    # ---- STEP 5: Score each file ----
    for module in all_modules:
        compute_importance_score(module, import_map)

    # ---- STEP 6: Sort by importance score (descending) ----
    all_modules.sort(key=lambda m: m.get('importance_score', 0), reverse=True)

    # ---- STEP 7: Build module summaries (from ALL modules) ----
    module_summaries = build_module_summaries(all_modules)

    # ---- STEP 8: Build project summary ----
    from collections import Counter
    lang_counter = Counter(m['language'] for m in all_modules)
    kind_counter = Counter(m.get('kind', 'unknown') for m in all_modules)
    total_lines = sum(m['lines'] for m in all_modules)

    project_summary = {
        'total_files_found': total_found,
        'total_files_analyzed': files_analyzed,
        'total_files_skipped': files_skipped,
        'total_lines': total_lines,
        'languages': dict(lang_counter.most_common()),
        'kind_distribution': dict(kind_counter.most_common()),
    }

    # ---- STEP 9: Select modules for detailed output ----
    if args.summaries_only:
        output_modules = []
        truncation_notice = (
            f'Skipped per-file module details (--summaries-only). '
            f'{files_analyzed} files analyzed. '
            f'See `module_summaries` for directory-level overview and `project_summary` for aggregate stats.'
        )
    elif max_files == 0 or len(all_modules) <= max_files:
        output_modules = all_modules
        truncation_notice = None
    else:
        output_modules = all_modules[:max_files]
        truncation_notice = (
            f'Showing top {max_files} of {len(all_modules)} files '
            f'by importance score (entry points, high fan-in, and '
            f'architecturally significant files prioritized). '
            f'Boilerplate (DTOs, enums, configs, mappers) is de-prioritized. '
            f'Use --max-files N to adjust (0=unlimited). '
            f'Use --summaries-only for directory-level overview only. '
            f'The `module_summaries` field covers all directories regardless.'
        )

    # ---- STEP 10: Build output JSON ----
    output = {
        'status': 'success',
        'method': 'regex',
        'files_found': total_found,
        'files_analyzed': files_analyzed,
        'files_skipped': files_skipped,
        'project_summary': project_summary,
        'module_summaries': module_summaries,
        'modules': output_modules,
    }
    if truncation_notice:
        output['truncation_notice'] = truncation_notice

    print(json.dumps(output, ensure_ascii=False))


if __name__ == '__main__':
    main()
