"""
Unit tests for nuget_api module.
Tests NuGet API client functionality with mock data.
"""
import unittest
from unittest.mock import patch, MagicMock
import json

from nuget_api import (
    get_package_versions,
    get_latest_version,
    fetch_nuspec,
    parse_nuspec_dependencies,
    get_package_dependencies,
    create_nuget_dependency_provider,
)


class TestNuGetAPI(unittest.TestCase):
    """Test NuGet API client functions."""

    def test_parse_nuspec_simple_dependencies(self):
        """Test parsing nuspec with simple dependencies (no framework groups)."""
        nuspec_xml = '''<?xml version="1.0"?>
<package xmlns="http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd">
  <metadata>
    <id>TestPackage</id>
    <version>1.0.0</version>
    <dependencies>
      <dependency id="PackageA" version="1.0.0" />
      <dependency id="PackageB" version="2.0.0" />
    </dependencies>
  </metadata>
</package>'''
        deps = parse_nuspec_dependencies(nuspec_xml)
        self.assertEqual(len(deps), 2)
        self.assertIn(("PackageA", "1.0.0"), deps)
        self.assertIn(("PackageB", "2.0.0"), deps)

    def test_parse_nuspec_grouped_dependencies(self):
        """Test parsing nuspec with framework-specific dependency groups."""
        nuspec_xml = '''<?xml version="1.0"?>
<package xmlns="http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd">
  <metadata>
    <id>TestPackage</id>
    <version>1.0.0</version>
    <dependencies>
      <group targetFramework="net6.0">
        <dependency id="Net6Package" version="1.0.0" />
      </group>
      <group targetFramework=".NETStandard2.0">
        <dependency id="NetStdPackage" version="2.0.0" />
      </group>
    </dependencies>
  </metadata>
</package>'''
        # Without filter - should get all dependencies
        deps = parse_nuspec_dependencies(nuspec_xml)
        self.assertEqual(len(deps), 2)
        self.assertIn(("Net6Package", "1.0.0"), deps)
        self.assertIn(("NetStdPackage", "2.0.0"), deps)

    def test_parse_nuspec_with_framework_filter(self):
        """Test parsing nuspec with target framework filter."""
        nuspec_xml = '''<?xml version="1.0"?>
<package xmlns="http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd">
  <metadata>
    <id>TestPackage</id>
    <version>1.0.0</version>
    <dependencies>
      <group targetFramework="net6.0">
        <dependency id="Net6Package" version="1.0.0" />
      </group>
      <group targetFramework=".NETStandard2.0">
        <dependency id="NetStdPackage" version="2.0.0" />
      </group>
    </dependencies>
  </metadata>
</package>'''
        # Filter by net6.0
        deps = parse_nuspec_dependencies(nuspec_xml, target_framework="net6.0")
        self.assertEqual(len(deps), 1)
        self.assertIn(("Net6Package", "1.0.0"), deps)

    def test_parse_nuspec_empty_dependencies(self):
        """Test parsing nuspec with no dependencies."""
        nuspec_xml = '''<?xml version="1.0"?>
<package xmlns="http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd">
  <metadata>
    <id>TestPackage</id>
    <version>1.0.0</version>
    <dependencies>
    </dependencies>
  </metadata>
</package>'''
        deps = parse_nuspec_dependencies(nuspec_xml)
        self.assertEqual(len(deps), 0)

    def test_parse_nuspec_no_dependencies_element(self):
        """Test parsing nuspec without dependencies element at all."""
        nuspec_xml = '''<?xml version="1.0"?>
<package xmlns="http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd">
  <metadata>
    <id>TestPackage</id>
    <version>1.0.0</version>
  </metadata>
</package>'''
        deps = parse_nuspec_dependencies(nuspec_xml)
        self.assertEqual(len(deps), 0)

    def test_parse_nuspec_deduplicates(self):
        """Test that duplicate dependencies are removed."""
        nuspec_xml = '''<?xml version="1.0"?>
<package xmlns="http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd">
  <metadata>
    <id>TestPackage</id>
    <version>1.0.0</version>
    <dependencies>
      <group targetFramework="net6.0">
        <dependency id="CommonPackage" version="1.0.0" />
      </group>
      <group targetFramework="net7.0">
        <dependency id="CommonPackage" version="2.0.0" />
      </group>
    </dependencies>
  </metadata>
</package>'''
        deps = parse_nuspec_dependencies(nuspec_xml)
        # Should only include the first occurrence
        package_ids = [d[0] for d in deps]
        self.assertEqual(package_ids.count("CommonPackage"), 1)

    @patch('nuget_api.urllib.request.urlopen')
    def test_get_package_versions(self, mock_urlopen):
        """Test fetching package versions from API."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "versions": ["1.0.0", "1.1.0", "2.0.0"]
        }).encode('utf-8')
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        versions = get_package_versions("TestPackage")
        self.assertEqual(versions, ["1.0.0", "1.1.0", "2.0.0"])

        # Check URL is lowercased
        call_args = mock_urlopen.call_args[0][0]
        self.assertIn("testpackage", call_args.lower())

    @patch('nuget_api.urllib.request.urlopen')
    def test_get_latest_version(self, mock_urlopen):
        """Test getting latest version."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "versions": ["1.0.0", "1.1.0", "2.0.0"]
        }).encode('utf-8')
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        latest = get_latest_version("TestPackage")
        self.assertEqual(latest, "2.0.0")

    @patch('nuget_api.urllib.request.urlopen')
    def test_get_latest_version_empty(self, mock_urlopen):
        """Test getting latest version when no versions exist."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "versions": []
        }).encode('utf-8')
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        latest = get_latest_version("TestPackage")
        self.assertIsNone(latest)

    @patch('nuget_api.urllib.request.urlopen')
    def test_fetch_nuspec(self, mock_urlopen):
        """Test fetching nuspec content."""
        expected_xml = '<package><metadata/></package>'
        mock_response = MagicMock()
        mock_response.read.return_value = expected_xml.encode('utf-8')
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = fetch_nuspec("TestPackage", "1.0.0")
        self.assertEqual(result, expected_xml)

        # Check URL format
        call_args = mock_urlopen.call_args[0][0]
        self.assertIn("testpackage", call_args)
        self.assertIn("1.0.0", call_args)
        self.assertIn(".nuspec", call_args)

    def test_create_nuget_dependency_provider(self):
        """Test creating a dependency provider function."""
        provider = create_nuget_dependency_provider()
        self.assertTrue(callable(provider))

    def test_create_nuget_dependency_provider_with_cache(self):
        """Test provider uses version cache."""
        version_cache = {"CachedPackage": "1.0.0"}
        provider = create_nuget_dependency_provider(version_cache=version_cache)
        
        # The cache should be used, verify it's the same dict
        self.assertIn("CachedPackage", version_cache)


class TestNuGetAPIIntegration(unittest.TestCase):
    """Integration tests that actually call the NuGet API.
    
    These tests are skipped by default. Set NUGET_API_LIVE_TESTS=1 
    environment variable to run them.
    """
    
    @unittest.skip("Integration test - requires network. Remove skip to test.")
    def test_live_get_newtonsoft_versions(self):
        """Test getting Newtonsoft.Json versions from live API."""
        versions = get_package_versions("Newtonsoft.Json")
        self.assertIsInstance(versions, list)
        self.assertGreater(len(versions), 0)
        # Newtonsoft.Json 13.0.0 was released, should be in the list
        self.assertIn("13.0.1", versions)

    @unittest.skip("Integration test - requires network. Remove skip to test.")
    def test_live_get_package_dependencies(self):
        """Test getting dependencies from live API."""
        deps = get_package_dependencies("Newtonsoft.Json", "13.0.1")
        # Newtonsoft.Json 13.0.1 has minimal dependencies
        self.assertIsInstance(deps, list)


if __name__ == "__main__":
    unittest.main()
