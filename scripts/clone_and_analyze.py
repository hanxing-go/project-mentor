#!/usr/bin/env python3
# clone_and_analyze.py — Clone a GitHub repo and generate a structured project overview
# Usage: python clone_and_analyze.py <repo-url> [--deep] [--output-dir <dir>]
# Output: JSON to stdout
#
# Cross-platform Python port of clone_and_analyze.sh.
# Uses stdlib only — no pip dependencies.

import sys
import os
import json
import subprocess
import re
import time
import tempfile
import shutil
import argparse
from pathlib import Path
from collections import Counter

EXCLUDE_DIRS = {
    'node_modules', 'vendor', '.git', 'venv', '.venv',
    'target', '__pycache__', 'dist', 'build', '.next',
    '.nuxt', '.cache', 'coverage', '*.egg-info',
}

EXCLUDE_GLOBS = ['*.lock']


def parse_args():
    parser = argparse.ArgumentParser(description='Clone and analyze a GitHub repo')
    parser.add_argument('repo_url', help='GitHub repository URL')
    parser.add_argument('--deep', action='store_true', help='Full clone (not shallow)')
    parser.add_argument('--output-dir', help='Directory to clone into')
    return parser.parse_args()


def extract_project_name(url):
    m = re.search(r'/([^/]+?)(?:\.git)?$', url.rstrip('/'))
    if not m:
        return None
    return m.group(1)


def clone_repo(url, target_dir, deep=False):
    start = time.time()
    args = ['git', 'clone']
    if not deep:
        args += ['--depth=1']
    args += [url, str(target_dir)]
    try:
        subprocess.run(args, check=True, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300)
    except subprocess.CalledProcessError as e:
        return {'error': True, 'stderr': e.stderr[:500], 'duration': time.time() - start}
    duration = time.time() - start
    return {'error': False, 'duration': duration}


def iter_source_files(root):
    exclude_set = EXCLUDE_DIRS
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in exclude_set]
        rel = os.path.relpath(dirpath, root)
        parts = set(Path(rel).parts)
        if parts & exclude_set:
            continue
        for f in filenames:
            if any(Path(f).match(g) for g in EXCLUDE_GLOBS):
                continue
            yield os.path.join(dirpath, f)


def detect_language(root):
    counter = Counter()
    for fpath in iter_source_files(root):
        ext = os.path.splitext(fpath)[1].lstrip('.')
        if ext:
            counter[ext] += 1

    ext_to_lang = {
        'go': 'Go', 'rs': 'Rust', 'py': 'Python', 'pyx': 'Python',
        'ts': 'TypeScript', 'tsx': 'TypeScript',
        'js': 'JavaScript', 'jsx': 'JavaScript', 'mjs': 'JavaScript',
        'java': 'Java', 'rb': 'Ruby', 'php': 'PHP',
        'c': 'C/C++', 'cpp': 'C/C++', 'h': 'C/C++', 'hpp': 'C/C++',
        'swift': 'Swift', 'kt': 'Kotlin', 'kts': 'Kotlin',
        'vue': 'Vue', 'svelte': 'Svelte',
        'sh': 'Shell', 'bash': 'Shell', 'zsh': 'Shell',
        'sol': 'Solidity',
    }

    lang_scores = Counter()
    for ext, count in counter.items():
        lang = ext_to_lang.get(ext)
        if lang:
            lang_scores[lang] += count

    if not lang_scores:
        return 'Unknown', {}

    primary = lang_scores.most_common(1)[0][0]
    breakdown = dict(lang_scores)
    return primary, breakdown


def detect_framework(root):
    # Go
    gomod = os.path.join(root, 'go.mod')
    if os.path.isfile(gomod):
        content = open(gomod).read()
        if 'gin-gonic/gin' in content: return 'Gin'
        if 'labstack/echo' in content: return 'Echo'
        if 'gofiber/fiber' in content: return 'Fiber'
        if 'gorilla/mux' in content: return 'Gorilla Mux'
        if 'spf13/cobra' in content: return 'Cobra (CLI)'
        if 'urfave/cli' in content: return 'urfave/cli (CLI)'

    # Node
    pkg_json = os.path.join(root, 'package.json')
    if os.path.isfile(pkg_json):
        content = open(pkg_json).read()
        if '"next"' in content: return 'Next.js'
        if '"react"' in content: return 'React'
        if '"vue"' in content: return 'Vue'
        if '"svelte"' in content: return 'Svelte'
        if '"express"' in content: return 'Express'
        if '"fastify"' in content: return 'Fastify'
        if '"koa"' in content: return 'Koa'
        if '"nestjs"' in content: return 'NestJS'
        if '"astro"' in content: return 'Astro'

    # Python
    py_deps = ''
    req = os.path.join(root, 'requirements.txt')
    pptoml = os.path.join(root, 'pyproject.toml')
    if os.path.isfile(req):
        py_deps += open(req).read()
    if os.path.isfile(pptoml):
        py_deps += open(pptoml).read()
    if py_deps:
        if 'fastapi' in py_deps: return 'FastAPI'
        if 'django' in py_deps: return 'Django'
        if 'flask' in py_deps: return 'Flask'
        if 'typer' in py_deps or 'click' in py_deps: return 'Click/Typer (CLI)'
        if any(x in py_deps for x in ('torch', 'tensorflow', 'jax')): return 'ML Framework'

    # Rust
    cargo = os.path.join(root, 'Cargo.toml')
    if os.path.isfile(cargo):
        content = open(cargo).read()
        if 'actix-web' in content: return 'Actix Web'
        if 'axum' in content: return 'Axum'
        if 'rocket' in content: return 'Rocket'
        if 'clap' in content: return 'Clap (CLI)'

    return None


