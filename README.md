# git-tools

A collection of Git utilities to enhance your workflow.

## Tools

### git-refs
Display all refs (branches, tags, etc.) that point to the current commit or a specified commit.

**Usage:**
```bash
git-refs                  # Show refs for current commit
git-refs abc123           # Show refs for specific commit
git-refs HEAD~3           # Show refs for 3 commits ago
```

### git-rp (Recursive Push)
Push to main repository and all configured subtrees in one command. Now supports recursive nested subtrees!

**Features:**
- Push to main repository and all subtrees with one command
- Supports nested subtrees (subtrees within subtrees)
- Dry run mode to preview what will be pushed
- Force push support

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

### Quick Install

Use the provided install script to symlink all tools to `~/.local/bin`:

```bash
python3 install.py        # Install all tools
python3 install.py -l     # List available tools
python3 install.py -u     # Uninstall all tools
python3 install.py -f     # Force overwrite existing symlinks
```

The install script will:
- Create `~/.local/bin` if it doesn't exist
- Create symlinks for all git tools
- Check if `~/.local/bin` is in your PATH
- Use colored output to show success/warnings/errors

If `~/.local/bin` is not in your PATH, add this to your shell configuration:
```bash
export PATH="$PATH:$HOME/.local/bin"
```

### Manual Installation

1. Clone this repository
2. Add each tool's directory to your PATH, or
3. Copy/symlink the scripts to a directory in your PATH

## Directory Structure

```
git-tools/
├── refs/
│   └── git-refs       # Display refs pointing to commits
├── stree/
│   ├── git-rp         # Recursive push for subtrees
│   └── util.py        # Utility functions for git-rp
├── sync/
│   └── git-sync       # Sync branches with remotes
└── install.py         # Installation script
```

## Requirements

- Python 3
- Git with subtree support (for git-rp)
- SSH access to remote repositories (for git-sync)
