from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def resolve_repo_path(path: str | Path, *, allow_missing: bool = False, allow_symlink: bool = False) -> Path:
    """Return a path guaranteed to stay inside the repository root."""
    root = repo_root()
    candidate = Path(path).expanduser()
    candidate = candidate if candidate.is_absolute() else (root / candidate)
    resolved = candidate.resolve()

    try:
        resolved.relative_to(root)
    except ValueError as exc:  # pragma: no cover - defensive path guard
        raise ValueError(f"Path is outside repository root: {path}") from exc

    if resolved.is_symlink() and not allow_symlink:
        raise ValueError(f"Symlinks are not allowed for repository paths: {path}")

    if not allow_missing and not resolved.exists():
        raise FileNotFoundError(f"Required repository file not found: {path}")

    return resolved
