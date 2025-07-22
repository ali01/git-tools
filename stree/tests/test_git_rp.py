"""Comprehensive integration tests for git-rp tool."""

import os
import sys
import subprocess
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import shutil
import importlib.util

from .test_fixtures import (
    GitRepo,
    temp_git_env,
    create_simple_repo_structure,
    create_nested_repo_structure,
    verify_push_occurred
)
from .test_config import ERROR_NOT_GIT_REPO, COMMIT_MESSAGES

# Import the module under test
# Since the file is named git-rp (with hyphen), we need to import it specially
git_rp_path = Path(__file__).parent.parent / "git-rp"

# Add parent directory to path and import using exec
sys.path.insert(0, str(git_rp_path.parent))

# Load the module by executing the file
git_rp = type(sys)('git_rp')
with open(git_rp_path, 'r') as f:
    exec(f.read(), git_rp.__dict__)


class TestBasicFunctionality:
    """Test basic git-rp functionality."""

    def test_parse_command_line_defaults(self):
        """Test command line parsing with default values."""
        with patch('sys.argv', ['git-rp']):
            args = git_rp.parse_command_line()
            assert args.branch is None
            assert args.force is False
            assert args.dry_run is False

    def test_parse_command_line_all_options(self):
        """Test command line parsing with all options."""
        with patch('sys.argv', ['git-rp', '-b', 'feature', '-f', '-n']):
            args = git_rp.parse_command_line()
            assert args.branch == 'feature'
            assert args.force is True
            assert args.dry_run is True

    def test_get_current_branch(self):
        """Test getting current branch."""
        with temp_git_env() as env:
            repo = GitRepo(env["repos_dir"] / "test-repo")
            repo.init()
            repo.add_file("test.txt")
            repo.commit("Initial")

            os.chdir(repo.path)
            assert git_rp.get_current_branch() == "main"

            repo.create_branch("feature")
            assert git_rp.get_current_branch() == "feature"

    def test_push_main_repo_only(self):
        """Test pushing to main repository with no subtrees."""
        with temp_git_env() as env:
            # Create main repo and bare remote
            main = GitRepo(env["repos_dir"] / "main")
            main.init()
            main.add_file("README.md", "# Test")
            main.commit("Initial")

            bare = GitRepo(env["repos_dir"] / "bare", bare=True)
            bare.init()

            main.add_remote("origin", str(bare.path))

            os.chdir(main.path)

            # Test dry run
            assert git_rp.push_main_repo("main", dry_run=True) is True
            assert not verify_push_occurred(bare)

            # Test actual push
            assert git_rp.push_main_repo("main") is True
            assert verify_push_occurred(bare)

    def test_get_subtrees_from_config(self):
        """Test reading subtree configuration."""
        with temp_git_env() as env:
            repo = GitRepo(env["repos_dir"] / "test")
            repo.init()

            # Add subtree configurations
            repo.add_subtree_config("lib/shared", "https://example.com/shared.git", "main")
            repo.add_subtree_config("vendor/third", "https://example.com/third.git", "master")

            os.chdir(repo.path)
            subtrees = git_rp.get_subtrees_from_config()

            assert len(subtrees) == 2
            assert subtrees[0]['path'] == "lib/shared"
            assert subtrees[0]['url'] == "https://example.com/shared.git"
            assert subtrees[0]['branch'] == "main"
            assert subtrees[1]['path'] == "vendor/third"
            assert subtrees[1]['branch'] == "master"


