from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

# Types
Dependency = Tuple[str, str]  # (id, versionSpec)


# -----------------
# Parsing utilities
# -----------------

def _ns_clean(tag: str) -> str:
    # Remove XML namespace if present: {namespace}Tag -> Tag
    if tag.startswith("{"):
        close = tag.find("}")
        if close != -1:
            return tag[close + 1 :]
    return tag


def parse_csproj(file_path: Path) -> Iterable[Dependency]:
    tree = ET.parse(file_path)
    root = tree.getroot()
    for itemgroup in root.iter():
        if _ns_clean(itemgroup.tag) != "ItemGroup":
            continue
        for pkg in itemgroup:
            if _ns_clean(pkg.tag) != "PackageReference":
                continue
            dep_id = pkg.attrib.get("Include") or pkg.attrib.get("Update")
            version = pkg.attrib.get("Version")
            if version is None:
                # Sometimes <Version>child</Version>
                vchild = next((c for c in pkg if _ns_clean(c.tag) == "Version"), None)
                if vchild is not None and vchild.text:
                    version = vchild.text.strip()
            if dep_id:
                yield (dep_id, version or "*")


def parse_packages_config(file_path: Path) -> Iterable[Dependency]:
    tree = ET.parse(file_path)
    root = tree.getroot()
    if _ns_clean(root.tag) != "packages":
        return []
    for pkg in root:
        if _ns_clean(pkg.tag) != "package":
            continue
        dep_id = pkg.attrib.get("id")
        version = pkg.attrib.get("version")
        if dep_id and version:
            yield (dep_id, version)


def parse_nuspec(file_path: Path) -> Iterable[Dependency]:
    tree = ET.parse(file_path)
    root = tree.getroot()
    # Look for package/metadata/dependencies/*/dependency
    for metadata in root:
        if _ns_clean(metadata.tag) != "metadata":
            continue
        for deps in metadata:
            if _ns_clean(deps.tag) != "dependencies":
                continue
            # Either <group><dependency .../></group> or direct <dependency/>
            for node in deps:
                name = _ns_clean(node.tag)
                if name == "group":
                    for d in node:
                        if _ns_clean(d.tag) == "dependency":
                            dep_id = d.attrib.get("id")
                            version = d.attrib.get("version") or "*"
                            if dep_id:
                                yield (dep_id, version)
                elif name == "dependency":
                    dep_id = node.attrib.get("id")
                    version = node.attrib.get("version") or "*"
                    if dep_id:
                        yield (dep_id, version)


# -----------------
# Discovery utilities
# -----------------

def discover_project_file(repo_root: Path, package_name: str) -> Optional[Path]:
    """Try to find a .nuspec or .csproj corresponding to package_name.
    Priority:
      1) {package_name}.nuspec anywhere
      2) {package_name}.csproj anywhere
      3) single .nuspec in repo (if unique)
      4) single .csproj in repo (if unique)
    """
    nuspec_targets: List[Path] = []
    csproj_targets: List[Path] = []

    for p in repo_root.rglob("*.nuspec"):
        if p.name.lower() == f"{package_name.lower()}.nuspec":
            return p
        nuspec_targets.append(p)
    for p in repo_root.rglob("*.csproj"):
        if p.name.lower() == f"{package_name.lower()}.csproj":
            return p
        csproj_targets.append(p)

    if len(nuspec_targets) == 1:
        return nuspec_targets[0]
    if len(csproj_targets) == 1:
        return csproj_targets[0]
    return None


def parse_dependencies_from_project(project_file: Path) -> Iterable[Dependency]:
    suffix = project_file.suffix.lower()
    if suffix == ".nuspec":
        return list(parse_nuspec(project_file))
    if suffix == ".csproj":
        # Prefer PackageReference, but also check sibling packages.config
        deps = list(parse_csproj(project_file))
        if deps:
            return deps
        pkg_cfg = project_file.with_name("packages.config")
        if pkg_cfg.exists():
            return list(parse_packages_config(pkg_cfg))
        # Search in project directory as fallback
        for candidate in project_file.parent.glob("**/packages.config"):
            return list(parse_packages_config(candidate))
        return []
    if suffix == ".config" and project_file.name == "packages.config":
        return list(parse_packages_config(project_file))
    return []
