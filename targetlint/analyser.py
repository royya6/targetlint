from targetlint.rules.memory import check as check_memory
from targetlint.rules.stdlib import check as check_stdlib
from targetlint.rules.timing import check as check_timing
from targetlint.rules.hardware import check as check_hardware
from targetlint.rules.safety import check as check_safety

_SEVERITY_ORDER = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}


def run(source_text: str, target: dict) -> list[dict]:
    """Run all five rule checks and return findings sorted by severity.

    Severity order: CRITICAL -> HIGH -> MEDIUM -> LOW.
    """
    findings = []
    findings.extend(check_memory(source_text, target))
    findings.extend(check_stdlib(source_text, target))
    findings.extend(check_timing(source_text, target))
    findings.extend(check_hardware(source_text, target))
    findings.extend(check_safety(source_text, target))

    findings.sort(key=lambda f: _SEVERITY_ORDER.get(f.get('severity', 'LOW'), 3))
    return findings
