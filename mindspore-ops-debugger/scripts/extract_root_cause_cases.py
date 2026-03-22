#!/usr/bin/env python3
"""
Extract structured root cause analysis from GitCode issue files.
Parses "Appearance & Root Cause" section and converts to skill case studies format.
"""

import os
import re
import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional


@dataclass
class RootCauseCase:
    issue_id: str
    title: str
    problem: str
    root_cause: str
    fix_solution: str
    fix_pr: str
    introduction_type: str  # 引入类型
    issue_type: str
    labels: List[str]
    backend: str
    status: str


def parse_issue_file(filepath: str) -> Optional[RootCauseCase]:
    """Parse a GitCode issue file and extract Appearance & Root Cause section."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check if has Appearance & Root Cause section
    if 'Appearance & Root Cause' not in content:
        return None

    # Extract issue ID
    filename = os.path.basename(filepath)
    issue_id = ''
    match = re.search(r'issues-(\d+)\.md', filename)
    if match:
        issue_id = f"#{match.group(1)}"

    # Extract title (first line)
    title = ''
    title_match = re.search(r'^#\s*\[.*?\]:\s*(.+?)\n', content)
    if title_match:
        title = title_match.group(1).strip()
    else:
        title_match = re.search(r'^#\s*(.+?)\n', content)
        if title_match:
            title = title_match.group(1).strip()

    # Extract Appearance & Root Cause section
    arc_match = re.search(
        r'Appearance & Root Cause\s*\n\s*\n?'
        r'(.*?)'
        r'(?:Fix Solution|## |$)',
        content, re.DOTALL | re.IGNORECASE
    )
    if not arc_match:
        return None

    arc_content = arc_match.group(1).strip()

    # Parse problem description
    problem = ''
    problem_match = re.search(r'问题[:：]\s*(.+?)(?:\n|$)', arc_content)
    if problem_match:
        problem = problem_match.group(1).strip()

    # Parse root cause
    root_cause = ''
    rc_match = re.search(r'根因[:：]\s*(.+?)(?:\n\s*\n|\n[A-Z]|Fix Solution|$)', arc_content, re.DOTALL)
    if rc_match:
        root_cause = rc_match.group(1).strip()
        # Clean up the root cause (remove numbered list formatting)
        root_cause = re.sub(r'\n\s*\d+\s*[、.]\s*', '; ', root_cause)
        root_cause = root_cause.replace('\n', ' ')

    # Extract Fix Solution section
    fix_solution = ''
    fs_match = re.search(
        r'Fix Solution\s*\n\s*\n?'
        r'(.*?)'
        r'(?:Fix Description|Self-test|## |$)',
        content, re.DOTALL | re.IGNORECASE
    )
    if fs_match:
        fix_solution = fs_match.group(1).strip()
        fix_solution = re.sub(r'\n\s*\d+\s*[、.]\s*', '; ', fix_solution)
        fix_solution = fix_solution.replace('\n', ' ')

    # Extract Fix PR
    fix_pr = ''
    pr_match = re.search(r'(?:关联PR|Fix PR|PR合入)[:：]?\s*.*?pull[s/]?(\d+)', content, re.IGNORECASE)
    if pr_match:
        fix_pr = f"!{pr_match.group(1)}"

    # Extract introduction type (引入类型)
    intro_type = ''
    it_match = re.search(r'引入类型[:：]\s*(.+?)(?:\n|$)', content)
    if it_match:
        intro_type = it_match.group(1).strip()

    # Extract issue type
    issue_type = ''
    type_match = re.search(r'##### Issue 类型\s*\n\s*\n([^\n]+)', content)
    if type_match:
        issue_type = type_match.group(1).strip()

    # Extract labels
    labels = []
    label_match = re.search(r'##### Label\s*\n\s*\n([^#]+)', content)
    if label_match:
        labels_text = label_match.group(1).strip()
        if labels_text and '暂未设置' not in labels_text:
            labels = [l.strip() for l in re.split(r'[\n,]+', labels_text) if l.strip()]

    # Extract backend
    backend = ''
    backend_match = re.search(r'##### 问题后端类型\s*\n\s*```\s*\n([^`]+)', content)
    if backend_match:
        backend = backend_match.group(1).strip()

    # Extract status
    status = ''
    status_match = re.search(r'##### Issue 状态\s*\n\s*\n([^\n]+)', content)
    if status_match:
        status = status_match.group(1).strip()

    # Skip if missing essential fields
    if not root_cause or not problem:
        return None

    return RootCauseCase(
        issue_id=issue_id,
        title=title,
        problem=problem,
        root_cause=root_cause,
        fix_solution=fix_solution,
        fix_pr=fix_pr,
        introduction_type=intro_type,
        issue_type=issue_type,
        labels=labels,
        backend=backend,
        status=status
    )


def categorize_case(case: RootCauseCase) -> str:
    """Categorize case based on keywords."""
    text = f"{case.title} {case.problem} {case.root_cause} {case.labels}".lower()

    if any(k in text for k in ['精度', 'precision', 'allclose', 'diff']):
        return '精度/数值'
    if any(k in text for k in ['shape', '维度', 'broadcast']):
        return 'Shape推导'
    if any(k in text for k in ['bprop', '梯度', 'grad', 'backward', '反向']):
        return '反向传播'
    if any(k in text for k in ['kernel', '算子实现', '算子错误']):
        return 'Kernel实现'
    if any(k in text for k in ['编译', 'compile', 'graph', '图']):
        return '编译器/IR'
    if any(k in text for k in ['api', '接口', '参数']):
        return 'API/签名'
    if any(k in text for k in ['内存', 'memory', 'oom']):
        return '运行时'
    if any(k in text for k in ['性能', 'performance', 'slow']):
        return '性能退化'

    return '其他'


def generate_case_id(category: str, index: int) -> str:
    """Generate case ID like CS-021."""
    category_map = {
        '精度/数值': 'CS',
        'API/签名': 'API',
        'Shape推导': 'SP',
        '编译器/IR': 'IR',
        'Kernel实现': 'KR',
        '反向传播': 'BP',
        '运行时': 'RT',
        '性能退化': 'PF',
        '其他': 'OT'
    }
    prefix = category_map.get(category, 'OT')
    return f"{prefix}-{index:03d}"


def generate_markdown_cases(cases: List[RootCauseCase]) -> str:
    """Generate markdown content for case studies."""
    # Group by category
    categories = {}
    for case in cases:
        cat = categorize_case(case)
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(case)

    # Generate markdown
    output = []
    output.append("# 新增案例研究（来自 GitCode org-issues）\n")
    output.append("基于最新 GitCode issue 文件提取的结构化根因分析案例。\n")

    cat_order = ['精度/数值', '反向传播', 'Shape推导', 'Kernel实现', '编译器/IR', 'API/签名', '运行时', '性能退化', '其他']

    index_counters = {}

    for cat in cat_order:
        if cat not in categories:
            continue

        output.append(f"\n## {cat}\n")

        for case in categories[cat]:
            # Get next index for this category
            idx = index_counters.get(cat, 21)  # Start from 021
            case_id = generate_case_id(cat, idx)
            index_counters[cat] = idx + 1

            output.append(f"\n### Case {case_id}: {case.title} ({case.issue_id})\n")

            # Create table
            output.append("\n| 字段 | 内容 |")
            output.append("|------|------|")
            output.append(f"| 问题 | {case.problem} |")
            output.append(f"| 根因 | {case.root_cause} |")
            if case.fix_solution:
                output.append(f"| 修复 | {case.fix_solution} |")
            if case.fix_pr:
                output.append(f"| Fix PR | [{case.fix_pr}](https://gitee.com/mindspore/mindspore/pulls/{case.fix_pr.lstrip('!')}) |")
            if case.introduction_type:
                output.append(f"| 引入类型 | {case.introduction_type} |")
            if case.backend:
                output.append(f"| 后端 | {case.backend} |")
            output.append(f"| 状态 | {case.status} |")

            # Key lessons
            output.append(f"\n**关键教训**: {case.root_cause[:100]}..." if len(case.root_cause) > 100 else f"\n**关键教训**: {case.root_cause}")
            output.append("")

    return '\n'.join(output)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', '-i', default='/Users/claw/work/debug/mindspore/data/md_files/gitcode/issues')
    parser.add_argument('--output', '-o', default='/Users/claw/work/skills/mindspore-ops-debugger/data/extracted_cases.md')
    parser.add_argument('--json', '-j', default='/Users/claw/work/skills/mindspore-ops-debugger/data/extracted_cases.json')
    args = parser.parse_args()

    # Find all issue files
    md_files = list(Path(args.input).glob('*.md'))
    print(f"Found {len(md_files)} issue files")

    cases = []
    for filepath in md_files:
        try:
            case = parse_issue_file(str(filepath))
            if case:
                cases.append(case)
        except Exception as e:
            print(f"Error parsing {filepath}: {e}")

    print(f"Extracted {len(cases)} cases with root cause analysis")

    # Generate markdown
    markdown = generate_markdown_cases(cases)

    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(markdown)

    # Save JSON
    with open(args.json, 'w', encoding='utf-8') as f:
        json.dump([asdict(c) for c in cases], f, ensure_ascii=False, indent=2)

    print(f"Markdown report: {args.output}")
    print(f"JSON data: {args.json}")

    # Print statistics
    categories = {}
    for case in cases:
        cat = categorize_case(case)
        categories[cat] = categories.get(cat, 0) + 1

    print("\nCategories:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")


if __name__ == '__main__':
    main()
