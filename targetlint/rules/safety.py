import re
from typing import List, Tuple

_FUNC_DEF_RE = re.compile(r'^[\w\s\*]+\b(\w+)\s*\([^;]*\)\s*\{?\s*$')
_RETURN_RE = re.compile(r'\breturn\b')
_GOTO_RE = re.compile(r'\bgoto\b')
_LOOP_RE = re.compile(r'\b(for|while)\s*\(')
_WATCHDOG_RE = re.compile(
    r'\b(WDT_Reset|watchdog_reset|IWDG_ReloadCounter|HAL_IWDG_Refresh|'
    r'wdt_reset|kick_watchdog|watchdog_kick)\s*\('
)
_SKIP_KEYWORDS = frozenset({'if', 'for', 'while', 'switch', 'else', 'do'})


def _is_comment(line: str) -> bool:
    s = line.strip()
    return s.startswith('//') or s.startswith('*') or s.startswith('/*')


def _extract_functions(lines: List[str]) -> List[Tuple[str, int, List[str]]]:
    """Return list of (func_name, start_line_1based, body_lines)."""
    functions = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = _FUNC_DEF_RE.match(line.rstrip())
        if m:
            func_name = m.group(1)
            if func_name in _SKIP_KEYWORDS:
                i += 1
                continue
            brace_line = i
            if '{' not in line:
                for j in range(i + 1, min(i + 4, len(lines))):
                    if '{' in lines[j]:
                        brace_line = j
                        break
            depth = 0
            body: List[str] = []
            found_brace = False
            for j in range(brace_line, len(lines)):
                body.append(lines[j])
                depth += lines[j].count('{') - lines[j].count('}')
                if '{' in lines[j]:
                    found_brace = True
                if found_brace and depth <= 0:
                    break
            if found_brace:
                functions.append((func_name, i + 1, body))
            i = brace_line + max(1, len(body))
            continue
        i += 1
    return functions


def _check_recursion(lines: List[str], target: dict) -> List[dict]:
    safety_critical = target.get('safety_critical', False)
    functions = _extract_functions(lines)
    findings = []
    for func_name, start_line, body in functions:
        call_re = re.compile(r'\b' + re.escape(func_name) + r'\s*\(')
        for j, bline in enumerate(body):
            if j == 0 or _is_comment(bline):
                continue
            if call_re.search(bline):
                severity = 'CRITICAL' if safety_critical else 'MEDIUM'
                findings.append({
                    'severity': severity,
                    'rule': 'recursive-function',
                    'location': f'line {start_line + j}',
                    'assumption': f"Function '{func_name}' assumes unbounded stack depth is available for recursion",
                    'conflict': (
                        'safety_critical=true; recursive functions violate MISRA-C Rule 17.2 and risk stack overflow'
                        if safety_critical else
                        'Recursive functions risk stack overflow on constrained targets'
                    ),
                    'recommendation': 'Rewrite using an explicit stack or iterative approach to bound stack usage',
                })
                break
    return findings


def _check_watchdog(lines: List[str], target: dict) -> List[dict]:
    watchdog_ms = target.get('watchdog_timeout_ms')
    if not watchdog_ms:
        return []
    findings = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if _is_comment(line):
            i += 1
            continue
        if _LOOP_RE.search(line):
            loop_start = i
            depth = 0
            body: List[str] = []
            found_brace = False
            for j in range(i, min(i + 200, len(lines))):
                body.append(lines[j])
                depth += lines[j].count('{') - lines[j].count('}')
                if '{' in lines[j]:
                    found_brace = True
                if found_brace and depth <= 0:
                    break
            if found_brace and len(body) > 3:
                if not any(_WATCHDOG_RE.search(bl) for bl in body):
                    findings.append({
                        'severity': 'HIGH',
                        'rule': 'watchdog-not-kicked',
                        'location': f'line {loop_start + 1}',
                        'assumption': 'Loop assumes it completes before watchdog timeout',
                        'conflict': f'Target watchdog_timeout_ms={watchdog_ms}; no watchdog kick found inside loop body',
                        'recommendation': 'Add a watchdog reset call inside the loop body to prevent unintended resets',
                    })
            i += max(1, len(body))
            continue
        i += 1
    return findings


def _check_multiple_returns(lines: List[str], target: dict) -> List[dict]:
    if not target.get('safety_critical', False):
        return []
    functions = _extract_functions(lines)
    findings = []
    for func_name, start_line, body in functions:
        return_lines = [
            start_line + j
            for j, bline in enumerate(body)
            if not _is_comment(bline) and _RETURN_RE.search(bline)
        ]
        if len(return_lines) > 1:
            findings.append({
                'severity': 'LOW',
                'rule': 'multiple-return-points',
                'location': f'line {return_lines[0]}',
                'assumption': f"Function '{func_name}' uses multiple return points for control flow",
                'conflict': 'safety_critical=true; MISRA-C Rule 15.5 requires a single exit point per function',
                'recommendation': f"Refactor '{func_name}' to have a single return statement at the end",
            })
    return findings


def _check_goto(lines: List[str], target: dict) -> List[dict]:
    if not target.get('safety_critical', False):
        return []
    findings = []
    for i, line in enumerate(lines, 1):
        if _is_comment(line):
            continue
        if _GOTO_RE.search(line):
            findings.append({
                'severity': 'MEDIUM',
                'rule': 'goto-in-safety-critical',
                'location': f'line {i}',
                'assumption': 'Code uses goto for control flow',
                'conflict': 'safety_critical=true; goto is prohibited by MISRA-C Rule 15.1',
                'recommendation': 'Replace goto with structured control flow (break, return, or refactored loops)',
            })
    return findings


def check(source_text: str, target: dict) -> list:
    lines = source_text.splitlines()
    findings = []
    findings.extend(_check_recursion(lines, target))
    findings.extend(_check_watchdog(lines, target))
    findings.extend(_check_multiple_returns(lines, target))
    findings.extend(_check_goto(lines, target))
    return findings
