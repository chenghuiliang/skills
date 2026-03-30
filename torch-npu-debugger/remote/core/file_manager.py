# Remote file manager for upload/download and manipulation
# All comments in this file are in English per project guidelines

import os
import stat
from datetime import datetime
from pathlib import Path
from typing import List, Optional, BinaryIO, Union

from remote.core.exceptions import FileError, FileNotFoundError, PermissionError
from remote.core.session_manager import RemoteSessionManager
from remote.models.data_models import FileInfo, SyncPlan


class RemoteFileManager:
    """Manages file operations on remote servers.

    Supports file upload/download, directory synchronization,
    and remote file manipulation.

    Example:
        session = RemoteSessionManager("dev@server")
        file_mgr = RemoteFileManager(session)

        # Upload a file
        file_mgr.upload("local/path/file.txt", "/remote/path/file.txt")

        # Read remote file
        content = file_mgr.read_file("/remote/path/file.txt")

        # List directory
        files = file_mgr.list_directory("/remote/path")
    """

    def __init__(self, session: RemoteSessionManager):
        """Initialize file manager.

        Args:
            session: Connected SSH session manager
        """
        self.session = session

    def upload(
        self,
        local_path: str,
        remote_path: str,
        preserve_permissions: bool = True
    ) -> None:
        """Upload a file to remote server.

        Args:
            local_path: Path to local file
            remote_path: Destination path on remote
            preserve_permissions: Whether to preserve file permissions

        Raises:
            FileNotFoundError: If local file doesn't exist
            FileError: If upload fails
        """
        local = Path(local_path).expanduser()

        if not local.exists():
            raise FileNotFoundError(f"Local file not found: {local_path}")

        if not local.is_file():
            raise FileError(f"Path is not a file: {local_path}")

        try:
            sftp = self.session.get_sftp()

            # Create remote directory if needed
            remote_dir = str(Path(remote_path).parent)
            self._ensure_remote_directory(remote_dir)

            # Upload file
            sftp.put(str(local), remote_path)

            # Preserve permissions
            if preserve_permissions:
                mode = local.stat().st_mode & 0o777
                sftp.chmod(remote_path, mode)

        except Exception as e:
            raise FileError(
                f"Failed to upload {local_path} to {remote_path}: {e}"
            ) from e

    def download(
        self,
        remote_path: str,
        local_path: str,
        preserve_permissions: bool = True
    ) -> None:
        """Download a file from remote server.

        Args:
            remote_path: Path to remote file
            local_path: Destination path locally
            preserve_permissions: Whether to preserve file permissions

        Raises:
            FileNotFoundError: If remote file doesn't exist
            FileError: If download fails
        """
        local = Path(local_path).expanduser()

        # Create local directory if needed
        local.parent.mkdir(parents=True, exist_ok=True)

        try:
            sftp = self.session.get_sftp()

            # Check if remote file exists
            try:
                sftp.stat(remote_path)
            except IOError:
                raise FileNotFoundError(f"Remote file not found: {remote_path}")

            # Download file
            sftp.get(remote_path, str(local))

            # Preserve permissions
            if preserve_permissions:
                remote_stat = sftp.stat(remote_path)
                os.chmod(local, remote_stat.st_mode & 0o777)

        except FileNotFoundError:
            raise
        except Exception as e:
            raise FileError(
                f"Failed to download {remote_path} to {local_path}: {e}"
            ) from e

    def upload_directory(
        self,
        local_dir: str,
        remote_dir: str,
        exclude: Optional[List[str]] = None,
        preserve_permissions: bool = True
    ) -> None:
        """Upload a directory recursively.

        Args:
            local_dir: Path to local directory
            remote_dir: Destination directory on remote
            exclude: Patterns to exclude (e.g., ["*.pyc", ".git"])
            preserve_permissions: Whether to preserve file permissions

        Raises:
            FileNotFoundError: If local directory doesn't exist
            FileError: If upload fails
        """
        local = Path(local_dir).expanduser()

        if not local.exists():
            raise FileNotFoundError(f"Local directory not found: {local_dir}")

        if not local.is_dir():
            raise FileError(f"Path is not a directory: {local_dir}")

        exclude = exclude or []

        try:
            sftp = self.session.get_sftp()

            # Create remote directory
            self._ensure_remote_directory(remote_dir)

            # Walk and upload
            for root, dirs, files in os.walk(local):
                # Filter excluded directories
                dirs[:] = [
                    d for d in dirs
                    if not any(self._matches_pattern(d, p) for p in exclude)
                ]

                # Calculate relative path
                rel_path = Path(root).relative_to(local)
                remote_path = f"{remote_dir}/{rel_path}"

                # Create remote subdirectory
                self._ensure_remote_directory(remote_path)

                # Upload files
                for file in files:
                    if any(self._matches_pattern(file, p) for p in exclude):
                        continue

                    local_file = Path(root) / file
                    remote_file = f"{remote_path}/{file}"

                    sftp.put(str(local_file), remote_file)

                    if preserve_permissions:
                        mode = local_file.stat().st_mode & 0o777
                        sftp.chmod(remote_file, mode)

        except Exception as e:
            raise FileError(
                f"Failed to upload directory {local_dir} to {remote_dir}: {e}"
            ) from e

    def download_directory(
        self,
        remote_dir: str,
        local_dir: str,
        exclude: Optional[List[str]] = None,
        preserve_permissions: bool = True
    ) -> None:
        """Download a directory recursively.

        Args:
            remote_dir: Path to remote directory
            local_dir: Destination directory locally
            exclude: Patterns to exclude
            preserve_permissions: Whether to preserve file permissions

        Raises:
            FileNotFoundError: If remote directory doesn't exist
            FileError: If download fails
        """
        local = Path(local_dir).expanduser()
        local.mkdir(parents=True, exist_ok=True)

        exclude = exclude or []

        try:
            sftp = self.session.get_sftp()

            # List remote directory recursively
            files = self._list_remote_recursive(remote_dir, exclude)

            for remote_file in files:
                rel_path = Path(remote_file).relative_to(remote_dir)
                local_file = local / rel_path

                # Create local subdirectory
                local_file.parent.mkdir(parents=True, exist_ok=True)

                # Download file
                sftp.get(remote_file, str(local_file))

                if preserve_permissions:
                    remote_stat = sftp.stat(remote_file)
                    os.chmod(local_file, remote_stat.st_mode & 0o777)

        except Exception as e:
            raise FileError(
                f"Failed to download directory {remote_dir} to {local_dir}: {e}"
            ) from e

    def read_file(
        self,
        remote_path: str,
        offset: int = 0,
        limit: int = -1,
        encoding: str = "utf-8"
    ) -> str:
        """Read contents of a remote file.

        Args:
            remote_path: Path to remote file
            offset: Starting byte offset
            limit: Maximum bytes to read (-1 for all)
            encoding: File encoding

        Returns:
            str: File contents

        Raises:
            FileNotFoundError: If file doesn't exist
            FileError: If read fails
        """
        try:
            sftp = self.session.get_sftp()

            with sftp.file(remote_path, "r") as f:
                if offset > 0:
                    f.seek(offset)

                if limit > 0:
                    content = f.read(limit)
                else:
                    content = f.read()

                return content.decode(encoding, errors="replace")

        except IOError as e:
            if "No such file" in str(e):
                raise FileNotFoundError(f"Remote file not found: {remote_path}")
            raise FileError(f"Failed to read {remote_path}: {e}") from e

    def write_file(
        self,
        remote_path: str,
        content: str,
        mode: str = "w",
        encoding: str = "utf-8"
    ) -> None:
        """Write content to a remote file.

        Args:
            remote_path: Path to remote file
            content: Content to write
            mode: File mode ("w" for write, "a" for append)
            encoding: File encoding

        Raises:
            FileError: If write fails
            PermissionError: If write permission denied
        """
        try:
            sftp = self.session.get_sftp()

            # Ensure parent directory exists
            remote_dir = str(Path(remote_path).parent)
            self._ensure_remote_directory(remote_dir)

            # Write file
            sftp_mode = "w" if mode == "w" else "a"
            with sftp.file(remote_path, sftp_mode) as f:
                f.write(content.encode(encoding))

        except IOError as e:
            if "Permission denied" in str(e):
                raise PermissionError(f"Permission denied writing to {remote_path}")
            raise FileError(f"Failed to write {remote_path}: {e}") from e

    def list_directory(self, remote_dir: str) -> List[FileInfo]:
        """List contents of a remote directory.

        Args:
            remote_dir: Path to remote directory

        Returns:
            List[FileInfo]: Directory contents

        Raises:
            FileNotFoundError: If directory doesn't exist
            FileError: If listing fails
        """
        try:
            sftp = self.session.get_sftp()

            entries = []
            for entry in sftp.listdir_attr(remote_dir):
                full_path = f"{remote_dir}/{entry.filename}"

                file_info = FileInfo(
                    name=entry.filename,
                    path=full_path,
                    size=entry.st_size,
                    is_directory=stat.S_ISDIR(entry.st_mode),
                    is_symlink=stat.S_ISLNK(entry.st_mode),
                    permissions=oct(entry.st_mode)[-3:],
                    owner=str(entry.st_uid),
                    group=str(entry.st_gid),
                    modified_time=datetime.fromtimestamp(entry.st_mtime),
                    accessed_time=datetime.fromtimestamp(entry.st_atime)
                )
                entries.append(file_info)

            return entries

        except IOError as e:
            if "No such file" in str(e):
                raise FileNotFoundError(f"Remote directory not found: {remote_dir}")
            raise FileError(f"Failed to list {remote_dir}: {e}") from e

    def file_exists(self, remote_path: str) -> bool:
        """Check if a remote file exists.

        Args:
            remote_path: Path to check

        Returns:
            bool: True if file exists
        """
        try:
            sftp = self.session.get_sftp()
            sftp.stat(remote_path)
            return True
        except IOError:
            return False

    def get_file_info(self, remote_path: str) -> FileInfo:
        """Get information about a remote file.

        Args:
            remote_path: Path to remote file

        Returns:
            FileInfo: File information

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        try:
            sftp = self.session.get_sftp()
            entry = sftp.stat(remote_path)

            filename = Path(remote_path).name

            return FileInfo(
                name=filename,
                path=remote_path,
                size=entry.st_size,
                is_directory=stat.S_ISDIR(entry.st_mode),
                is_symlink=stat.S_ISLNK(entry.st_mode),
                permissions=oct(entry.st_mode)[-3:],
                owner=str(entry.st_uid),
                group=str(entry.st_gid),
                modified_time=datetime.fromtimestamp(entry.st_mtime),
                accessed_time=datetime.fromtimestamp(entry.st_atime)
            )

        except IOError as e:
            if "No such file" in str(e):
                raise FileNotFoundError(f"Remote file not found: {remote_path}")
            raise FileError(f"Failed to get info for {remote_path}: {e}") from e

    def apply_patch(self, patch_content: str, working_dir: str) -> bool:
        """Apply a git patch to the remote working directory.

        Args:
            patch_content: Git patch content
            working_dir: Working directory on remote

        Returns:
            bool: True if patch applied successfully
        """
        import tempfile
        import uuid

        # Write patch to temp file
        patch_file = f"/tmp/patch_{uuid.uuid4().hex[:8]}.diff"

        try:
            self.write_file(patch_file, patch_content)

            # Apply patch
            result = self.session.execute_command(
                f"cd {working_dir} && git apply --check {patch_file} 2>&1 && git apply {patch_file}",
                timeout=30
            )

            return result[0] == 0

        except Exception:
            return False
        finally:
            # Cleanup
            try:
                self.session.execute_command(f"rm -f {patch_file}", timeout=5)
            except Exception:
                pass

    def generate_patch(
        self,
        working_dir: str,
        ref: str = "HEAD",
        target_ref: Optional[str] = None
    ) -> str:
        """Generate a git patch from the remote working directory.

        Args:
            working_dir: Working directory on remote
            ref: Git reference (e.g., "HEAD", "HEAD~1")
            target_ref: Target reference for diff (None for uncommitted changes)

        Returns:
            str: Patch content
        """
        if target_ref:
            command = f"cd {working_dir} && git diff {ref} {target_ref}"
        else:
            command = f"cd {working_dir} && git diff {ref}"

        exit_code, stdout, stderr = self.session.execute_command(
            command,
            timeout=30
        )

        if exit_code != 0:
            raise FileError(f"Failed to generate patch: {stderr}")

        return stdout

    def delete_file(self, remote_path: str, recursive: bool = False) -> None:
        """Delete a remote file or directory.

        Args:
            remote_path: Path to delete
            recursive: Whether to delete directories recursively

        Raises:
            FileNotFoundError: If file doesn't exist
            FileError: If deletion fails
        """
        try:
            info = self.get_file_info(remote_path)

            if info.is_directory:
                if recursive:
                    self.session.execute_command(
                        f"rm -rf {remote_path}",
                        timeout=60
                    )
                else:
                    sftp = self.session.get_sftp()
                    sftp.rmdir(remote_path)
            else:
                sftp = self.session.get_sftp()
                sftp.remove(remote_path)

        except FileNotFoundError:
            raise
        except Exception as e:
            raise FileError(f"Failed to delete {remote_path}: {e}") from e

    def _ensure_remote_directory(self, remote_dir: str) -> None:
        """Ensure remote directory exists."""
        try:
            sftp = self.session.get_sftp()

            # Try to create directory (will fail if exists, that's ok)
            try:
                sftp.mkdir(remote_dir)
            except IOError:
                # Directory might already exist
                pass

        except Exception as e:
            raise FileError(f"Failed to create directory {remote_dir}: {e}") from e

    def _matches_pattern(self, name: str, pattern: str) -> bool:
        """Check if name matches glob pattern."""
        import fnmatch
        return fnmatch.fnmatch(name, pattern)

    def _list_remote_recursive(
        self,
        remote_dir: str,
        exclude: List[str]
    ) -> List[str]:
        """Recursively list files in remote directory."""
        files = []

        def recurse(current_dir: str):
            entries = self.list_directory(current_dir)

            for entry in entries:
                if any(self._matches_pattern(entry.name, p) for p in exclude):
                    continue

                if entry.is_directory:
                    recurse(entry.path)
                else:
                    files.append(entry.path)

        recurse(remote_dir)
        return files

    def compute_sync_plan(
        self,
        local_dir: str,
        remote_dir: str,
        exclude: Optional[List[str]] = None
    ) -> SyncPlan:
        """Compute a plan for synchronizing directories.

        Args:
            local_dir: Local directory path
            remote_dir: Remote directory path
            exclude: Patterns to exclude

        Returns:
            SyncPlan: Synchronization plan
        """
        # This would require comparing local and remote file lists
        # For now, return a simple plan
        plan = SyncPlan()

        # Walk local directory
        local = Path(local_dir).expanduser()
        exclude = exclude or []

        for root, dirs, files in os.walk(local):
            # Filter excluded directories
            dirs[:] = [
                d for d in dirs
                if not any(self._matches_pattern(d, p) for p in exclude)
            ]

            rel_path = Path(root).relative_to(local)

            for file in files:
                if any(self._matches_pattern(file, p) for p in exclude):
                    continue

                local_file = Path(root) / file
                remote_file = f"{remote_dir}/{rel_path}/{file}"

                # Check if remote file needs update
                if self._needs_update(local_file, remote_file):
                    plan.files_to_upload.append(str(local_file))

        return plan

    def _needs_update(self, local_file: Path, remote_file: str) -> bool:
        """Check if local file needs to be uploaded."""
        try:
            remote_info = self.get_file_info(remote_file)
            local_stat = local_file.stat()

            # Compare modification times and sizes
            local_mtime = datetime.fromtimestamp(local_stat.st_mtime)
            remote_mtime = remote_info.modified_time

            return (local_mtime > remote_mtime or
                    local_stat.st_size != remote_info.size)
        except FileNotFoundError:
            # Remote file doesn't exist, needs upload
            return True