def detect_build_system(root):
    checks = [
        ('go.mod', 'go mod'),
        ('go.sum', 'go mod'),
        ('package.json', 'npm/yarn/pnpm'),
        ('Cargo.toml', 'Cargo'),
        ('Makefile', 'Make'),
        ('CMakeLists.txt', 'CMake'),
        ('pom.xml', 'Maven'),
        ('build.gradle', 'Gradle'),
        ('build.gradle.kts', 'Gradle'),
        ('pyproject.toml', 'pip/setuptools'),
        ('setup.py', 'setuptools'),
    ]
    for fname, system in checks:
        if os.path.isfile(os.path.join(root, fname)):
            return system
    return None


def detect_test_framework(root):
    if os.path.isfile(os.path.join(root, 'go.mod')):
        return 'go test'
    if os.path.isdir(os.path.join(root, '__tests__')):
        return 'Jest'
    pkg_json = os.path.join(root, 'package.json')
    if os.path.isfile(pkg_json):
        content = open(pkg_json).read()
        if '"jest"' in content: return 'Jest'
        if '"vitest"' in content: return 'Vitest'
        if '"mocha"' in content: return 'Mocha'
    req = os.path.join(root, 'requirements.txt')
    if os.path.isfile(req) and 'pytest' in open(req).read():
        return 'pytest'
    if os.path.isfile(os.path.join(root, 'Cargo.toml')):
        return 'cargo test'
    return None


def count_files(root):
    count = 0
    for _ in iter_source_files(root):
        count += 1
    return count


def count_by_extension(root):
    counter = Counter()
    for fpath in iter_source_files(root):
        ext = os.path.splitext(fpath)[1].lstrip('.')
        if ext:
            counter[ext] += 1
    return dict(counter.most_common(10))


def count_by_top_directory(root):
    counter = Counter()
    for fpath in iter_source_files(root):
        rel = os.path.relpath(fpath, root)
        top = rel.split(os.sep)[0]
        counter[top] += 1
    return dict(counter.most_common(15))


def generate_tree(root, max_depth=3, max_lines=80):
    lines = []
    exclude_set = EXCLUDE_DIRS

    def _walk(current, prefix, depth):
        if depth > max_depth or len(lines) >= max_lines:
            return
        try:
            entries = sorted(os.listdir(current))
        except PermissionError:
            return
        entries = [e for e in entries if e not in exclude_set and not e.startswith('.')]
        dirs = [e for e in entries if os.path.isdir(os.path.join(current, e))]
        files = [e for e in entries if os.path.isfile(os.path.join(current, e))]
        items = dirs + files
        for i, name in enumerate(items):
            if len(lines) >= max_lines:
                return
            is_last = (i == len(items) - 1)
            connector = '└── ' if is_last else '├── '
            lines.append(f'{prefix}{connector}{name}')
            full = os.path.join(current, name)
            if os.path.isdir(full):
                ext_prefix = '    ' if is_last else '│   '
                _walk(full, prefix + ext_prefix, depth + 1)

    lines.append(os.path.basename(root) or root)
    _walk(root, '', 1)
    return '\n'.join(lines)


def main():
    args = parse_args()

    project_name = extract_project_name(args.repo_url)
    if not project_name:
        print(json.dumps({'status': 'error', 'error': 'Could not parse project name from URL.'}))
        sys.exit(1)

    output_base = args.output_dir or os.path.join(tempfile.gettempdir(), 'project-mentor-clones')
    clone_dir = os.path.join(output_base, project_name)

    # Remove existing clone
    if os.path.exists(clone_dir):
        shutil.rmtree(clone_dir, ignore_errors=True)
    os.makedirs(output_base, exist_ok=True)

    # Clone
    result = clone_repo(args.repo_url, clone_dir, deep=args.deep)
    if result['error']:
        print(json.dumps({'status': 'error', 'error': f"Failed to clone repository. {result['stderr']}"}))
        sys.exit(1)

    root = clone_dir
    primary_language, language_breakdown = detect_language(root)
    framework = detect_framework(root)
    build_system = detect_build_system(root)
    test_framework = detect_test_framework(root)
    file_count = count_files(root)
    by_ext = count_by_extension(root)
    by_dir = count_by_top_directory(root)
    tree = generate_tree(root)

    output = {
        'status': 'success',
        'project_name': project_name,
        'clone_path': clone_dir,
        'clone_depth': 'full' if args.deep else 'shallow',
        'clone_duration_seconds': round(result['duration']),
        'tech_stack': {
            'primary_language': primary_language,
            'language_breakdown': language_breakdown,
            'framework': framework,
            'build_system': build_system,
            'test_framework': test_framework,
        },
        'file_stats': {
            'total': file_count,
            'by_extension': by_ext,
            'by_top_directory': by_dir,
        },
        'directory_tree': tree,
    }
    print(json.dumps(output, ensure_ascii=False))


if __name__ == '__main__':
    main()