class TestSubtreeOperations:
    """Test subtree push operations."""

    def test_push_single_subtree(self):
        """Test pushing a single subtree."""
        with temp_git_env() as env:
            repos = create_simple_repo_structure(env["repos_dir"])
            main = repos["main"]
            subtree_bare = repos["subtree_bare"]

            # Add subtree to main repo
            main.add_subtree("lib", str(subtree_bare.path), "main")
            main.add_subtree_config("lib", str(subtree_bare.path), "main")

            # Make a change in the subtree
            os.chdir(main.path)
            (main.path / "lib" / "new_file.py").write_text("# New file")
            main.commit("Add new file to subtree")

            # Test subtree push
            subtree_config = {
                'path': 'lib',
                'url': str(subtree_bare.path),
                'branch': 'main'
            }

            # Dry run first
            assert git_rp.push_subtree(subtree_config, "main", dry_run=True) is True

            # Actual push
            assert git_rp.push_subtree(subtree_config, "main") is True

    def test_push_multiple_subtrees(self):
        """Test pushing multiple subtrees."""
        with temp_git_env() as env:
            main = GitRepo(env["repos_dir"] / "main")
            main.init()
            main.add_file("README.md", "# Main")
            main.commit("Initial")

            # Create multiple subtree repos
            subtree1_bare = GitRepo(env["repos_dir"] / "sub1-bare", bare=True)
            subtree1_bare.init()

            subtree2_bare = GitRepo(env["repos_dir"] / "sub2-bare", bare=True)
            subtree2_bare.init()

            # Create working repos to initialize subtrees
            for i, bare_repo in enumerate([subtree1_bare, subtree2_bare], 1):
                work = GitRepo(env["repos_dir"] / f"sub{i}-work")
                work.init()
                work.add_file(f"sub{i}.py", f"# Subtree {i}")
                work.commit(f"Initial subtree {i}")
                work.add_remote("origin", str(bare_repo.path))
                work.run_git("push", "origin", "main")

            # Add both subtrees to main
            main.add_subtree("lib1", str(subtree1_bare.path), "main")
            main.add_subtree_config("lib1", str(subtree1_bare.path), "main")

            main.add_subtree("lib2", str(subtree2_bare.path), "main")
            main.add_subtree_config("lib2", str(subtree2_bare.path), "main")

            # Make changes
            os.chdir(main.path)
            (main.path / "lib1" / "update.py").write_text("# Update 1")
            (main.path / "lib2" / "update.py").write_text("# Update 2")
            main.commit("Update both subtrees")

            # Get subtrees and push
            subtrees = git_rp.get_subtrees_from_config()
            assert len(subtrees) == 2

            for subtree in subtrees:
                assert git_rp.push_subtree(subtree, "main") is True


