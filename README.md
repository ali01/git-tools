# git-tools

A collection of Git utilities to enhance your workflow.

## Tools

### git-rp (Recursive Push)
Push to main repository and all configured subtrees in one command.

**Setup:**
Add subtree configuration to your `.git/config`:
```ini
[subtree "path/to/subtree"]
    url = https://github.com/user/repo.git
    branch = main
```

**Usage:**
```bash
git-rp                    # Push current branch
git-rp -b feature-branch  # Push specific branch
git-rp -f                 # Force push
git-rp -n                 # Dry run
```

### git-sync
Synchronize local branches with remote repositories via SSH.

**Usage:**
```bash
git-sync                  # Sync with origin
git-sync remote1 remote2  # Sync with multiple remotes
git-sync -c "command"     # Run command after sync
```

## Installation

1. Clone this repository
2. Add the directory to your PATH
3. Make scripts executable: `chmod +x git-*`

## Requirements

- Python 3
- Git with subtree support (for git-rp)
- SSH access to remote repositories (for git-sync)