import re
from typing import List

_PRINTF_RE = re.compile(r'\b(printf|fprintf|sprintf)\s*\(')
_INCLUDE_STDIO_RE = re.compile(r'#\s*include\s*[<"]\s*stdio\.h\s*[>"]')
_INCLUDE_STDLIB_RE = re.compile(r'#\s*include\s*[<"]\s*stdlib\.h\s*[>"]')
_INCLUDE_STRING_RE = re.compile(r'#\s*include\s*[<"]\s*string\.h\s*[>"]')
_UNSAFE_STR_RE = re.compile(r'\b(strcpy|strcat)\s*\(')


def _is_comment(line: str) -> bool:
    s = line.strip()
    return s.startswith('//') or s.startswith('*') or s.startswith('/*')


def _check_include_stdio(lines: List[str], target: dict) -> List[dict]:
    if target.get('has_stdlib', True):
        return []
    findings = []
    for i, line in enumerate(lines, 1):
        if _is_comment(line):
            continue
        if _INCLUDE_STDIO_RE.search(line):
            findings.append({
                'severity': 'CRITICAL',
                'rule': 'stdlib-include-stdio',
                'location': f'line {i}',
                'assumption': 'Code includes <stdio.h> assuming the C standard library is available',
                'conflict': 'Target profile sets has_stdlib=false — <stdio.h> is not available',
                'recommendation': 'Remove #include <stdio.h> and all stdio function calls',
            })
    return findings


def _check_include_stdlib(lines: List[str], target: dict) -> List[dict]:
    if target.get('has_stdlib', True):
        return []
    findings = []
    for i, line in enumerate(lines, 1):
        if _is_comment(line):
            continue
        if _INCLUDE_STDLIB_RE.search(line):
            findings.append({
                'severity': 'CRITICAL',
                'rule': 'stdlib-include-stdlib',
                'location': f'line {i}',
                'assumption': 'Code includes <stdlib.h> assuming the C standard library is available',
                'conflict': 'Target profile sets has_stdlib=false — <stdlib.h> is not available',
                'recommendation': 'Remove #include <stdlib.h> and replace any stdlib functions with bare-metal equivalents',
            })
    return findings


def _check_include_string(lines: List[str], target: dict) -> List[dict]:
    if target.get('has_stdlib', True):
        return []
    findings = []
    for i, line in enumerate(lines, 1):
        if _is_comment(line):
            continue
        if _INCLUDE_STRING_RE.search(line):
            findings.append({
                'severity': 'HIGH',
                'rule': 'stdlib-include-string',
                'location': f'line {i}',
                'assumption': 'Code includes <string.h> assuming the C standard library is available',
                'conflict': 'Target profile sets has_stdlib=false — <string.h> may not be available',
                'recommendation': 'Remove #include <string.h> and implement only the specific string operations needed',
            })
    return findings


def _check_printf(lines: List[str], target: dict) -> List[dict]:
    if target.get('has_stdlib', True):
        return []
    findings = []
    for i, line in enumerate(lines, 1):
        if _is_comment(line):
            continue
        m = _PRINTF_RE.search(line)
        if m:
            func = m.group(1)
            findings.append({
                'severity': 'CRITICAL',
                'rule': 'stdlib-printf-unavailable',
                'location': f'line {i}',
                'assumption': f'Code calls {func}() assuming the C standard library is available',
                'conflict': 'Target profile sets has_stdlib=false — libc is not linked',
                'recommendation': f'Remove {func}() call; implement a minimal UART output function or remove logging entirely',
            })
    return findings


def _check_unsafe_str(lines: List[str], target: dict) -> List[dict]:
    findings = []
    for i, line in enumerate(lines, 1):
        if _is_comment(line):
            continue
        m = _UNSAFE_STR_RE.search(line)
        if m:
            func = m.group(1)
            findings.append({
                'severity': 'HIGH',
                'rule': 'unsafe-string-function',
                'location': f'line {i}',
                'assumption': f'Code uses {func}() assuming destination buffer is always large enough',
                'conflict': f'{func}() performs no bounds checking and can cause buffer overflows on any target',
                'recommendation': f'Replace {func}() with {func[:-1]}n() or a bounds-checked alternative',
            })
    return findings


def check(source_text: str, target: dict) -> list:
    lines = source_text.splitlines()
    findings = []
    findings.extend(_check_include_stdio(lines, target))
    findings.extend(_check_include_stdlib(lines, target))
    findings.extend(_check_include_string(lines, target))
    findings.extend(_check_printf(lines, target))
    findings.extend(_check_unsafe_str(lines, target))
    return findings