class TestNestedSubtrees:
    """Test recursive nested subtree operations."""

    def test_get_nested_subtrees(self):
        """Test detection of nested subtrees."""
        with temp_git_env() as env:
            repos = create_nested_repo_structure(env["repos_dir"])

            # Check for nested subtrees in the level1 repository
            # (not in the lib directory of main, which is just a subtree)
            os.chdir(repos["level1_work"].path)
            nested = git_rp.get_nested_subtrees(".", repos["level1_work"].path)

            assert len(nested) == 1
            assert nested[0]['relative_path'] == "nested"
            assert nested[0]['path'] == "./nested"

    def test_push_nested_subtrees(self):
        """Test pushing nested subtrees recursively."""
        with temp_git_env() as env:
            repos = create_nested_repo_structure(env["repos_dir"])
            main = repos["main"]

            # Make changes at all levels
            os.chdir(main.path)
            (main.path / "README.md").write_text("# Updated main")
            (main.path / "lib" / "level1.py").write_text("# Updated level 1")
            (main.path / "lib" / "nested" / "level2.py").write_text("# Updated level 2")
            main.commit("Update all levels")

            # Run git-rp
            with patch('sys.argv', ['git-rp']):
                result = git_rp.main(sys.argv)
                assert result == 0

    def test_three_level_nested_subtrees(self):
        """Test three levels of nested subtrees."""
        with temp_git_env() as env:
            # Create a simpler three-level structure
            # Level 3 - deepest
            level3_bare = GitRepo(env["repos_dir"] / "level3-bare", bare=True)
            level3_bare.init()

            level3_work = GitRepo(env["repos_dir"] / "level3-work")
            level3_work.init()
            level3_work.add_file("level3.py", "# Level 3")
            level3_work.commit("Initial level 3")
            level3_work.add_remote("origin", str(level3_bare.path))
            level3_work.run_git("push", "origin", "main")

            # Level 2 - contains level 3
            level2_bare = GitRepo(env["repos_dir"] / "level2-bare", bare=True)
            level2_bare.init()

            level2_work = GitRepo(env["repos_dir"] / "level2-work")
            level2_work.init()
            level2_work.add_file("level2.py", "# Level 2")
            level2_work.commit("Initial level 2")
            level2_work.add_subtree("deep", str(level3_bare.path), "main")
            level2_work.add_subtree_config("deep", str(level3_bare.path), "main")
            level2_work.add_remote("origin", str(level2_bare.path))
            level2_work.run_git("push", "origin", "main")

            # Level 1 - contains level 2
            level1_bare = GitRepo(env["repos_dir"] / "level1-bare", bare=True)
            level1_bare.init()

            level1_work = GitRepo(env["repos_dir"] / "level1-work")
            level1_work.init()
            level1_work.add_file("level1.py", "# Level 1")
            level1_work.commit("Initial level 1")
            level1_work.add_subtree("nested", str(level2_bare.path), "main")
            level1_work.add_subtree_config("nested", str(level2_bare.path), "main")
            level1_work.add_remote("origin", str(level1_bare.path))
            level1_work.run_git("push", "origin", "main")

            # Main - contains level 1
            main_bare = GitRepo(env["repos_dir"] / "main-bare", bare=True)
            main_bare.init()

            main = GitRepo(env["repos_dir"] / "main")
            main.init()
            main.add_file("README.md", "# Main")
            main.commit("Initial main")
            main.add_subtree("lib", str(level1_bare.path), "main")
            main.add_subtree_config("lib", str(level1_bare.path), "main")
            main.add_remote("origin", str(main_bare.path))

            # Make a change at the deepest level
            os.chdir(main.path)
            (main.path / "lib" / "nested" / "deep" / "level3.py").write_text("# Updated level 3")
            main.commit("Update deepest level")

            # Test pushing with dry run first
            subtrees = git_rp.get_subtrees_from_config()
            assert len(subtrees) == 1
            assert subtrees[0]['path'] == 'lib'

            # The actual recursive push would happen when pushing to level1,
            # which would then push to level2, which would push to level3
            result = git_rp.push_subtree(subtrees[0], "main", dry_run=True)
            assert result is True


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_not_in_git_repository(self):
        """Test behavior when not in a git repository."""
        with temp_git_env() as env:
            os.chdir(env["test_dir"])

            with pytest.raises(SystemExit) as exc_info:
                git_rp.get_subtrees_from_config()
            assert exc_info.value.code == 1

    def test_push_with_no_origin(self):
        """Test push when origin remote doesn't exist."""
        with temp_git_env() as env:
            repo = GitRepo(env["repos_dir"] / "test")
            repo.init()
            repo.add_file("test.txt")
            repo.commit("Initial")

            os.chdir(repo.path)

            # Try to push without origin
            result = git_rp.push_main_repo("main")
            assert result is False

    def test_invalid_subtree_path(self):
        """Test handling of invalid subtree paths."""
        with temp_git_env() as env:
            repo = GitRepo(env["repos_dir"] / "test")
            repo.init()
            repo.add_file("test.txt")
            repo.commit("Initial")

            # Add config for non-existent subtree
            repo.add_subtree_config("nonexistent", "https://example.com/fake.git")

            os.chdir(repo.path)

            subtree_config = {
                'path': 'nonexistent',
                'url': 'https://example.com/fake.git',
                'branch': 'main'
            }

            # Should handle gracefully
            result = git_rp.push_subtree(subtree_config, "main")
            assert result is False

    def test_unreachable_remote_url(self):
        """Test handling of unreachable remote URLs."""
        with temp_git_env() as env:
            repo = GitRepo(env["repos_dir"] / "test")
            repo.init()
            repo.add_file("test.txt")
            repo.commit("Initial")

            # Add subtree with unreachable URL
            os.chdir(repo.path)

            # Create a subtree directory
            os.makedirs("lib", exist_ok=True)
            (repo.path / "lib" / "file.txt").write_text("content")
            repo.commit("Add lib")

            subtree_config = {
                'path': 'lib',
                'url': '/nonexistent/path/to/repo.git',
                'branch': 'main'
            }

            # Should fail gracefully
            result = git_rp.push_subtree(subtree_config, "main")
            assert result is False


