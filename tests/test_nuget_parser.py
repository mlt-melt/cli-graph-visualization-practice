import io
from pathlib import Path
import tempfile
import unittest

from nuget_parser import parse_csproj, parse_nuspec, parse_packages_config, discover_project_file, parse_dependencies_from_project


class TestNuGetParser(unittest.TestCase):
    def test_parse_csproj(self):
        xml = """
<Project Sdk="Microsoft.NET.Sdk">
  <ItemGroup>
    <PackageReference Include="Newtonsoft.Json" Version="13.0.1" />
    <PackageReference Include="Serilog">
      <Version>2.12.0</Version>
    </PackageReference>
  </ItemGroup>
</Project>
"""
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "App.csproj"
            p.write_text(xml, encoding="utf-8")
            deps = list(parse_csproj(p))
            self.assertIn(("Newtonsoft.Json", "13.0.1"), deps)
            self.assertIn(("Serilog", "2.12.0"), deps)

    def test_parse_packages_config(self):
        xml = """
<packages>
  <package id="NUnit" version="3.13.3" />
  <package id="Moq" version="4.18.4" />
</packages>
"""
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "packages.config"
            p.write_text(xml, encoding="utf-8")
            deps = list(parse_packages_config(p))
            self.assertEqual(deps, [("NUnit", "3.13.3"), ("Moq", "4.18.4")])

    def test_parse_nuspec(self):
        xml = """
<package>
  <metadata>
    <id>MyLib</id>
    <dependencies>
      <group targetFramework="net6.0">
        <dependency id="Dapper" version=">= 2.0.0" />
      </group>
      <dependency id="Polly" version="7.*" />
    </dependencies>
  </metadata>
</package>
"""
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "MyLib.nuspec"
            p.write_text(xml, encoding="utf-8")
            deps = list(parse_nuspec(p))
            self.assertIn(("Dapper", ">= 2.0.0"), deps)
            self.assertIn(("Polly", "7.*"), deps)

    def test_discover_and_parse(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            # Create a nested project structure
            proj_dir = root / "src" / "MyLib"
            proj_dir.mkdir(parents=True)
            (proj_dir / "MyLib.csproj").write_text(
                """
<Project Sdk=\"Microsoft.NET.Sdk\">
  <ItemGroup>
    <PackageReference Include=\"FluentAssertions\" Version=\"6.12.0\" />
  </ItemGroup>
</Project>
""",
                encoding="utf-8",
            )
            proj_file = discover_project_file(root, "MyLib")
            self.assertIsNotNone(proj_file)
            deps = list(parse_dependencies_from_project(proj_file))
            self.assertEqual(deps, [("FluentAssertions", "6.12.0")])


if __name__ == "__main__":
    unittest.main()
