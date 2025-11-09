from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple


def parse_test_repo(file_path: Path) -> Dict[str, List[Tuple[str, str]]]:
    """
    Parse a test repository file.
    Format:
        A: B C
        B: D E
        C:
        ...
    Where each line is:
        PACKAGE: DEP1 DEP2 ...
    Package names are uppercase letters.
    Returns a dict: package_id -> [(dep_id, version), ...]
    Version is always "*" in test repos.
    """
    repo: Dict[str, List[Tuple[str, str]]] = {}
    with file_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" not in line:
                continue
            pkg, deps_str = line.split(":", 1)
            pkg = pkg.strip()
            deps_list = deps_str.strip().split() if deps_str.strip() else []
            repo[pkg] = [(d, "*") for d in deps_list]
    return repo


def create_test_dependency_provider(repo: Dict[str, List[Tuple[str, str]]]):
    """
    Create a dependency provider function from a test repo dict.
    """

    def provider(package_id: str) -> List[Tuple[str, str]]:
        return repo.get(package_id, [])

    return provider
