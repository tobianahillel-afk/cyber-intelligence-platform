from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory


@contextmanager
def quarantined_artifact(content: bytes, *, suffix: str) -> Iterator[Path]:
    """Expose bounded untrusted bytes only inside a disposable private directory."""

    if not content:
        raise ValueError("quarantined artifact content cannot be empty")
    if not suffix.startswith(".") or "/" in suffix or "\\" in suffix or len(suffix) > 16:
        raise ValueError("quarantine suffix is invalid")
    with TemporaryDirectory(prefix="cip-artifact-") as directory:
        root = Path(directory)
        root.chmod(0o700)
        path = root / f"artifact{suffix.casefold()}"
        path.write_bytes(content)
        path.chmod(0o600)
        yield path
