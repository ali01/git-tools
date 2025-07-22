# git-rp Integration Tests

Comprehensive test suite for the git-rp (recursive push) tool.

## Test Structure

- `test_fixtures.py` - Helper classes and functions for creating test git repositories
- `test_config.py` - Test configuration and constants
- `test_git_rp.py` - Main test suite with all test cases

## Running Tests

### Setup

Install test dependencies:
```bash
pip install -r requirements-test.txt
```

### Run All Tests

```bash
# From the stree directory
pytest tests/

# With coverage
pytest tests/ --cov=git_rp --cov-report=html

# Verbose output
pytest tests/ -v

# Run specific test class
pytest tests/test_git_rp.py::TestBasicFunctionality -v

# Run specific test
pytest tests/test_git_rp.py::TestBasicFunctionality::test_get_current_branch -v
```

### Test Categories

1. **Basic Functionality** - Command line parsing, branch detection, main repo push
2. **Subtree Operations** - Single and multiple subtree pushes
3. **Nested Subtrees** - Recursive detection and pushing of nested subtrees
4. **Error Handling** - Invalid repos, missing remotes, unreachable URLs
5. **Dry Run Mode** - Testing the -n flag
6. **Force Push** - Testing the -f flag
7. **Branch Operations** - Custom branch pushing
8. **Complete Integration** - End-to-end workflows

## Test Environment

Tests use temporary directories and local file:// URLs for git remotes. No actual GitHub repositories are required. Each test is isolated and cleans up after itself.

## Coverage Goals

The test suite aims for 100% code coverage of the git-rp tool, including:
- All command line options
- All error paths
- Edge cases (empty repos, no commits, etc.)
- Nested subtree recursion
