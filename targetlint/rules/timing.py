import re
from typing import List

_BUSY_WAIT_RE = re.compile(r'\bfor\s*\(.*;\s*\w+\s*[<>]=?\s*(\d+)\s*;')
_CLOCK_COMMENT_RE = re.compile(r'(MHz|clock\s*speed|cpu\s*freq|mhz)', re.IGNORECASE)
_CLOCK_LITERAL_RE = re.compile(r'\b(8000000|16000000|48000000|72000000|168000000)\b')
_DELAY_FUNC_RE = re.compile(r'\b(delay_ms|delay_us|HAL_Delay|_delay_ms|_delay_us)\s*\(\s*(\d+)\s*\)')


def _is_comment(line: str) -> bool:
    s = line.strip()
    return s.startswith('//') or s.startswith('*') or s.startswith('/*')


def _check_busy_wait_clock(lines: List[str], target: dict) -> List[dict]:
    """Busy-wait loop with hardcoded count + clock-speed comment → MEDIUM."""
    clock_hz = target.get('clock_hz')
    findings = []
    for i, line in enumerate(lines, 1):
        if _is_comment(line):
            continue
        if _BUSY_WAIT_RE.search(line):
            window_start = max(0, i - 3)
            window_end = min(len(lines), i + 2)
            window = lines[window_start:window_end]
            if any(_CLOCK_COMMENT_RE.search(wl) for wl in window):
                m = _BUSY_WAIT_RE.search(line)
                assumed = m.group(1) if m else 'unknown'
                findings.append({
                    'severity': 'MEDIUM',
                    'rule': 'busy-wait-clock-assumption',
                    'location': f'line {i}',
                    'assumption': f'Busy-wait loop with iteration count {assumed} assumes a specific clock speed',
                    'conflict': f'Target clock_hz={clock_hz}; hardcoded delay will be wrong if clock differs',
                    'recommendation': 'Use a hardware timer or HAL delay function instead of a busy-wait calibrated to a fixed clock',
                })
    return findings


def _check_clock_literal(lines: List[str], target: dict) -> List[dict]:
    """Common clock-speed literal that does not match target clock_hz → HIGH."""
    clock_hz = target.get('clock_hz')
    findings = []
    seen: set = set()
    for i, line in enumerate(lines, 1):
        if _is_comment(line):
            continue
        for m in _CLOCK_LITERAL_RE.finditer(line):
            val = int(m.group(1))
            if clock_hz is not None and val == clock_hz:
                continue
            key = (i, val)
            if key in seen:
                continue
            seen.add(key)
            findings.append({
                'severity': 'HIGH',
                'rule': 'hardcoded-clock-literal',
                'location': f'line {i}',
                'assumption': f'Code assumes CPU clock is {val} Hz',
                'conflict': f'Target clock_hz={clock_hz}; literal {val} does not match',
                'recommendation': f'Replace the literal {val} with a macro derived from the target clock (e.g. F_CPU or SystemCoreClock)',
            })
    return findings


def _check_delay_magic(lines: List[str], target: dict) -> List[dict]:
    """delay_ms/delay_us with hardcoded magic number → MEDIUM."""
    findings = []
    for i, line in enumerate(lines, 1):
        if _is_comment(line):
            continue
        m = _DELAY_FUNC_RE.search(line)
        if m:
            func = m.group(1)
            val = m.group(2)
            findings.append({
                'severity': 'MEDIUM',
                'rule': 'delay-magic-number',
                'location': f'line {i}',
                'assumption': f'{func}({val}) encodes a timing assumption based on current clock speed',
                'conflict': 'Magic-number delays become incorrect when clock speed changes between targets',
                'recommendation': f'Define the delay as a named constant and document its relationship to clock speed; verify against target clock_hz={target.get("clock_hz")}',
            })
    return findings


def check(source_text: str, target: dict) -> list:
    lines = source_text.splitlines()
    findings = []
    findings.extend(_check_busy_wait_clock(lines, target))
    findings.extend(_check_clock_literal(lines, target))
    findings.extend(_check_delay_magic(lines, target))
    return findings
