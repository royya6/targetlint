import yaml

_REQUIRED_KEYS = {
    'arch', 'ram_bytes', 'stack_bytes', 'has_heap', 'has_stdlib',
    'has_fpu', 'clock_hz', 'word_size_bits', 'safety_critical',
}


def load_source(path: str) -> str:
    """Read and return a C source file as a string.

    Raises:
        FileNotFoundError: if the file does not exist.
        ValueError: if the file cannot be decoded as UTF-8.
    """
    try:
        with open(path, 'r', encoding='utf-8') as fh:
            return fh.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"Source file not found: {path!r}")
    except UnicodeDecodeError as exc:
        raise ValueError(f"Source file is not valid UTF-8: {path!r}") from exc


def load_target(path: str) -> dict:
    """Read and parse a YAML target profile.

    Raises:
        FileNotFoundError: if the file does not exist.
        ValueError: if required keys are missing from the profile.
    """
    try:
        with open(path, 'r', encoding='utf-8') as fh:
            profile = yaml.safe_load(fh)
    except FileNotFoundError:
        raise FileNotFoundError(f"Target profile not found: {path!r}")

    if not isinstance(profile, dict):
        raise ValueError(f"Target profile must be a YAML mapping: {path!r}")

    missing = _REQUIRED_KEYS - profile.keys()
    if missing:
        raise ValueError(
            f"Target profile missing required keys: {', '.join(sorted(missing))}"
        )

    profile.setdefault('watchdog_timeout_ms', None)
    return profile
