#!/usr/bin/env python3
"""
Extract valuable debugging experience from new md_files.
Analyzes GitCode issue files and extracts patterns for skill enrichment.
"""

import os
import re
import json
from pathlib import Path
from collections import Counter
import argparse


def parse_issue_file(filepath):
    """Parse a single GitCode issue md file and extract key information."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    result = {
        'issue_id': '',
        'title': '',
        'issue_type': '',
        'status': '',
        'labels': [],
        'related_prs': [],
        'has_root_cause': False,
        'has_stack_trace': False,
        'error_keywords': [],
        'backend_type': [],  # Ascend, GPU, CPU
        'component': ''
    }

    # Extract issue ID from filename
    filename = os.path.basename(filepath)
    match = re.search(r'issues-(\d+)\.md', filename)
    if match:
        result['issue_id'] = match.group(1)

    # Extract title (first line usually)
    title_match = re.search(r'^#\s+(.+?)\n', content)
    if title_match:
        result['title'] = title_match.group(1).strip()

    # Extract issue type
    type_match = re.search(r'##### Issue 类型\s*\n\s*\n([^\n]+)', content)
    if type_match:
        result['issue_type'] = type_match.group(1).strip()

    # Extract status
    status_match = re.search(r'##### Issue 状态\s*\n\s*\n([^\n]+)', content)
    if status_match:
        result['status'] = status_match.group(1).strip()

    # Extract labels
    label_match = re.search(r'##### Label\s*\n\s*\n([^#]+)', content)
    if label_match:
        labels_text = label_match.group(1).strip()
        # Labels are often separated by newlines or commas
        labels = [l.strip() for l in re.split(r'[\n,]+', labels_text) if l.strip() and l.strip() not in ['暂无', '暂未设置 Label']]
        result['labels'] = labels

    # Extract related PRs
    pr_matches = re.findall(r'Pull Request\s*!?(\d+)', content)
    if pr_matches:
        result['related_prs'] = pr_matches

    # Check for root cause indicators
    root_cause_patterns = [
        r'根因',
        r'Root Cause',
        r'Appearance & Root Cause',
        r'问题原因',
        r'根本原因',
        r'原因分析'
    ]
    for pattern in root_cause_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            result['has_root_cause'] = True
            break

    # Check for stack trace / error logs
    stack_patterns = [
        r'```\s*\n.*?(?:Error|Exception|Traceback)',
        r'RuntimeError',
        r'ValueError',
        r'TypeError',
        r'KeyError',
        r'IndexError',
        r'\[ERROR\]',
        r'\[FATAL\]',
        r'E\d{4}:\d{2}:\d{2}'  # CANN error format
    ]
    for pattern in stack_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            result['has_stack_trace'] = True
            break

    # Extract error keywords
    error_keywords = {
        '精度': r'精度|precision|allclose|diff|偏差',
        'shape': r'shape|维度|broadcast',
        '内存': r'内存|memory|OOM|malloc|free',
        '算子': r'算子|operator|kernel|acl|aclnn',
        '编译': r'编译|compile|graph|编译器',
        '梯度': r'梯度|gradient|grad|bprop',
        'dtype': r'dtype|类型|float16|float32|int32',
        '性能': r'性能|performance|slow|latency',
        '死锁': r'死锁|deadlock|hang|卡死',
        '崩溃': r'崩溃|crash|core dump|段错误'
    }
    for keyword, pattern in error_keywords.items():
        if re.search(pattern, content, re.IGNORECASE):
            result['error_keywords'].append(keyword)

    # Extract backend type
    backend_patterns = {
        'Ascend': r'Ascend|910|CANN|NPU',
        'GPU': r'GPU|CUDA',
        'CPU': r'CPU(?!\w)'
    }
    for backend, pattern in backend_patterns.items():
        if re.search(pattern, content):
            result['backend_type'].append(backend)

    return result


def analyze_issues(directory, output_dir):
    """Analyze all issue files in directory."""
    md_files = list(Path(directory).rglob('*.md'))
    print(f"Found {len(md_files)} markdown files")

    all_issues = []
    labels_counter = Counter()
    type_counter = Counter()
    keyword_counter = Counter()
    backend_counter = Counter()

    for i, filepath in enumerate(md_files):
        if i % 1000 == 0:
            print(f"Processed {i}/{len(md_files)} files...")

        try:
            issue = parse_issue_file(filepath)
            all_issues.append(issue)

            # Update counters
            labels_counter.update(issue['labels'])
            type_counter.update([issue['issue_type']])
            keyword_counter.update(issue['error_keywords'])
            backend_counter.update(issue['backend_type'])
        except Exception as e:
            print(f"Error processing {filepath}: {e}")

    # Generate statistics
    stats = {
        'total_files': len(md_files),
        'parsed_issues': len(all_issues),
        'with_root_cause': sum(1 for i in all_issues if i['has_root_cause']),
        'with_stack_trace': sum(1 for i in all_issues if i['has_stack_trace']),
        'top_labels': dict(labels_counter.most_common(50)),
        'issue_types': dict(type_counter),
        'error_keywords': dict(keyword_counter),
        'backend_distribution': dict(backend_counter)
    }

    # Save results
    os.makedirs(output_dir, exist_ok=True)

    with open(os.path.join(output_dir, 'all_issues.json'), 'w', encoding='utf-8') as f:
        json.dump(all_issues, f, ensure_ascii=False, indent=2)

    with open(os.path.join(output_dir, 'statistics.json'), 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    # Generate markdown report
    report_path = os.path.join(output_dir, 'analysis_report.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# GitCode Issues Analysis Report\n\n")
        f.write(f"## Overview\n\n")
        f.write(f"- Total files analyzed: {stats['total_files']}\n")
        f.write(f"- Successfully parsed: {stats['parsed_issues']}\n")
        f.write(f"- With root cause analysis: {stats['with_root_cause']}\n")
        f.write(f"- With stack trace/error log: {stats['with_stack_trace']}\n\n")

        f.write("## Issue Types Distribution\n\n")
        f.write("| Type | Count |\n|------|-------|\n")
        for t, count in type_counter.most_common():
            f.write(f"| {t} | {count} |\n")

        f.write("\n## Top Labels (Categories)\n\n")
        f.write("| Label | Count |\n|-------|-------|\n")
        for label, count in labels_counter.most_common(30):
            f.write(f"| {label} | {count} |\n")

        f.write("\n## Error Keywords Distribution\n\n")
        f.write("| Keyword | Count |\n|---------|-------|\n")
        for kw, count in keyword_counter.most_common():
            f.write(f"| {kw} | {count} |\n")

        f.write("\n## Backend Distribution\n\n")
        f.write("| Backend | Count |\n|---------|-------|\n")
        for be, count in backend_counter.most_common():
            f.write(f"| {be} | {count} |\n")

    print(f"\nAnalysis complete. Results saved to {output_dir}")
    print(f"Report: {report_path}")
    return stats


def extract_detailed_cases(directory, output_file, min_quality_score=2):
    """
    Extract high-quality cases with root cause analysis.
    Quality score based on: has_root_cause + has_stack_trace + has_pr + keywords count
    """
    md_files = list(Path(directory).rglob('*.md'))
    high_quality_cases = []

    for filepath in md_files:
        try:
            issue = parse_issue_file(filepath)
            # Calculate quality score
            score = 0
            if issue['has_root_cause']:
                score += 2
            if issue['has_stack_trace']:
                score += 1
            if issue['related_prs']:
                score += 1
            score += min(len(issue['error_keywords']), 2)

            if score >= min_quality_score:
                issue['quality_score'] = score
                # Read full content for high-quality cases
                with open(filepath, 'r', encoding='utf-8') as f:
                    issue['full_content'] = f.read()[:5000]  # First 5000 chars
                high_quality_cases.append(issue)
        except Exception as e:
            continue

    # Sort by quality score
    high_quality_cases.sort(key=lambda x: x['quality_score'], reverse=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(high_quality_cases, f, ensure_ascii=False, indent=2)

    print(f"Extracted {len(high_quality_cases)} high-quality cases to {output_file}")
    return high_quality_cases


def main():
    parser = argparse.ArgumentParser(description='Analyze GitCode issue files')
    parser.add_argument('--input', '-i', default='/Users/claw/work/debug/mindspore/data/md_files/gitcode/task',
                        help='Input directory containing md files')
    parser.add_argument('--output', '-o', default='/Users/claw/work/skills/mindspore-ops-debugger/data/extracted',
                        help='Output directory for analysis results')
    parser.add_argument('--extract-quality', '-q', action='store_true',
                        help='Extract high-quality cases with detailed content')

    args = parser.parse_args()

    stats = analyze_issues(args.input, args.output)

    if args.extract_quality:
        extract_detailed_cases(
            args.input,
            os.path.join(args.output, 'high_quality_cases.json')
        )


if __name__ == '__main__':
    main()
