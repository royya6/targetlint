import re
from typing import List

_ALLOC_RE = re.compile(r'\b(malloc|calloc|realloc)\s*\(')
_MALLOC_ASSIGN_RE = re.compile(r'(\w+)\s*=\s*malloc\s*\(')
_LOCAL_ARRAY_RE = re.compile(r'\b\w+\s+\w+\s*\[(\d+)\]')

_ELEM_SIZES = {'int': 4, 'long': 4, 'uint32_t': 4, 'int32_t': 4,
               'float': 4, 'double': 8, 'uint16_t': 2, 'int16_t': 2}


def _is_comment(line: str) -> bool:
    s = line.strip()
    return s.startswith('//') or s.startswith('*') or s.startswith('/*')


def _array_bytes(line: str, count: int) -> int:
    m = re.search(r'\b(int|long|uint32_t|int32_t|float|double|uint16_t|int16_t)\b', line)
    return count * (_ELEM_SIZES.get(m.group(1), 1) if m else 1)


def _check_heap_alloc(lines: List[str], target: dict) -> List[dict]:
    if target.get('has_heap', True):
        return []
    findings = []
    for i, line in enumerate(lines, 1):
        if _is_comment(line):
            continue
        m = _ALLOC_RE.search(line)
        if m:
            func = m.group(1)
            findings.append({
                'severity': 'CRITICAL',
                'rule': 'heap-unavailable',
                'location': f'line {i}',
                'assumption': f'Code calls {func}() assuming a heap is available',
                'conflict': 'Target profile sets has_heap=false — no heap allocator exists',
                'recommendation': f'Replace {func}() with static allocation or a fixed-size memory pool',
            })
    return findings


def _check_malloc_null(lines: List[str], target: dict) -> List[dict]:
    findings = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if _is_comment(line):
            i += 1
            continue
        m = _MALLOC_ASSIGN_RE.search(line)
        if m:
            var = m.group(1)
            window = lines[i:min(i + 6, len(lines))]
            null_pattern = re.compile(
                r'\bif\s*\(\s*!' + re.escape(var) + r'\b'
                r'|\bif\s*\(\s*' + re.escape(var) + r'\s*==\s*NULL'
                r'|\bif\s*\(\s*NULL\s*==\s*' + re.escape(var) + r'\b'
                r'|\bif\s*\(\s*' + re.escape(var) + r'\s*!=\s*NULL'
            )
            if not any(null_pattern.search(wl) for wl in window):
                findings.append({
                    'severity': 'HIGH',
                    'rule': 'malloc-no-null-check',
                    'location': f'line {i + 1}',
                    'assumption': f"Return value of malloc assigned to '{var}' is assumed non-NULL",
                    'conflict': 'malloc() can return NULL on allocation failure; return value is not checked',
                    'recommendation': f"Check '{var}' for NULL immediately after malloc() and handle the failure",
                })
        i += 1
    return findings


def _check_large_local_array(lines: List[str], target: dict) -> List[dict]:
    stack_bytes = target.get('stack_bytes')
    if not stack_bytes:
        return []
    threshold = stack_bytes * 0.1
    findings = []
    for i, line in enumerate(lines, 1):
        if _is_comment(line):
            continue
        m = _LOCAL_ARRAY_RE.search(line)
        if m:
            nbytes = _array_bytes(line, int(m.group(1)))
            if nbytes > threshold:
                findings.append({
                    'severity': 'HIGH',
                    'rule': 'large-local-array',
                    'location': f'line {i}',
                    'assumption': f'Local array of ~{nbytes} bytes fits on the stack',
                    'conflict': f'Target stack_bytes={stack_bytes}; array consumes >{threshold:.0f} bytes (>10%)',
                    'recommendation': 'Reduce array size, use static storage, or allocate from a memory pool',
                })
    return findings


def _check_stack_overflow(lines: List[str], target: dict) -> List[dict]:
    stack_bytes = target.get('stack_bytes')
    if not stack_bytes:
        return []
    total = sum(
        _array_bytes(line, int(m.group(1)))
        for line in lines
        if not _is_comment(line)
        for m in [_LOCAL_ARRAY_RE.search(line)]
        if m
    )
    if total > stack_bytes:
        return [{
            'severity': 'CRITICAL',
            'rule': 'stack-overflow-risk',
            'location': 'global',
            'assumption': f'Total estimated local array allocation (~{total} bytes) fits in stack',
            'conflict': f'Target stack_bytes={stack_bytes}; estimated usage exceeds limit',
            'recommendation': 'Move large arrays to static or global scope, or increase stack size in target profile',
        }]
    return []


def check(source_text: str, target: dict) -> list:
    lines = source_text.splitlines()
    findings = []
    findings.extend(_check_heap_alloc(lines, target))
    findings.extend(_check_malloc_null(lines, target))
    findings.extend(_check_large_local_array(lines, target))
    findings.extend(_check_stack_overflow(lines, target))
    return findings
