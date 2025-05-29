#!/usr/bin/env python3

import argparse
import fnmatch
import logging
import os
import shutil
import subprocess
import tempfile
from datetime import datetime

import yaml


class RepositoryExporter:
    def __init__(
        self,
        source,
        output_file,
        config_file,
        is_git,
        cli_excluded_dirs,
        obey_gitignore,
        verbose=False,
    ):
        # Set up logging first
        log_level = logging.DEBUG if verbose else logging.WARNING
        logging.basicConfig(
            level=log_level, format="%(asctime)s - %(levelname)s - %(message)s"
        )
        self.logger = logging.getLogger(__name__)

        # Initialize other attributes
        self.source = source
        self.output_file = self.generate_output_filename(output_file)
        self.is_git = is_git
        self.temp_dir = None
        self.snapshot_time = datetime.now()
        self.config = self.load_config(config_file)
        self.excluded_dirs = cli_excluded_dirs or self.config.get("excluded_dirs", [])
        self.included_extensions = self.config.get("included_extensions", {})
        self.obey_gitignore = obey_gitignore
        self.gitignore_patterns = self.load_gitignore() if obey_gitignore else []

    def load_config(self, config_file=None):
        """
        Load the configuration from a YAML file with fallback locations.
        """
        # Define potential config file locations in order of preference
        potential_configs = []
        
        if config_file:
            potential_configs.append(config_file)
        
        # Add fallback locations
        potential_configs.extend([
            "config.yaml",  # Current directory
            os.path.expanduser("~/.config/repo2md/config.yaml"),  # User config
            os.path.expanduser("~/.repo2md/config.yaml"),  # User home
            "/etc/repo2md/config.yaml",  # System-wide
        ])
        
        # Try each location
        for config_path in potential_configs:
            try:
                with open(config_path, "r", encoding="utf-8") as file:
                    config = yaml.safe_load(file)
                    if not config:
                        self.logger.warning(
                            f"Configuration file {config_path} is empty, trying next location."
                        )
                        continue
                    self.logger.info(f"Loaded config from: {config_path}")
                    return config
            except FileNotFoundError:
                self.logger.debug(f"Config file not found: {config_path}")
                continue
            except yaml.YAMLError as e:
                self.logger.error(f"Error parsing YAML file {config_path}: {e}")
                continue
        
        # If no config file found, return default configuration
        self.logger.info("No configuration file found, using default settings")
        return {
            "max_file_size": 1048576,  # 1 MB
            "excluded_dirs": [".venv", "node_modules", "__pycache__", ".git"],
            "included_extensions": {
                ".py": "python",
                ".js": "javascript",
                ".ts": "typescript",
                ".tsx": "react",
                ".jsx": "react",
                ".html": "html",
                ".css": "css",
                ".json": "json",
                ".yaml": "yaml",
                ".yml": "yaml",
                ".md": "markdown",
                ".sh": "bash",
                ".sql": "sql",
                ".java": "java",
                ".cpp": "cpp",
                ".c": "c",
                ".h": "c",
                ".rs": "rust",
                ".go": "go"
            }
        }

    def load_gitignore(self):
        """
        Load patterns from .gitignore if present.
        """
        gitignore_path = os.path.join(self.source, ".gitignore")
        if os.path.exists(gitignore_path):
            try:
                with open(gitignore_path, "r", encoding="utf-8") as file:
                    patterns = [
                        line.strip()
                        for line in file
                        if line.strip() and not line.startswith("#")
                    ]
                    self.logger.info(f"Loaded .gitignore patterns: {patterns}")
                    return patterns
            except Exception as e:
                self.logger.error(f"Error reading .gitignore: {e}")
        return []

    @staticmethod
    def generate_output_filename(base_name):
        """
        Generate a filename with the current date and time appended.
        """
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"{base_name}_{timestamp}.md"

    def clone_repository(self):
        """
        Clone the Git repository into a temporary directory.
        """
        self.temp_dir = tempfile.mkdtemp()
        self.logger.info(
            f"Cloning repository from {self.source} into {self.temp_dir}..."
        )
        try:
            subprocess.run(["git", "clone", self.source, self.temp_dir], check=True)
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Error cloning repository: {e}")
            raise

    def cleanup(self):
        """
        Clean up temporary directory.
        """
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def is_excluded(self, path):
        """
        Check if a path matches excluded directories or .gitignore patterns.
        """
        # Check against excluded directories
        for excluded_dir in self.excluded_dirs:
            if path.startswith(os.path.join(self.source, excluded_dir)):
                self.logger.debug(f"Excluding directory (by config): {path}")
                return True

        # Check against .gitignore patterns
        relative_path = os.path.relpath(path, self.source)
        for pattern in self.gitignore_patterns:
            # Handle directory patterns ending with /
            if pattern.endswith("/"):
                pattern = pattern[:-1]  # Remove trailing slash
                if relative_path.startswith(pattern):
                    self.logger.debug(f"Excluding directory (by .gitignore): {path}")
                    return True
            # Handle regular patterns
            if fnmatch.fnmatch(relative_path, pattern):
                self.logger.debug(f"Excluding file (by .gitignore): {path}")
                return True

        return False

    def is_file_valid(self, file_path):
        """
        Check if a file is valid based on size, included extensions, and exclusions.
        """
        if self.is_excluded(file_path):
            self.logger.info(f"Excluding file (by exclusion rules): {file_path}")
            return False

        try:
            file_size = os.path.getsize(file_path)
            if file_size > self.config.get("max_file_size", 1048576):
                self.logger.info(f"Excluding file (by size): {file_path}")
                return False

            file_extension = os.path.splitext(file_path)[-1].lower()
            if file_extension in self.included_extensions.keys():
                self.logger.info(f"Including file: {file_path}")
                return True
            else:
                self.logger.info(f"Excluding file (by extension): {file_path}")
                return False
        except (FileNotFoundError, PermissionError) as e:
            self.logger.error(f"Error accessing file {file_path}: {e}")
            return False

    def get_language_from_extension(self, file_extension):
        """
        Get the programming language for syntax highlighting based on the file extension.
        """
        return self.included_extensions.get(file_extension, "")  # Default: no language

    def export(self):
        """
        Export repository files to a Markdown file.
        """
        source_dir = self.temp_dir if self.is_git else self.source

        if not os.path.exists(source_dir):
            self.logger.error(f"Source directory does not exist: {source_dir}")
            raise ValueError(f"Source directory does not exist: {source_dir}")

        snapshot_time_str = self.snapshot_time.strftime("%Y-%m-%d %H:%M:%S")
        with open(self.output_file, "w", encoding="utf-8") as markdown_file:
            # Add snapshot time to the Markdown header
            markdown_file.write("# Repository Snapshot\n\n")
            markdown_file.write(f"**Snapshot taken on:** {snapshot_time_str}\n\n")
            markdown_file.write("---\n\n")

            for root, dirs, files in os.walk(source_dir):
                self.logger.info(f"Checking directory: {root}")
                dirs[:] = [
                    d for d in dirs if not self.is_excluded(os.path.join(root, d))
                ]

                for file in files:
                    file_path = os.path.join(root, file)
                    file_extension = os.path.splitext(file)[-1].lower()
                    self.logger.info(
                        f"Found file: {file_path} with extension: {file_extension}"
                    )

                    if self.is_file_valid(file_path):
                        self.logger.info(f"Including file: {file_path}")
                        try:
                            with open(file_path, "r", encoding="utf-8") as code_file:
                                content = code_file.read()

                            relative_path = os.path.relpath(file_path, source_dir)
                            language = self.get_language_from_extension(file_extension)

                            markdown_file.write(f"## File: `{relative_path}`\n\n")
                            markdown_file.write(f"```{language}\n{content}\n```\n\n")
                        except Exception as e:
                            self.logger.error(f"Error reading file {file_path}: {e}")

        self.logger.info(f"Repository content exported to {self.output_file}")


