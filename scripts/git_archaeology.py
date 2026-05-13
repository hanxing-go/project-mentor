#!/usr/bin/env python3
# git_archaeology.py — Analyze full Git history and output a project growth timeline
# Usage: python git_archaeology.py <repo-path> [--max-commits <N>] [--recent-days <N>] [--timeout <N>]
# Output: JSON to stdout
#
# Cross-platform Python port of git_archaeology.sh.
# Uses stdlib only — no pip dependencies.

import sys
import os
import re
import json
import subprocess
import argparse
from pathlib import Path


def run_git(repo_path, *args, timeout=60):
    try:
        result = subprocess.run(
            ['git', *args],
            cwd=repo_path,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=timeout,
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return '', 'timeout', 1
    except Exception as e:
        return '', str(e), 1


def parse_args():
    parser = argparse.ArgumentParser(description='Git archaeology analysis')
    parser.add_argument('repo_path', help='Path to cloned git repository')
    parser.add_argument('--max-commits', type=int, default=2000)
    parser.add_argument('--recent-days', type=int, default=90)
    parser.add_argument('--timeout', type=int, default=60)
    return parser.parse_args()


def check_repo(repo_path):
    git_dir = os.path.join(repo_path, '.git')
    if not os.path.isdir(git_dir):
        return False, 'No Git repository found at the given path.'
    return True, None


def check_shallow(repo_path):
    count_out, _, _ = run_git(repo_path, 'rev-list', '--count', 'HEAD')
    if not count_out or count_out == '0':
        return False
    is_shallow, _, _ = run_git(repo_path, 'rev-parse', '--is-shallow-repository')
    if count_out == '1' and 'true' in is_shallow.lower():
        return True
    return False


def get_first_commit(repo_path):
    # Find the root commit
    hash_out, _, _ = run_git(repo_path, 'rev-list', '--max-parents=0', 'HEAD')
    first_hash = (hash_out.split('\n')[-1].strip() if hash_out else '')
    if not first_hash:
        # Fallback: first commit chronologically
        log_out, _, _ = run_git(repo_path, 'log', '--reverse', '--format=%H')
        first_hash = log_out.split('\n')[0].strip() if log_out else ''

    if not first_hash:
        return None

    date_out, _, _ = run_git(repo_path, 'show', '-s', '--format=%ai', first_hash)
    author_out, _, _ = run_git(repo_path, 'show', '-s', '--format=%an', first_hash)
    msg_out, _, _ = run_git(repo_path, 'show', '-s', '--format=%s', first_hash)
    stat_out, _, _ = run_git(repo_path, 'show', '--stat', '--format=', first_hash)

    first_date = date_out.split(' ')[0] if date_out else ''
    first_author = author_out or ''
    first_msg = msg_out or ''

    # Parse files changed from stat
    files_match = re.search(r'(\d+) files? changed', stat_out)
    first_files = int(files_match.group(1)) if files_match else 0

    insert_match = re.search(r'(\d+) insertions?', stat_out)
    first_insertions = int(insert_match.group(1)) if insert_match else 0

    return {
        'hash': first_hash[:8],
        'date': first_date,
        'author': first_author,
        'message': first_msg,
        'files_changed': first_files,
        'lines_added': first_insertions,
    }


def get_milestones(repo_path):
    milestones = []

    # Method A: Directory birth — first commit touching each top-level directory
    exclude = {'node_modules', 'vendor', '.git', 'venv', 'target', '__pycache__',
               'dist', 'build', '.next', '.nuxt', '.cache'}
    try:
        entries = os.listdir(repo_path)
    except PermissionError:
        entries = []

    dirs = []
    for e in sorted(entries):
        full = os.path.join(repo_path, e)
        if os.path.isdir(full) and e not in exclude and not e.startswith('.'):
            dirs.append(e)

    for d in dirs[:10]:
        out, _, _ = run_git(repo_path, 'log', '--reverse', '--format=%H|%ai|%s', '--', d)
        if out:
            first_line = out.split('\n')[0]
            parts = first_line.split('|', 2)
            if len(parts) >= 2:
                milestones.append({
                    'hash': parts[0][:8] if parts[0] else '',
                    'date': parts[1].split(' ')[0] if parts[1] else '',
                    'description': f'Directory `{d}/` created',
                    'significance': f'New subsystem: {d}',
                    'detected_by': 'directory_birth',
                })

    # Method B: Tag-based milestones (major versions)
    tags_out, _, _ = run_git(
        repo_path, 'tag', '--sort=creatordate', '--format=%(creatordate:short)|%(refname:short)',
        timeout=30,
    )
    if tags_out:
        for line in tags_out.split('\n')[:10]:
            parts = line.split('|', 1)
            if len(parts) == 2:
                tagdate, tagname = parts
                if re.search(r'v?\d+\.\d+', tagname):
                    taghash_out, _, _ = run_git(repo_path, 'rev-list', '-1', tagname)
                    taghash = taghash_out.strip() if taghash_out else ''
                    if taghash:
                        tagmsg_out, _, _ = run_git(repo_path, 'show', '-s', '--format=%s', taghash)
                        milestones.append({
                            'hash': taghash[:8],
                            'date': tagdate,
                            'description': f'Release: {tagname}',
                            'significance': f'Version release — {tagmsg_out or ""}',
                            'detected_by': 'tag',
                        })

    # Deduplicate and sort by date
    seen = set()
    unique = []
    for m in sorted(milestones, key=lambda x: x['date']):
        key = (m['date'], m['description'])
        if key not in seen:
            seen.add(key)
            unique.append(m)
    return unique


def get_recent_activity(repo_path, recent_days):
    count_out, _, _ = run_git(repo_path, 'log', f'--after={recent_days} days ago', '--oneline')
    commit_count = len(count_out.split('\n')) if count_out else 0

    # Active branches
    branches_out, _, _ = run_git(repo_path, 'branch', '-r', '--sort=-committerdate')
    active_branches = []
    if branches_out:
        for line in branches_out.split('\n')[:5]:
            name = line.strip().lstrip('* ')
            name = re.sub(r'^origin/', '', name)
            # Filter out HEAD references
            if name and 'HEAD ->' not in name:
                active_branches.append(name)

    # Top contributors
    shortlog_out, _, _ = run_git(repo_path, 'shortlog', '-sn', f'--after={recent_days} days ago')
    top_contributors = []
    if shortlog_out:
        for line in shortlog_out.split('\n')[:5]:
            parts = line.strip().split('\t')
            if len(parts) == 2:
                top_contributors.append({'name': parts[1], 'commits': int(parts[0])})

    return {
        'days_analyzed': recent_days,
        'commit_count': commit_count,
        'active_branches': active_branches,
        'top_contributors': top_contributors,
    }


def get_growth_timeline(repo_path):
    total_out, _, _ = run_git(repo_path, 'rev-list', '--count', 'HEAD')
    total_commits = int(total_out) if total_out and total_out.isdigit() else 0
    if total_commits == 0:
        return [], total_commits

    interval = max(1, total_commits // 20)
    timeline = []

    # Get reversed commit list
    hashes_out, _, _ = run_git(repo_path, 'rev-list', '--reverse', 'HEAD')
    all_hashes = hashes_out.split('\n') if hashes_out else []

    for i in range(0, len(all_hashes), interval):
        if i >= len(all_hashes):
            break
        commit_hash = all_hashes[i]
        date_out, _, _ = run_git(repo_path, 'show', '-s', '--format=%ai', commit_hash)
        if not date_out:
            continue
        ym = date_out[:7]  # YYYY-MM

        # Count files at this commit
        files_out, _, _ = run_git(repo_path, 'ls-tree', '-r', '--name-only', commit_hash)
        total_files = 0
        if files_out:
            exclude = {'node_modules/', 'vendor/', '.git/', 'venv/', 'target/'}
            total_files = sum(
                1 for f in files_out.split('\n')
                if f and not any(f.startswith(e) for e in exclude)
            )

        # Contributors up to this date
        contrib_out, _, _ = run_git(repo_path, 'shortlog', '-sn', f'--before={date_out}')
        total_contributors = len(contrib_out.split('\n')) if contrib_out else 0

        timeline.append({
            'date': ym,
            'total_commits': i + 1,
            'total_files': total_files,
            'total_contributors': total_contributors,
        })

        if len(timeline) >= 25:
            break

    return timeline, total_commits


def get_total_authors(repo_path):
    out, _, _ = run_git(repo_path, 'shortlog', '-sn')
    if not out:
        return 1
    return len(out.split('\n'))


def count_current_files(repo_path):
    exclude = {'node_modules', 'vendor', '.git', 'venv', '.venv',
               'target', '__pycache__', 'dist', 'build', '.next', '.nuxt'}
    count = 0
    for dirpath, dirnames, filenames in os.walk(repo_path):
        dirnames[:] = [d for d in dirnames if d not in exclude]
        rel = os.path.relpath(dirpath, repo_path)
        parts = set(Path(rel).parts)
        if parts & exclude:
            continue
        count += len(filenames)
    return count


def main():
    args = parse_args()
    repo_path = args.repo_path

    is_valid, err = check_repo(repo_path)
    if not is_valid:
        print(json.dumps({'status': 'error', 'error': err}))
        sys.exit(1)

    if check_shallow(repo_path):
        print(json.dumps({
            'status': 'error',
            'error': 'Repository is a shallow clone (--depth=1). Git archaeology requires full history. Re-clone without --depth.',
        }))
        sys.exit(1)

    first = get_first_commit(repo_path)
    if not first:
        print(json.dumps({'status': 'error', 'error': 'Could not determine first commit.'}))
        sys.exit(1)

    milestones = get_milestones(repo_path)
    recent = get_recent_activity(repo_path, args.recent_days)
    timeline, total_commits = get_growth_timeline(repo_path)
    total_authors = get_total_authors(repo_path)
    file_count = count_current_files(repo_path)

    narrative = (
        f"This project began on {first['date']} when {first['author']} "
        f"made the first commit: \"{first['message']}\" — "
        f"just {first['files_changed']} file(s) and {first['lines_added']} line(s) of code. "
        f"Over {total_commits} commits by {total_authors} contributor(s), "
        f"it grew to {file_count} files. "
        f"In the last {args.recent_days} days, there have been {recent['commit_count']} commits."
    )

    output = {
        'status': 'success',
        'first_commit': first,
        'milestones': milestones,
        'recent_activity': recent,
        'stats': {
            'total_commits': total_commits,
            'total_contributors': total_authors,
            'current_file_count': file_count,
        },
        'growth_timeline': timeline,
        'narrative_summary': narrative,
    }
    print(json.dumps(output, ensure_ascii=False))


if __name__ == '__main__':
    main()
