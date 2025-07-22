"""Test configuration for git-rp tests."""

import sys
from pathlib import Path

# Add parent directory to Python path so we can import git-rp modules
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

# Test configuration
TEST_TIMEOUT = 30  # seconds
TEST_BRANCH = "main"
TEST_USER_NAME = "Test User"
TEST_USER_EMAIL = "test@example.com"

# Error messages we expect to see
ERROR_NOT_GIT_REPO = "Error: Not in a git repository"

# Test commit messages
COMMIT_MESSAGES = {
    "initial": "Initial commit",
    "update": "Update files",
    "feature": "Add new feature",
    "nested": "Add nested content",
}