def main():
    """
    Main entry point for the repo2md command-line tool.
    """
    parser = argparse.ArgumentParser(
        description="Export files from a local directory or Git repository to a Markdown file."
    )
    parser.add_argument(
        "source", help="Path to the local directory or URL of the Git repository."
    )
    parser.add_argument(
        "-c",
        "--config",
        help="Path to the YAML configuration file. If not provided, will search for config.yaml in current directory, ~/.config/repo2md/, ~/.repo2md/, and /etc/repo2md/.",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="repository",
        help="Base name for the output Markdown file (timestamp will be appended).",
    )
    parser.add_argument(
        "-g",
        "--git",
        action="store_true",
        help="Specify if the source is a Git repository URL.",
    )
    parser.add_argument(
        "-e",
        "--exclude-dirs",
        nargs="*",
        help="Directories to exclude from processing.",
    )
    parser.add_argument(
        "-i",
        "--obey-gitignore",
        action="store_true",
        help="Respect the .gitignore file in the repository.",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging output."
    )
    args = parser.parse_args()

    exporter = RepositoryExporter(
        args.source,
        args.output,
        args.config,
        args.git,
        args.exclude_dirs,
        args.obey_gitignore,
        args.verbose,
    )

    try:
        if args.git:
            exporter.clone_repository()
        exporter.export()
        print(f"Repository content exported to {exporter.output_file}")
    except Exception as e:
        print(f"Error: {str(e)}")
        exit(1)
    finally:
        if args.git:
            exporter.cleanup()


if __name__ == "__main__":
    main()
