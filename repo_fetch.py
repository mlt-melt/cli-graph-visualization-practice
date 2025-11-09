from __future__ import annotations

import io
import re
import urllib.request
import urllib.error
import zipfile
from pathlib import Path
from typing import Optional

GITHUB_RE = re.compile(r"^https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/#]+)(?:\.git)?(?:$|[/#])")


def _github_zip_url(owner: str, repo: str, branch: str) -> str:
    # codeload provides clean ZIPs per ref
    return f"https://codeload.github.com/{owner}/{repo}/zip/refs/heads/{branch}"


def fetch_github_repo_to_temp(repo_url: str, dest_dir: Path) -> Optional[Path]:
    """
    If repo_url is a GitHub repository URL, download ZIP of main/master into dest_dir
    and extract it. Return path to the extracted repo root. Otherwise return None.
    """
    m = GITHUB_RE.match(repo_url)
    if not m:
        return None
    owner = m.group("owner")
    repo = m.group("repo")

    # Try main then master
    for branch in ("main", "master"):
        url = _github_zip_url(owner, repo, branch)
        try:
            with urllib.request.urlopen(url) as resp:
                data = resp.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue
            raise
        except urllib.error.URLError:
            raise

        # Extract ZIP to dest_dir
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            zf.extractall(dest_dir)
            # GitHub zips have a top-level directory named {repo}-{branch}
            extracted_root = dest_dir / f"{repo}-{branch}"
            if extracted_root.exists():
                return extracted_root
            # Fallback: pick the only top-level directory
            candidates = [p for p in dest_dir.iterdir() if p.is_dir()]
            return candidates[0] if candidates else dest_dir

    # Neither main nor master found
    return None
