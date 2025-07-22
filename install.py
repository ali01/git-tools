#!/usr/bin/env python3
"""
Install script for git-tools

This script creates symlinks for all executable scripts in this directory
to ~/.local/bin, making them available in your PATH.

Usage:
    python3 install.py          # Install all scripts
    python3 install.py -u       # Uninstall all scripts
"""

import argparse
import os
import stat
import sys
from pathlib import Path


# ANSI color codes
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
RESET = '\033[0m'


def is_executable_script(file_path):
    """Check if a file is an executable script"""
    if not os.path.isfile(file_path):
        return False

    # Check if file is executable
    if not os.access(file_path, os.X_OK):
        return False

    # Check if it's a git tool (starts with git-)
    if not os.path.basename(file_path).startswith('git-'):
        return False

    # Skip test files and common non-script files
    name = os.path.basename(file_path)
    if name.endswith(('.test', '.md', '.txt', '.pyc', '__pycache__')):
        return False

    return True


def find_scripts(directory):
    """Find all executable scripts in subdirectories only"""
    scripts = []

    # Only check subdirectories for executable scripts
    for item in os.listdir(directory):
        item_path = os.path.join(directory, item)
        if os.path.isdir(item_path) and not item.startswith('.'):
            # Look for executable scripts in subdirectory
            for file in os.listdir(item_path):
                file_path = os.path.join(item_path, file)
                if is_executable_script(file_path):
                    scripts.append(file_path)

    return sorted(scripts)


def ensure_local_bin():
    """Ensure ~/.local/bin exists and is in PATH"""
    local_bin = Path.home() / '.local' / 'bin'
    local_bin.mkdir(parents=True, exist_ok=True)

    # Check if ~/.local/bin is in PATH
    if str(local_bin) not in os.environ.get('PATH', '').split(':'):
        shell_rc = Path.home() / '.zshrc' if os.path.exists(Path.home() / '.zshrc') else Path.home() / '.bashrc'
        print(f"\n{YELLOW}Warning:{RESET} {local_bin} is not in your PATH.")
        print(f"   Add this line to your {shell_rc}:")
        print(f'   export PATH="$PATH:$HOME/.local/bin"')
        print(f"   Then run: source {shell_rc}")

    return local_bin


def install_scripts(scripts, local_bin, force=False):
    """Create symlinks for all scripts in ~/.local/bin"""
    installed = []
    skipped = []
    errors = []

    for script in scripts:
        script_name = os.path.basename(script)
        target = local_bin / script_name

        # Check if target already exists
        if target.exists() or target.is_symlink():
            if force:
                try:
                    target.unlink()
                except Exception as e:
                    errors.append((script_name, f"Failed to remove existing: {e}"))
                    continue
            else:
                # Check if it's already linked to our script
                if target.is_symlink() and os.path.realpath(target) == os.path.realpath(script):
                    skipped.append((script_name, "Already installed"))
                else:
                    skipped.append((script_name, "Already exists (use --force to overwrite)"))
                continue

        # Create symlink
        try:
            target.symlink_to(os.path.abspath(script))
            installed.append(script_name)
        except Exception as e:
            errors.append((script_name, str(e)))

    return installed, skipped, errors


def uninstall_scripts(scripts, local_bin):
    """Remove symlinks for all scripts from ~/.local/bin"""
    removed = []
    not_found = []
    errors = []

    for script in scripts:
        script_name = os.path.basename(script)
        target = local_bin / script_name

        if not (target.exists() or target.is_symlink()):
            not_found.append(script_name)
            continue

        # Check if it's a symlink to our script
        if target.is_symlink() and os.path.realpath(target) == os.path.realpath(script):
            try:
                target.unlink()
                removed.append(script_name)
            except Exception as e:
                errors.append((script_name, str(e)))
        else:
            errors.append((script_name, "Not a symlink to our script"))

    return removed, not_found, errors


def main():
    parser = argparse.ArgumentParser(description="Install git-tools scripts to ~/.local/bin")
    parser.add_argument('-u', '--uninstall', action='store_true',
                        help='Uninstall scripts instead of installing')
    parser.add_argument('-f', '--force', action='store_true',
                        help='Force overwrite existing files')
    parser.add_argument('-l', '--list', action='store_true',
                        help='List scripts without installing')

    args = parser.parse_args()

    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Find all executable scripts
    scripts = find_scripts(script_dir)

    if not scripts:
        print("No executable scripts found!")
        return 1

    if args.list:
        print("Found executable scripts:")
        for script in scripts:
            print(f"  - {os.path.basename(script)}")
        return 0

    # Ensure ~/.local/bin exists
    local_bin = ensure_local_bin()

    if args.uninstall:
        print(f"Uninstalling scripts from {local_bin}...")
        removed, not_found, errors = uninstall_scripts(scripts, local_bin)

        if removed:
            print(f"\n{GREEN}Success:{RESET} Removed {len(removed)} script(s):")
            for script in removed:
                print(f"  - {script}")

        if not_found:
            print(f"\n{YELLOW}Warning:{RESET} Not found {len(not_found)} script(s):")
            for script in not_found:
                print(f"  - {script}")

        if errors:
            print(f"\n{RED}Error:{RESET} Failed to remove {len(errors)} script(s):")
            for script, error in errors:
                print(f"  - {script}: {error}")
            return 1
    else:
        print(f"Installing scripts to {local_bin}...")
        installed, skipped, errors = install_scripts(scripts, local_bin, args.force)

        if installed:
            print(f"\n{GREEN}Success:{RESET} Installed {len(installed)} script(s):")
            for script in installed:
                print(f"  - {script}")

        if skipped:
            print(f"\n{YELLOW}Warning:{RESET} Skipped {len(skipped)} script(s):")
            for script, reason in skipped:
                print(f"  - {script}: {reason}")

        if errors:
            print(f"\n{RED}Error:{RESET} Failed to install {len(errors)} script(s):")
            for script, error in errors:
                print(f"  - {script}: {error}")
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
