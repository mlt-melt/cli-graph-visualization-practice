"""
NuGet API client for fetching package dependencies from api.nuget.org.

Uses the NuGet V3 flat container API:
- List versions: GET /v3-flatcontainer/{package}/index.json
- Get nuspec: GET /v3-flatcontainer/{package}/{version}/{package}.nuspec
"""
from __future__ import annotations

import urllib.request
import urllib.error
import json
import xml.etree.ElementTree as ET
from typing import List, Tuple, Optional, Dict

# Base URL for NuGet API (without trailing slash)
NUGET_API_BASE = "https://api.nuget.org/v3-flatcontainer"

# Type alias
Dependency = Tuple[str, str]  # (package_id, version_spec)


def get_package_versions(package_id: str, base_url: str = NUGET_API_BASE) -> List[str]:
    """
    Get list of available versions for a package from NuGet API.
    
    Args:
        package_id: Package name (case-insensitive)
        base_url: NuGet API base URL
        
    Returns:
        List of version strings, sorted by NuGet (oldest first)
        
    Raises:
        urllib.error.HTTPError: If package not found (404) or other HTTP error
        urllib.error.URLError: If network error occurs
    """
    # NuGet API uses lowercase package IDs
    package_lower = package_id.lower()
    url = f"{base_url}/{package_lower}/index.json"
    
    with urllib.request.urlopen(url) as response:
        data = json.loads(response.read().decode("utf-8"))
        return data.get("versions", [])


def get_latest_version(package_id: str, base_url: str = NUGET_API_BASE) -> Optional[str]:
    """
    Get the latest version of a package.
    
    Returns:
        Latest version string, or None if package has no versions
    """
    versions = get_package_versions(package_id, base_url)
    return versions[-1] if versions else None


def fetch_nuspec(package_id: str, version: str, base_url: str = NUGET_API_BASE) -> str:
    """
    Fetch .nuspec file content from NuGet API.
    
    Args:
        package_id: Package name (case-insensitive)
        version: Package version
        base_url: NuGet API base URL
        
    Returns:
        XML content of the .nuspec file
        
    Raises:
        urllib.error.HTTPError: If package/version not found or other HTTP error
    """
    package_lower = package_id.lower()
    url = f"{base_url}/{package_lower}/{version}/{package_lower}.nuspec"
    
    with urllib.request.urlopen(url) as response:
        return response.read().decode("utf-8")


def _strip_namespace(tag: str) -> str:
    """Remove XML namespace prefix from tag."""
    if tag.startswith("{"):
        close = tag.find("}")
        if close != -1:
            return tag[close + 1:]
    return tag


def parse_nuspec_dependencies(nuspec_xml: str, target_framework: Optional[str] = None) -> List[Dependency]:
    """
    Parse dependencies from .nuspec XML content.
    
    The .nuspec format has dependencies in:
    <package>
      <metadata>
        <dependencies>
          <group targetFramework="...">
            <dependency id="..." version="..." />
          </group>
          <!-- or directly: -->
          <dependency id="..." version="..." />
        </dependencies>
      </metadata>
    </package>
    
    Args:
        nuspec_xml: XML content of .nuspec file
        target_framework: Optional target framework filter (e.g., "net6.0")
                         If None, returns all dependencies from all groups
        
    Returns:
        List of (package_id, version_spec) tuples
    """
    root = ET.fromstring(nuspec_xml)
    dependencies: List[Dependency] = []
    seen: set = set()  # Avoid duplicates
    
    # Find metadata element
    for metadata in root:
        if _strip_namespace(metadata.tag) != "metadata":
            continue
            
        # Find dependencies element
        for deps_elem in metadata:
            if _strip_namespace(deps_elem.tag) != "dependencies":
                continue
                
            # Process children (groups or direct dependencies)
            for child in deps_elem:
                tag_name = _strip_namespace(child.tag)
                
                if tag_name == "group":
                    # Framework-specific dependency group
                    framework = child.attrib.get("targetFramework", "")
                    
                    # Filter by target framework if specified
                    if target_framework and framework:
                        # Simple matching - could be improved for proper framework comparison
                        if target_framework.lower() not in framework.lower():
                            continue
                    
                    for dep in child:
                        if _strip_namespace(dep.tag) == "dependency":
                            dep_id = dep.attrib.get("id", "")
                            dep_version = dep.attrib.get("version", "*")
                            if dep_id and dep_id not in seen:
                                seen.add(dep_id)
                                dependencies.append((dep_id, dep_version))
                                
                elif tag_name == "dependency":
                    # Direct dependency (no framework group)
                    dep_id = child.attrib.get("id", "")
                    dep_version = child.attrib.get("version", "*")
                    if dep_id and dep_id not in seen:
                        seen.add(dep_id)
                        dependencies.append((dep_id, dep_version))
    
    return dependencies


def get_package_dependencies(
    package_id: str,
    version: Optional[str] = None,
    base_url: str = NUGET_API_BASE,
    target_framework: Optional[str] = None,
) -> List[Dependency]:
    """
    Get dependencies for a NuGet package.
    
    Args:
        package_id: Package name
        version: Package version (if None, uses latest)
        base_url: NuGet API base URL
        target_framework: Optional framework filter
        
    Returns:
        List of (dependency_id, version_spec) tuples
        
    Raises:
        ValueError: If package or version not found
        urllib.error.HTTPError: On HTTP errors
    """
    # Get version if not specified
    if version is None:
        version = get_latest_version(package_id, base_url)
        if version is None:
            raise ValueError(f"Package '{package_id}' not found or has no versions")
    
    # Fetch and parse nuspec
    try:
        nuspec_xml = fetch_nuspec(package_id, version, base_url)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise ValueError(f"Package '{package_id}' version '{version}' not found")
        raise
    
    return parse_nuspec_dependencies(nuspec_xml, target_framework)


def create_nuget_dependency_provider(
    base_url: str = NUGET_API_BASE,
    target_framework: Optional[str] = None,
    version_cache: Optional[Dict[str, str]] = None,
):
    """
    Create a dependency provider function for use with DependencyGraph.
    
    Args:
        base_url: NuGet API base URL
        target_framework: Optional framework filter
        version_cache: Optional dict to cache resolved versions
        
    Returns:
        Function that takes package_id and returns list of dependencies
    """
    if version_cache is None:
        version_cache = {}
    
    def provider(package_id: str) -> List[Tuple[str, str]]:
        try:
            # Use cached version or get latest
            version = version_cache.get(package_id)
            if version is None:
                version = get_latest_version(package_id, base_url)
                if version:
                    version_cache[package_id] = version
            
            if version is None:
                return []
            
            return get_package_dependencies(package_id, version, base_url, target_framework)
        except (ValueError, urllib.error.HTTPError, urllib.error.URLError):
            # Package not found or network error - treat as no dependencies
            return []
    
    return provider
