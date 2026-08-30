import argparse
import os
import sys

from targetlint import loader, analyser, reporter


def main():
    parser = argparse.ArgumentParser(
        prog='targetlint',
        description='Target-aware static analysis for embedded C firmware',
    )
    parser.add_argument('--source', required=True, help='Path to C source file')
    parser.add_argument('--target', required=True, help='Path to YAML target profile')
    parser.add_argument(
        '--output',
        default=None,
        help='Output markdown report path (default: <source>-<target>-report.md)',
    )
    parser.add_argument(
        '--html',
        action='store_true',
        help='Also write an HTML report alongside the markdown report',
    )
    args = parser.parse_args()

    # Derive default output path
    if args.output is None:
        source_stem = os.path.splitext(os.path.basename(args.source))[0]
        target_stem = os.path.splitext(os.path.basename(args.target))[0]
        args.output = f'{source_stem}-{target_stem}-report.md'

    try:
        source_text = loader.load_source(args.source)
        target = loader.load_target(args.target)
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f'Unexpected error: {exc}', file=sys.stderr)
        sys.exit(1)

    try:
        findings = analyser.run(source_text, target)

        md_report = reporter.render_markdown(findings, args.source, args.target)
        with open(args.output, 'w', encoding='utf-8') as fh:
            fh.write(md_report)

        if args.html:
            html_path = os.path.splitext(args.output)[0] + '.html'
            html_report = reporter.render_html(findings, args.source, args.target)
            with open(html_path, 'w', encoding='utf-8') as fh:
                fh.write(html_report)

    except Exception as exc:
        print(f'Unexpected error: {exc}', file=sys.stderr)
        sys.exit(1)

    counts = reporter._counts(findings)
    total = len(findings)
    print('targetlint complete')
    print(
        f'{total} findings ({counts["critical"]} critical, {counts["high"]} high, '
        f'{counts["medium"]} medium, {counts["low"]} low)'
    )
    print(f'Report: {args.output}')