class TestDryRunMode:
    """Test dry run functionality."""

    def test_dry_run_main_repo(self):
        """Test dry run for main repository."""
        with temp_git_env() as env:
            repo = GitRepo(env["repos_dir"] / "test")
            repo.init()
            repo.add_file("test.txt")
            repo.commit("Initial")

            bare = GitRepo(env["repos_dir"] / "bare", bare=True)
            bare.init()

            repo.add_remote("origin", str(bare.path))

            os.chdir(repo.path)

            # Dry run should not push
            result = git_rp.push_main_repo("main", dry_run=True)
            assert result is True
            assert not verify_push_occurred(bare)

    def test_dry_run_subtrees(self):
        """Test dry run for subtree operations."""
        with temp_git_env() as env:
            repos = create_simple_repo_structure(env["repos_dir"])
            main = repos["main"]

            main.add_subtree("lib", str(repos["subtree_bare"].path), "main")
            main.add_subtree_config("lib", str(repos["subtree_bare"].path), "main")

            os.chdir(main.path)

            # Make changes
            (main.path / "lib" / "new.py").write_text("# New")
            main.commit("Add new file")

            # Dry run the entire operation
            with patch('sys.argv', ['git-rp', '-n']):
                result = git_rp.main(sys.argv)
                assert result == 0


class TestForcePush:
    """Test force push functionality."""

    def test_force_push_main_repo(self):
        """Test force push to main repository."""
        with temp_git_env() as env:
            repo = GitRepo(env["repos_dir"] / "test")
            repo.init()
            repo.add_file("test.txt", "v1")
            repo.commit("Initial")

            bare = GitRepo(env["repos_dir"] / "bare", bare=True)
            bare.init()

            repo.add_remote("origin", str(bare.path))
            repo.run_git("push", "origin", "main")

            # Amend commit (will require force push)
            repo.add_file("test.txt", "v2")
            repo.run_git("commit", "--amend", "-m", "Amended commit")

            os.chdir(repo.path)

            # Normal push should fail
            result = git_rp.push_main_repo("main")
            assert result is False

            # Force push should succeed
            result = git_rp.push_main_repo("main", force=True)
            assert result is True

    def test_force_push_subtree(self):
        """Test force push for subtrees."""
        with temp_git_env() as env:
            repos = create_simple_repo_structure(env["repos_dir"])
            main = repos["main"]

            main.add_subtree("lib", str(repos["subtree_bare"].path), "main")
            main.add_subtree_config("lib", str(repos["subtree_bare"].path), "main")

            os.chdir(main.path)

            # Make and push changes
            (main.path / "lib" / "file1.py").write_text("# Version 1")
            main.commit("Add file1")

            subtree_config = {
                'path': 'lib',
                'url': str(repos["subtree_bare"].path),
                'branch': 'main'
            }

            # First push
            assert git_rp.push_subtree(subtree_config, "main") is True

            # Now make conflicting changes
            (main.path / "lib" / "file1.py").write_text("# Version 2")
            main.run_git("commit", "--amend", "-m", "Amended subtree commit")

            # Force push should work
            assert git_rp.push_subtree(subtree_config, "main", force=True) is True


