# Data models for remote operations
# All comments in this file are in English per project guidelines

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Callable, Iterator


class TaskState(Enum):
    """States for async task lifecycle."""
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    CANCELLED = auto()
    TIMEOUT = auto()
    FAILED = auto()


@dataclass
class CommandResult:
    """Result of a remote command execution."""
    exit_code: int
    stdout: str
    stderr: str
    execution_time: float
    command: str
    working_dir: str
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def success(self) -> bool:
        """Check if command executed successfully."""
        return self.exit_code == 0


@dataclass
class AsyncTaskHandle:
    """Handle for tracking async remote tasks."""
    task_id: str
    command: str
    working_dir: str
    state: TaskState = TaskState.PENDING
    pid: Optional[int] = None
    log_file: Optional[str] = None
    status_file: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class TaskStatus:
    """Current status of an async task."""
    task_id: str
    state: TaskState
    progress: Optional[float] = None  # 0-100
    message: Optional[str] = None
    last_output: Optional[str] = None
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class ErrorInfo:
    """Information about a single error."""
    message: str
    category: str  # e.g., "link_error", "compile_error", "syntax_error"
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    column: Optional[int] = None
    suggestion: Optional[str] = None


@dataclass
class CompileAnalysis:
    """Analysis result of a compilation."""
    success: bool
    error_count: int
    warning_count: int
    error_categories: Dict[str, List[str]] = field(default_factory=dict)
    errors: List[ErrorInfo] = field(default_factory=list)
    warnings: List[ErrorInfo] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    is_link_error: bool = False
    is_op_plugin_error: bool = False
    is_abi_error: bool = False
    is_version_mismatch: bool = False
    raw_output: str = ""


@dataclass
class TestResult:
    """Result of a single test case."""
    name: str
    status: str  # "passed", "failed", "skipped", "error"
    duration: float
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None


@dataclass
class TestAnalysis:
    """Analysis result of test execution."""
    success: bool
    total_tests: int
    passed: int
    failed: int
    skipped: int
    errors: int
    duration: float
    failed_tests: List[str] = field(default_factory=list)
    error_details: Dict[str, str] = field(default_factory=dict)
    test_results: List[TestResult] = field(default_factory=list)
    raw_output: str = ""


@dataclass
class ErrorAnalysis:
    """General error analysis result."""
    category: str
    severity: str  # "critical", "high", "medium", "low"
    root_cause: Optional[str] = None
    suggestions: List[str] = field(default_factory=list)
    related_files: List[str] = field(default_factory=list)
    confidence: float = 0.0  # 0-1


@dataclass
class FileInfo:
    """Information about a remote file."""
    name: str
    path: str
    size: int
    is_directory: bool
    is_symlink: bool
    permissions: str
    owner: str
    group: str
    modified_time: datetime
    accessed_time: datetime
    created_time: Optional[datetime] = None
    symlink_target: Optional[str] = None


@dataclass
class GitStatus:
    """Git repository status."""
    branch: str
    is_clean: bool
    modified_files: List[str] = field(default_factory=list)
    staged_files: List[str] = field(default_factory=list)
    untracked_files: List[str] = field(default_factory=list)
    ahead_count: int = 0
    behind_count: int = 0
    last_commit_hash: Optional[str] = None
    last_commit_message: Optional[str] = None


@dataclass
class CommitInfo:
    """Information about a git commit."""
    hash: str
    short_hash: str
    author: str
    email: str
    date: datetime
    message: str
    subject: str
    body: str = ""
    files_changed: List[str] = field(default_factory=list)
    insertions: int = 0
    deletions: int = 0


@dataclass
class NPUDeviceInfo:
    """Information about an NPU device."""
    device_id: int
    name: str
    total_memory: int  # in MB
    used_memory: int
    free_memory: int
    utilization: float  # 0-100
    temperature: Optional[float] = None
    driver_version: Optional[str] = None


@dataclass
class SyncPlan:
    """Plan for synchronizing files between local and remote."""
    files_to_upload: List[str] = field(default_factory=list)
    files_to_download: List[str] = field(default_factory=list)
    files_to_delete: List[str] = field(default_factory=list)
    directories_to_create: List[str] = field(default_factory=list)
    estimated_size: int = 0
    estimated_time: float = 0.0


@dataclass
class VerificationResult:
    """Result of remote verification (compile + test)."""
    success: bool
    stage: str  # "compile", "test", "sync"
    compile_analysis: Optional[CompileAnalysis] = None
    test_analysis: Optional[TestAnalysis] = None
    error_message: Optional[str] = None
    duration: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
