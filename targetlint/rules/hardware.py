import re
from typing import List

_FLOAT_DECL_RE = re.compile(r'\bfloat\s+\w+')
_DOUBLE_DECL_RE = re.compile(r'\bdouble\s+\w+')
_SIZEOF_INT_RE = re.compile(r'sizeof\s*\(\s*int\s*\)\s*==\s*4')
_WORD32_COMMENT_RE = re.compile(r'(32.?bit|word\s*size\s*=\s*32|int\s*is\s*4\s*bytes)', re.IGNORECASE)
_ASM_RE = re.compile(r'\b(__asm__|asm)\s*\(|__asm__\s+volatile\s*\(')


def _is_comment(line: str) -> bool:
    s = line.strip()
    return s.startswith('//') or s.startswith('*') or s.startswith('/*')


def _check_float(lines: List[str], target: dict) -> List[dict]:
    """float declarations when has_fpu is false → HIGH."""
    if target.get('has_fpu', True):
        return []
    findings = []
    for i, line in enumerate(lines, 1):
        if _is_comment(line):
            continue
        if _FLOAT_DECL_RE.search(line):
            findings.append({
                'severity': 'HIGH',
                'rule': 'soft-float-usage',
                'location': f'line {i}',
                'assumption': 'Code uses float assuming hardware floating-point support',
                'conflict': 'Target profile sets has_fpu=false — float operations use slow software emulation',
                'recommendation': 'Replace float with fixed-point arithmetic (e.g. Q-format integers) or verify soft-float overhead is acceptable',
            })
    return findings


def _check_double(lines: List[str], target: dict) -> List[dict]:
    """double declarations when has_fpu is false → HIGH."""
    if target.get('has_fpu', True):
        return []
    findings = []
    for i, line in enumerate(lines, 1):
        if _is_comment(line):
            continue
        if _DOUBLE_DECL_RE.search(line):
            findings.append({
                'severity': 'HIGH',
                'rule': 'soft-double-usage',
                'location': f'line {i}',
                'assumption': 'Code uses double assuming hardware floating-point support',
                'conflict': 'Target profile sets has_fpu=false — double operations use slow software emulation and double precision may be 8 bytes',
                'recommendation': 'Replace double with fixed-point arithmetic or use float if precision allows; verify soft-float overhead',
            })
    return findings


def _check_word_size(lines: List[str], target: dict) -> List[dict]:
    """sizeof(int)==4 or 32-bit word assumption when target word_size_bits differs → MEDIUM."""
    word_size = target.get('word_size_bits', 32)
    if word_size == 32:
        return []
    findings = []
    for i, line in enumerate(lines, 1):
        if _SIZEOF_INT_RE.search(line) or _WORD32_COMMENT_RE.search(line):
            findings.append({
                'severity': 'MEDIUM',
                'rule': 'word-size-assumption',
                'location': f'line {i}',
                'assumption': 'Code assumes a 32-bit word size (sizeof(int)==4)',
                'conflict': f'Target word_size_bits={word_size}; int may not be 4 bytes',
                'recommendation': 'Use stdint.h fixed-width types (uint32_t, int32_t) instead of relying on sizeof(int)==4',
            })
    return findings


def _check_asm(lines: List[str], target: dict) -> List[dict]:
    """Inline assembly block → LOW (manual review, arch-specific)."""
    findings = []
    for i, line in enumerate(lines, 1):
        if _is_comment(line):
            continue
        if _ASM_RE.search(line):
            arch = target.get('arch', 'unknown')
            findings.append({
                'severity': 'LOW',
                'rule': 'inline-asm',
                'location': f'line {i}',
                'assumption': 'Inline assembly assumes a specific CPU architecture and ABI',
                'conflict': f'Target arch={arch}; inline assembly may not be portable or correct for this target',
                'recommendation': 'Review inline assembly for compatibility with target arch; prefer intrinsics or CMSIS functions where available',
            })
    return findings


def check(source_text: str, target: dict) -> list:
    lines = source_text.splitlines()
    findings = []
    findings.extend(_check_float(lines, target))
    findings.extend(_check_double(lines, target))
    findings.extend(_check_word_size(lines, target))
    findings.extend(_check_asm(lines, target))
    return findings