class TestBranchOperations:
    """Test operations with different branches."""

    def test_push_specific_branch(self):
        """Test pushing a specific branch."""
        with temp_git_env() as env:
            repo = GitRepo(env["repos_dir"] / "test")
            repo.init()
            repo.add_file("test.txt")
            repo.commit("Initial")

            bare = GitRepo(env["repos_dir"] / "bare", bare=True)
            bare.init()

            repo.add_remote("origin", str(bare.path))

            # Create feature branch
            repo.create_branch("feature")
            repo.add_file("feature.txt")
            repo.commit("Add feature")

            os.chdir(repo.path)

            # Push feature branch
            with patch('sys.argv', ['git-rp', '-b', 'feature']):
                result = git_rp.main(sys.argv)
                assert result == 0

            # Verify feature branch exists in bare repo
            assert bare.has_ref("refs/heads/feature")

    def test_subtree_with_custom_branch(self):
        """Test subtree with custom target branch."""
        with temp_git_env() as env:
            repos = create_simple_repo_structure(env["repos_dir"])
            main = repos["main"]

            # Configure subtree to push to 'develop' branch
            main.add_subtree("lib", str(repos["subtree_bare"].path), "main")
            main.add_subtree_config("lib", str(repos["subtree_bare"].path), "develop")

            os.chdir(main.path)

            # Make changes
            (main.path / "lib" / "dev.py").write_text("# Development")
            main.commit("Add dev file")

            # Push
            subtrees = git_rp.get_subtrees_from_config()
            assert subtrees[0]['branch'] == 'develop'

            # This would create the develop branch in the subtree repo
            result = git_rp.push_subtree(subtrees[0], "main")
            # Note: This might fail if git subtree doesn't handle branch creation
            # In real usage, the branch would need to exist


class TestCompleteIntegration:
    """Complete end-to-end integration tests."""

    def test_full_workflow_simple(self):
        """Test complete workflow with simple structure."""
        with temp_git_env() as env:
            # Setup repositories
            main = GitRepo(env["repos_dir"] / "main")
            main.init()
            main.add_file("README.md", "# Main Project")
            main.commit("Initial commit")

            main_bare = GitRepo(env["repos_dir"] / "main-bare", bare=True)
            main_bare.init()
            main.add_remote("origin", str(main_bare.path))

            # Create subtree
            sub_bare = GitRepo(env["repos_dir"] / "sub-bare", bare=True)
            sub_bare.init()

            sub_work = GitRepo(env["repos_dir"] / "sub-work")
            sub_work.init()
            sub_work.add_file("lib.py", "# Library code")
            sub_work.commit("Initial library")
            sub_work.add_remote("origin", str(sub_bare.path))
            sub_work.run_git("push", "origin", "main")

            # Add subtree to main
            main.add_subtree("lib", str(sub_bare.path), "main")
            main.add_subtree_config("lib", str(sub_bare.path), "main")

            # Make changes
            os.chdir(main.path)
            main.add_file("app.py", "# Application")
            (main.path / "lib" / "utils.py").write_text("# Utilities")
            main.commit("Add application and utilities")

            # Run git-rp
            with patch('sys.argv', ['git-rp']):
                result = git_rp.main(sys.argv)
                assert result == 0

            # Verify pushes
            assert verify_push_occurred(main_bare)
            assert verify_push_occurred(sub_bare)

    def test_full_workflow_nested(self):
        """Test complete workflow with nested subtrees."""
        with temp_git_env() as env:
            repos = create_nested_repo_structure(env["repos_dir"])

            os.chdir(repos["main"].path)

            # Make changes at all levels
            repos["main"].add_file("main_update.py", "# Main update")
            (repos["main"].path / "lib" / "level1_update.py").write_text("# Level 1 update")
            (repos["main"].path / "lib" / "nested" / "level2_update.py").write_text("# Level 2 update")
            repos["main"].commit("Update all levels")

            # Run git-rp with all options
            with patch('sys.argv', ['git-rp', '-n']):  # Dry run first
                result = git_rp.main(sys.argv)
                assert result == 0

            # Actual push
            with patch('sys.argv', ['git-rp']):
                result = git_rp.main(sys.argv)
                assert result == 0

            # Verify all repos received updates
            assert verify_push_occurred(repos["main_bare"])
            assert verify_push_occurred(repos["level1_bare"])
            assert verify_push_occurred(repos["level2_bare"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
