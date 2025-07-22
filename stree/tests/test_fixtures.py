"""Test fixtures and helpers for git-rp integration tests."""

import os
import shutil
import tempfile
import subprocess
from pathlib import Path
from contextlib import contextmanager


class GitRepo:
    """Helper class for managing test git repositories."""

    def __init__(self, path, bare=False):
        self.path = Path(path)
        self.bare = bare
        # Create the directory if it doesn't exist
        self.path.mkdir(parents=True, exist_ok=True)

    def init(self):
        """Initialize the git repository."""
        cmd = ["git", "init"]
        if self.bare:
            cmd.append("--bare")
        subprocess.run(cmd, cwd=self.path, check=True, capture_output=True)

        if not self.bare:
            # Set user config for test commits
            self.run_git("config", "user.email", "test@example.com")
            self.run_git("config", "user.name", "Test User")

    def run_git(self, *args):
        """Run a git command in this repository."""
        result = subprocess.run(
            ["git"] + list(args),
            cwd=self.path,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise subprocess.CalledProcessError(
                result.returncode,
                ["git"] + list(args),
                result.stdout,
                result.stderr
            )
        return result.stdout.strip()

    def add_file(self, filename, content="test content"):
        """Add a file to the repository."""
        file_path = self.path / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
        return file_path

    def commit(self, message="Test commit"):
        """Stage all changes and commit."""
        self.run_git("add", "-A")
        self.run_git("commit", "-m", message)
        return self.run_git("rev-parse", "HEAD")

    def add_remote(self, name, url):
        """Add a remote to the repository."""
        self.run_git("remote", "add", name, url)

    def create_branch(self, branch_name):
        """Create and checkout a new branch."""
        self.run_git("checkout", "-b", branch_name)

    def add_subtree(self, prefix, url, branch="main"):
        """Add a subtree to the repository."""
        self.run_git("subtree", "add", f"--prefix={prefix}", url, branch)

    def add_subtree_config(self, prefix, url, branch="main"):
        """Add subtree configuration to .git/config."""
        config_path = self.path / ".git" / "config"
        with open(config_path, "a") as f:
            f.write(f'\n[subtree "{prefix}"]\n')
            f.write(f'    url = {url}\n')
            f.write(f'    branch = {branch}\n')

    def get_refs(self):
        """Get all refs in the repository."""
        try:
            return self.run_git("show-ref").splitlines()
        except subprocess.CalledProcessError:
            return []

    def has_ref(self, ref_name):
        """Check if a ref exists."""
        refs = self.get_refs()
        return any(ref_name in ref for ref in refs)


@contextmanager
def temp_git_env():
    """Create a temporary environment for git tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Store original directory
        original_dir = os.getcwd()

        # Create test directory structure
        test_dir = Path(tmpdir)
        repos_dir = test_dir / "repos"
        repos_dir.mkdir()

        try:
            yield {
                "test_dir": test_dir,
                "repos_dir": repos_dir,
            }
        finally:
            # Restore original directory
            os.chdir(original_dir)


def create_simple_repo_structure(repos_dir):
    """Create a simple repository structure for testing.

    Returns:
        dict: Dictionary with paths to created repositories
    """
    # Create main repository
    main_repo = GitRepo(repos_dir / "main-repo")
    main_repo.init()
    main_repo.add_file("README.md", "# Main Repository")
    main_repo.commit("Initial commit")

    # Create subtree repository
    subtree_repo = GitRepo(repos_dir / "subtree-repo-bare", bare=True)
    subtree_repo.init()

    # Create a working repo for the subtree to push initial content
    subtree_work = GitRepo(repos_dir / "subtree-work")
    subtree_work.init()
    subtree_work.add_file("lib.py", "def hello(): return 'Hello from subtree'")
    subtree_work.commit("Initial subtree commit")
    subtree_work.add_remote("origin", str(subtree_repo.path))
    subtree_work.run_git("push", "origin", "main")

    return {
        "main": main_repo,
        "subtree_bare": subtree_repo,
        "subtree_work": subtree_work,
    }


def create_nested_repo_structure(repos_dir):
    """Create a nested repository structure for testing recursive subtrees.

    Returns:
        dict: Dictionary with paths to created repositories
    """
    # Create main repository
    main_repo = GitRepo(repos_dir / "main-repo")
    main_repo.init()
    main_repo.add_file("README.md", "# Main Repository with Nested Subtrees")
    main_repo.commit("Initial commit")

    # Create first-level subtree repository (will contain its own subtree)
    level1_repo_bare = GitRepo(repos_dir / "level1-repo-bare", bare=True)
    level1_repo_bare.init()

    level1_work = GitRepo(repos_dir / "level1-work")
    level1_work.init()
    level1_work.add_file("level1.py", "# Level 1 code")
    level1_work.commit("Initial level 1 commit")
    level1_work.add_remote("origin", str(level1_repo_bare.path))
    level1_work.run_git("push", "origin", "main")

    # Create second-level subtree repository
    level2_repo_bare = GitRepo(repos_dir / "level2-repo-bare", bare=True)
    level2_repo_bare.init()

    level2_work = GitRepo(repos_dir / "level2-work")
    level2_work.init()
    level2_work.add_file("level2.py", "# Level 2 code")
    level2_work.commit("Initial level 2 commit")
    level2_work.add_remote("origin", str(level2_repo_bare.path))
    level2_work.run_git("push", "origin", "main")

    # Add level2 as a subtree to level1
    level1_work.add_subtree("nested", str(level2_repo_bare.path), "main")
    level1_work.add_subtree_config("nested", str(level2_repo_bare.path), "main")
    level1_work.run_git("push", "origin", "main")

    # Add level1 as a subtree to main
    main_repo.add_subtree("lib", str(level1_repo_bare.path), "main")
    main_repo.add_subtree_config("lib", str(level1_repo_bare.path), "main")

    # Create bare repo for main
    main_repo_bare = GitRepo(repos_dir / "main-repo-bare", bare=True)
    main_repo_bare.init()
    main_repo.add_remote("origin", str(main_repo_bare.path))
    main_repo.run_git("push", "origin", "main")

    return {
        "main": main_repo,
        "main_bare": main_repo_bare,
        "level1_bare": level1_repo_bare,
        "level1_work": level1_work,
        "level2_bare": level2_repo_bare,
        "level2_work": level2_work,
    }


def verify_push_occurred(bare_repo, branch="main"):
    """Verify that a push occurred to a bare repository."""
    refs = bare_repo.get_refs()
    ref_to_check = f"refs/heads/{branch}"
    return any(ref_to_check in ref for ref in refs)
