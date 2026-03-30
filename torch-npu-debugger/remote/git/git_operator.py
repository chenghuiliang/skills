# Git operations on remote servers
# All comments in this file are in English per project guidelines

import re
from datetime import datetime
from typing import List, Optional

from remote.core.exceptions import GitError
from remote.core.session_manager import RemoteSessionManager
from remote.models.data_models import GitStatus, CommitInfo


class RemoteGitOperator:
    """Performs git operations on remote repositories.

    Example:
        session = RemoteSessionManager("dev@server")
        git = RemoteGitOperator(session)

        # Check status
        status = git.status("/home/dev/torch_npu")
        print(f"Current branch: {status.branch}")

        # Create branch and commit
        git.create_branch("/home/dev/torch_npu", "feature-branch")
        git.commit("/home/dev/torch_npu", "Add new feature")
        git.push("/home/dev/torch_npu")
    """

    def __init__(self, session: RemoteSessionManager):
        """Initialize git operator.

        Args:
            session: Connected SSH session manager
        """
        self.session = session

    def _run_git(
        self,
        repo_dir: str,
        command: str,
        timeout: int = 30
    ) -> tuple:
        """Run a git command in the repository.

        Args:
            repo_dir: Path to git repository
            command: Git command (without 'git' prefix)
            timeout: Command timeout

        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        full_command = f"cd {repo_dir} && git {command}"
        return self.session.execute_command(full_command, timeout=timeout)

    def status(self, repo_dir: str) -> GitStatus:
        """Get git repository status.

        Args:
            repo_dir: Path to git repository

        Returns:
            GitStatus: Repository status

        Raises:
            GitError: If status check fails
        """
        try:
            # Get current branch
            exit_code, stdout, stderr = self._run_git(
                repo_dir, "rev-parse --abbrev-ref HEAD", timeout=10
            )
            if exit_code != 0:
                raise GitError(f"Not a git repository: {repo_dir}")
            branch = stdout.strip()

            # Get status in porcelain format
            exit_code, stdout, stderr = self._run_git(
                repo_dir, "status --porcelain -b", timeout=10
            )

            modified_files = []
            staged_files = []
            untracked_files = []
            ahead_count = 0
            behind_count = 0

            for line in stdout.splitlines():
                if line.startswith("##"):
                    # Branch info line
                    match = re.search(r'\[ahead (\d+)', line)
                    if match:
                        ahead_count = int(match.group(1))
                    match = re.search(r'behind (\d+)', line)
                    if match:
                        behind_count = int(match.group(1))
                elif len(line) >= 2:
                    index_status = line[0]
                    worktree_status = line[1]
                    filename = line[3:].strip()

                    if index_status != ' ' and index_status != '?':
                        staged_files.append(filename)
                    if worktree_status != ' ':
                        modified_files.append(filename)
                    if index_status == '?':
                        untracked_files.append(filename)

            # Get last commit info
            last_commit_hash = None
            last_commit_message = None
            try:
                exit_code, stdout, _ = self._run_git(
                    repo_dir, "log -1 --format=%H%n%s", timeout=10
                )
                if exit_code == 0:
                    lines = stdout.strip().split('\n', 1)
                    if len(lines) >= 1:
                        last_commit_hash = lines[0]
                    if len(lines) >= 2:
                        last_commit_message = lines[1]
            except Exception:
                pass

            is_clean = (
                len(modified_files) == 0 and
                len(staged_files) == 0 and
                len(untracked_files) == 0
            )

            return GitStatus(
                branch=branch,
                is_clean=is_clean,
                modified_files=modified_files,
                staged_files=staged_files,
                untracked_files=untracked_files,
                ahead_count=ahead_count,
                behind_count=behind_count,
                last_commit_hash=last_commit_hash,
                last_commit_message=last_commit_message
            )

        except GitError:
            raise
        except Exception as e:
            raise GitError(f"Failed to get git status: {e}") from e

    def diff(self, repo_dir: str, ref: str = "HEAD", target_ref: Optional[str] = None) -> str:
        """Get git diff.

        Args:
            repo_dir: Path to git repository
            ref: Git reference (default: HEAD)
            target_ref: Target reference for comparison

        Returns:
            str: Diff output
        """
        if target_ref:
            command = f"diff {ref} {target_ref}"
        else:
            command = f"diff {ref}"

        exit_code, stdout, stderr = self._run_git(repo_dir, command, timeout=30)

        if exit_code != 0:
            raise GitError(f"Git diff failed: {stderr}")

        return stdout

    def log(
        self,
        repo_dir: str,
        n: int = 10,
        author: Optional[str] = None,
        since: Optional[str] = None,
        path: Optional[str] = None
    ) -> List[CommitInfo]:
        """Get commit history.

        Args:
            repo_dir: Path to git repository
            n: Number of commits to retrieve
            author: Filter by author
            since: Filter by date (e.g., "1 week ago")
            path: Filter by file path

        Returns:
            List[CommitInfo]: List of commits
        """
        format_str = "%H|%h|%an|%ae|%at|%s|%b%x00"
        command = f"log -n {n} --format='{format_str}'"

        if author:
            command += f" --author='{author}'"
        if since:
            command += f" --since='{since}'"
        if path:
            command += f" -- {path}"

        exit_code, stdout, stderr = self._run_git(repo_dir, command, timeout=30)

        if exit_code != 0:
            raise GitError(f"Git log failed: {stderr}")

        commits = []
        entries = stdout.split('\x00')

        for entry in entries:
            entry = entry.strip()
            if not entry:
                continue

            parts = entry.split('|', 6)
            if len(parts) < 6:
                continue

            hash_full = parts[0]
            hash_short = parts[1]
            author = parts[2]
            email = parts[3]
            timestamp = int(parts[4])
            subject = parts[5]
            body = parts[6] if len(parts) > 6 else ""

            # Get stats for this commit
            files_changed = []
            insertions = 0
            deletions = 0

            try:
                stat_exit, stat_out, _ = self._run_git(
                    repo_dir, f"show --stat --format='' {hash_full}", timeout=10
                )
                if stat_exit == 0:
                    # Parse stats
                    for line in stat_out.splitlines():
                        if '|' in line:
                            filename = line.split('|')[0].strip()
                            files_changed.append(filename)

                    # Get total insertions/deletions
                    total_match = re.search(r'(\d+) insertion', stat_out)
                    if total_match:
                        insertions = int(total_match.group(1))
                    total_match = re.search(r'(\d+) deletion', stat_out)
                    if total_match:
                        deletions = int(total_match.group(1))
            except Exception:
                pass

            commits.append(CommitInfo(
                hash=hash_full,
                short_hash=hash_short,
                author=author,
                email=email,
                date=datetime.fromtimestamp(timestamp),
                message=subject + ("\n" + body if body else ""),
                subject=subject,
                body=body,
                files_changed=files_changed,
                insertions=insertions,
                deletions=deletions
            ))

        return commits

    def checkout(self, repo_dir: str, branch: str, create: bool = False) -> None:
        """Checkout a branch.

        Args:
            repo_dir: Path to git repository
            branch: Branch name to checkout
            create: Whether to create the branch if it doesn't exist

        Raises:
            GitError: If checkout fails
        """
        if create:
            command = f"checkout -b {branch}"
        else:
            command = f"checkout {branch}"

        exit_code, stdout, stderr = self._run_git(repo_dir, command, timeout=30)

        if exit_code != 0:
            raise GitError(f"Git checkout failed: {stderr}")

    def create_branch(
        self,
        repo_dir: str,
        branch: str,
        base: Optional[str] = None
    ) -> None:
        """Create a new branch.

        Args:
            repo_dir: Path to git repository
            branch: New branch name
            base: Base branch/commit (default: current HEAD)

        Raises:
            GitError: If branch creation fails
        """
        if base:
            command = f"checkout -b {branch} {base}"
        else:
            command = f"checkout -b {branch}"

        exit_code, stdout, stderr = self._run_git(repo_dir, command, timeout=30)

        if exit_code != 0:
            raise GitError(f"Failed to create branch: {stderr}")

    def delete_branch(
        self,
        repo_dir: str,
        branch: str,
        force: bool = False,
        remote: bool = False
    ) -> None:
        """Delete a branch.

        Args:
            repo_dir: Path to git repository
            branch: Branch name to delete
            force: Force delete even if not merged
            remote: Delete remote branch

        Raises:
            GitError: If deletion fails
        """
        if remote:
            command = f"push origin --delete {branch}"
        elif force:
            command = f"branch -D {branch}"
        else:
            command = f"branch -d {branch}"

        exit_code, stdout, stderr = self._run_git(repo_dir, command, timeout=30)

        if exit_code != 0:
            raise GitError(f"Failed to delete branch: {stderr}")

    def commit(
        self,
        repo_dir: str,
        message: str,
        files: Optional[List[str]] = None,
        amend: bool = False
    ) -> str:
        """Create a git commit.

        Args:
            repo_dir: Path to git repository
            message: Commit message
            files: Specific files to commit (None for all staged)
            amend: Amend the last commit

        Returns:
            str: Commit hash

        Raises:
            GitError: If commit fails
        """
        # Stage files if specified
        if files:
            for file in files:
                exit_code, _, stderr = self._run_git(repo_dir, f"add {file}", timeout=10)
                if exit_code != 0:
                    raise GitError(f"Failed to stage {file}: {stderr}")

        # Create commit
        if amend:
            command = f'commit --amend --no-edit -m "{message}"'
        else:
            # Escape quotes in message
            escaped_message = message.replace('"', '\\"')
            command = f'commit -m "{escaped_message}"'

        exit_code, stdout, stderr = self._run_git(repo_dir, command, timeout=30)

        if exit_code != 0:
            raise GitError(f"Git commit failed: {stderr}")

        # Get commit hash
        exit_code, stdout, _ = self._run_git(repo_dir, "rev-parse HEAD", timeout=10)
        return stdout.strip()

    def push(
        self,
        repo_dir: str,
        remote: str = "origin",
        branch: Optional[str] = None,
        force: bool = False,
        set_upstream: bool = False
    ) -> None:
        """Push to remote.

        Args:
            repo_dir: Path to git repository
            remote: Remote name
            branch: Branch to push (None for current)
            force: Force push
            set_upstream: Set upstream tracking

        Raises:
            GitError: If push fails
        """
        command = "push"

        if force:
            command += " --force"
        if set_upstream:
            command += " -u"

        command += f" {remote}"

        if branch:
            command += f" {branch}"

        exit_code, stdout, stderr = self._run_git(repo_dir, command, timeout=60)

        if exit_code != 0:
            raise GitError(f"Git push failed: {stderr}")

    def pull(
        self,
        repo_dir: str,
        remote: str = "origin",
        branch: Optional[str] = None,
        rebase: bool = False
    ) -> None:
        """Pull from remote.

        Args:
            repo_dir: Path to git repository
            remote: Remote name
            branch: Branch to pull (None for current)
            rebase: Rebase instead of merge

        Raises:
            GitError: If pull fails
        """
        command = "pull"

        if rebase:
            command += " --rebase"

        command += f" {remote}"

        if branch:
            command += f" {branch}"

        exit_code, stdout, stderr = self._run_git(repo_dir, command, timeout=60)

        if exit_code != 0:
            raise GitError(f"Git pull failed: {stderr}")

    def stash(self, repo_dir: str, message: Optional[str] = None) -> str:
        """Stash changes.

        Args:
            repo_dir: Path to git repository
            message: Stash message

        Returns:
            str: Stash reference (e.g., "stash@{0}")
        """
        if message:
            escaped_message = message.replace('"', '\\"')
            command = f'stash push -m "{escaped_message}"'
        else:
            command = "stash push"

        exit_code, stdout, stderr = self._run_git(repo_dir, command, timeout=30)

        if exit_code != 0:
            raise GitError(f"Git stash failed: {stderr}")

        # Return the most recent stash
        return "stash@{0}"

    def stash_pop(self, repo_dir: str, stash_ref: str = "stash@{0}") -> None:
        """Pop a stash.

        Args:
            repo_dir: Path to git repository
            stash_ref: Stash reference to pop

        Raises:
            GitError: If pop fails
        """
        command = f"stash pop {stash_ref}"

        exit_code, stdout, stderr = self._run_git(repo_dir, command, timeout=30)

        if exit_code != 0:
            raise GitError(f"Git stash pop failed: {stderr}")

    def stash_list(self, repo_dir: str) -> List[dict]:
        """List stashes.

        Args:
            repo_dir: Path to git repository

        Returns:
            List of stash info dictionaries
        """
        command = 'stash list --format="%H|%gd|%ar|%s"'

        exit_code, stdout, stderr = self._run_git(repo_dir, command, timeout=10)

        if exit_code != 0:
            return []

        stashes = []
        for line in stdout.strip().split('\n'):
            if not line:
                continue
            parts = line.split('|', 3)
            if len(parts) >= 3:
                stashes.append({
                    'hash': parts[0],
                    'ref': parts[1],
                    'date': parts[2],
                    'message': parts[3] if len(parts) > 3 else ""
                })

        return stashes

    def reset(
        self,
        repo_dir: str,
        ref: str = "HEAD",
        hard: bool = False,
        soft: bool = False
    ) -> None:
        """Reset repository.

        Args:
            repo_dir: Path to git repository
            ref: Reference to reset to
            hard: Hard reset (discard changes)
            soft: Soft reset

        Raises:
            GitError: If reset fails
        """
        command = "reset"

        if hard:
            command += " --hard"
        elif soft:
            command += " --soft"

        command += f" {ref}"

        exit_code, stdout, stderr = self._run_git(repo_dir, command, timeout=30)

        if exit_code != 0:
            raise GitError(f"Git reset failed: {stderr}")

    def fetch(self, repo_dir: str, remote: str = "origin", prune: bool = False) -> None:
        """Fetch from remote.

        Args:
            repo_dir: Path to git repository
            remote: Remote name
            prune: Prune deleted remote branches

        Raises:
            GitError: If fetch fails
        """
        command = f"fetch {remote}"

        if prune:
            command += " --prune"

        exit_code, stdout, stderr = self._run_git(repo_dir, command, timeout=60)

        if exit_code != 0:
            raise GitError(f"Git fetch failed: {stderr}")

    def add_remote(
        self,
        repo_dir: str,
        name: str,
        url: str,
        fetch: bool = True
    ) -> None:
        """Add a remote.

        Args:
            repo_dir: Path to git repository
            name: Remote name
            url: Remote URL
            fetch: Fetch immediately

        Raises:
            GitError: If adding remote fails
        """
        command = f"remote add {name} {url}"

        exit_code, stdout, stderr = self._run_git(repo_dir, command, timeout=10)

        if exit_code != 0:
            raise GitError(f"Failed to add remote: {stderr}")

        if fetch:
            self.fetch(repo_dir, name)

    def get_remotes(self, repo_dir: str) -> List[dict]:
        """List configured remotes.

        Args:
            repo_dir: Path to git repository

        Returns:
            List of remote info dictionaries
        """
        command = "remote -v"

        exit_code, stdout, stderr = self._run_git(repo_dir, command, timeout=10)

        if exit_code != 0:
            return []

        remotes = {}
        for line in stdout.strip().split('\n'):
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 3:
                name = parts[0]
                url = parts[1]
                remote_type = parts[2].strip('()')

                if name not in remotes:
                    remotes[name] = {'name': name, 'fetch': None, 'push': None}

                remotes[name][remote_type] = url

        return list(remotes.values())

    def show(
        self,
        repo_dir: str,
        ref: str = "HEAD",
        stat: bool = False,
        patch: bool = True
    ) -> str:
        """Show commit details.

        Args:
            repo_dir: Path to git repository
            ref: Commit reference
            stat: Show diff stat
            patch: Show patch

        Returns:
            str: Commit details
        """
        command = f"show {ref}"

        if stat:
            command += " --stat"
        if not patch:
            command += " --no-patch"

        exit_code, stdout, stderr = self._run_git(repo_dir, command, timeout=30)

        if exit_code != 0:
            raise GitError(f"Git show failed: {stderr}")

        return stdout
