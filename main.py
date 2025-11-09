import argparse
import configparser
import sys
from pathlib import Path
from urllib.parse import urlparse
import re
import tempfile

from typing import Iterable

# Local modules
try:
	from repo_fetch import fetch_github_repo_to_temp
	from nuget_parser import (
		discover_project_file,
		parse_dependencies_from_project,
	)
except Exception:
	# Allow running even if modules not yet available during partial execution
	fetch_github_repo_to_temp = None  # type: ignore
	discover_project_file = None  # type: ignore
	parse_dependencies_from_project = None  # type: ignore


APP_SECTION = "app"
TEST_REPO_MODES = {"local-path", "remote-url"}
OUTPUT_MODES = {"ascii-tree", "list"}


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description=(
			"CLI tool: dependency graph visualizer (Stage 1: config + validation).\n"
			"Reads INI config and prints user parameters as key=value."
		)
	)
	parser.add_argument(
		"-c",
		"--config",
		type=str,
		default="configs/config.ini",
		help="Path to INI configuration file (default: ./configs/config.ini)",
	)
	parser.add_argument(
		"--action",
		choices=["print-config", "show-deps"],
		default="print-config",
		help=(
			"Action to perform. 'print-config' prints validated parameters (Stage 1). "
			"'show-deps' downloads/parses repo and prints direct NuGet dependencies (Stage 2)."
		),
	)
	return parser.parse_args()


def read_config(config_path: Path) -> configparser.ConfigParser:
	if not config_path.exists():
		raise FileNotFoundError(f"Config file not found: {config_path}")

	parser = configparser.ConfigParser()
	try:
		with config_path.open("r", encoding="utf-8") as f:
			parser.read_file(f)
	except configparser.Error as e:
		raise ValueError(f"Failed to parse INI config: {e}") from e
	return parser


def is_valid_package_name(name: str) -> bool:
	# Letters, numbers, dot, underscore, dash; cannot be empty; max 128 chars
	return bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", name))


def is_valid_url(url: str) -> bool:
	p = urlparse(url)
	return p.scheme in {"http", "https", "git"} and bool(p.netloc)


def validate_and_normalize(raw: dict) -> tuple[dict, list[str]]:
	errors: list[str] = []
	out: dict = {}

	# Required keys
	required = ["package_name", "repo_source", "test_repo_mode", "output_mode"]
	for key in required:
		if key not in raw:
			errors.append(f"Missing required parameter: {key}")

	if errors:
		return out, errors

	package_name = (raw["package_name"] or "").strip()
	repo_source = (raw["repo_source"] or "").strip()
	test_repo_mode = (raw["test_repo_mode"] or "").strip().lower()
	output_mode = (raw["output_mode"] or "").strip().lower()

	# package_name
	if not is_valid_package_name(package_name):
		errors.append(
			"package_name is invalid. Allowed: letters, numbers, '.', '_', '-'; must start with alnum; length 1..128."
		)
	else:
		out["package_name"] = package_name

	# test_repo_mode
	if test_repo_mode not in TEST_REPO_MODES:
		errors.append(
			f"test_repo_mode must be one of {sorted(TEST_REPO_MODES)}; got '{test_repo_mode or '<empty>'}'."
		)
	else:
		out["test_repo_mode"] = test_repo_mode

	# output_mode
	if output_mode not in OUTPUT_MODES:
		errors.append(
			f"output_mode must be one of {sorted(OUTPUT_MODES)}; got '{output_mode or '<empty>'}'."
		)
	else:
		out["output_mode"] = output_mode

	# repo_source (depends on test_repo_mode)
	if not repo_source:
		errors.append("repo_source cannot be empty")
	else:
		if test_repo_mode == "local-path":
			p = Path(repo_source).expanduser()
			if not p.exists():
				errors.append(
					f"repo_source path does not exist (test_repo_mode=local-path): {p}"
				)
			else:
				# Normalize to absolute path for output clarity
				out["repo_source"] = str(p.resolve())
		elif test_repo_mode == "remote-url":
			if not is_valid_url(repo_source):
				errors.append(
					f"repo_source is not a valid URL (test_repo_mode=remote-url): {repo_source}"
				)
			else:
				out["repo_source"] = repo_source
		else:
			# If mode itself invalid, skip validating source to avoid noise
			pass

	return out, errors


def load_user_parameters(cfg: configparser.ConfigParser) -> dict:
	if APP_SECTION not in cfg:
		raise KeyError(
			f"Missing section [{APP_SECTION}] in config. All parameters must be under this section."
		)
	section = cfg[APP_SECTION]
	# Fetch raw values as strings; don't provide defaults so we can detect missing keys
	raw = {
		key: section.get(key, fallback=None)
		for key in ["package_name", "repo_source", "test_repo_mode", "output_mode"]
	}
	validated, errors = validate_and_normalize(raw)
	if errors:
		raise ValueError(
			"Configuration validation failed:\n" + "\n".join(f" - {e}" for e in errors)
		)
	return validated


def print_parameters(params: dict) -> None:
	# Print exactly as key=value lines, in a stable order
	order = ["package_name", "repo_source", "test_repo_mode", "output_mode"]
	for key in order:
		value = params.get(key, "")
		print(f"{key}={value}")


def main() -> int:
	args = parse_args()
	try:
		cfg = read_config(Path(args.config))
		params = load_user_parameters(cfg)
	except (FileNotFoundError, KeyError, ValueError) as e:
		print(str(e), file=sys.stderr)
		return 1

	if args.action == "print-config":
		# Stage 1 requirement: print all user-configurable parameters
		print_parameters(params)
		return 0

	if args.action == "show-deps":
		# Stage 2: print all direct dependencies of the given package using repo URL
		if params.get("test_repo_mode") != "remote-url":
			print(
				"For --action=show-deps the config must use test_repo_mode=remote-url.",
				file=sys.stderr,
			)
			return 1
		if fetch_github_repo_to_temp is None:
			print("Internal error: repo fetch module not available", file=sys.stderr)
			return 1

		repo_url = params["repo_source"]
		package_name = params["package_name"]

		# Fetch repository to a temp directory (supports GitHub URLs in this prototype)
		try:
			with tempfile.TemporaryDirectory(prefix="deps_repo_") as tmpdir:
				repo_root = fetch_github_repo_to_temp(repo_url, Path(tmpdir))
				if repo_root is None:
					print(
						"Unsupported repository URL. Only GitHub repositories are supported at this stage.",
						file=sys.stderr,
					)
					return 1

				# Discover project file for the given package
				proj_file = discover_project_file(Path(repo_root), package_name)
				if proj_file is None:
					print(
						f"Cannot find project for package '{package_name}' (.csproj or .nuspec).",
						file=sys.stderr,
					)
					return 1

				# Parse dependencies
				deps = list(parse_dependencies_from_project(proj_file))
		except Exception as e:
			print(f"Failed to fetch or parse repository: {e}", file=sys.stderr)
			return 1

		# Print direct dependencies, one per line: name versionSpec
		for dep_id, version in deps:
			print(f"{dep_id} {version}")
		return 0

	print("Unknown action", file=sys.stderr)
	return 1


if __name__ == "__main__":
	sys.exit(main())

