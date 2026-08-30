import os
from datetime import datetime, timezone

from jinja2 import Environment, FileSystemLoader


def _counts(findings: list) -> dict:
    counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
    for f in findings:
        key = f.get('severity', 'LOW').lower()
        if key in counts:
            counts[key] += 1
    return counts


def render_markdown(findings: list, source_path: str, target_path: str) -> str:
    generated_at = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    counts = _counts(findings)
    total = len(findings)

    lines = [
        '# targetlint Report',
        '',
        f'**Source:** {source_path}',
        f'**Target:** {target_path}',
        f'**Date:** {generated_at}',
        f'**Findings:** {total} ({counts["critical"]} critical, {counts["high"]} high, '
        f'{counts["medium"]} medium, {counts["low"]} low)',
        '',
        '---',
    ]

    if not findings:
        lines.append('')
        lines.append('No constraint violations found for this target.')
        return '\n'.join(lines)

    severity_order = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']
    buckets = {sev: [f for f in findings if f.get('severity') == sev] for sev in severity_order}

    section_titles = {
        'CRITICAL': 'Critical Findings',
        'HIGH': 'High Findings',
        'MEDIUM': 'Medium Findings',
        'LOW': 'Low Findings',
    }

    for sev in severity_order:
        bucket = buckets[sev]
        if not bucket:
            continue
        lines.append('')
        lines.append(f'## {section_titles[sev]}')
        for f in bucket:
            lines.append('')
            lines.append(f'### [{f.get("severity", sev)}] {f.get("rule", "")}')
            lines.append(f'**Assumption:** {f.get("assumption", "")}')
            lines.append(f'**Conflict:** {f.get("conflict", "")}')
            lines.append(f'**Location:** {f.get("location", "")}')
            lines.append(f'**Recommendation:** {f.get("recommendation", "")}')

    return '\n'.join(lines)


def render_html(findings: list, source_path: str, target_path: str) -> str:
    generated_at = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    counts = _counts(findings)

    templates_dir = os.path.join(os.path.dirname(__file__), '..', 'templates')
    env = Environment(
        loader=FileSystemLoader(templates_dir),
        autoescape=True,
    )
    template = env.get_template('report.html.j2')
    return template.render(
        findings=findings,
        source_path=source_path,
        target_path=target_path,
        generated_at=generated_at,
        counts=counts,
    )
