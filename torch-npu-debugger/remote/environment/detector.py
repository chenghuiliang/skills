# Environment detector for Ascend NPU servers
# All comments in this file are in English per project guidelines

import re
from typing import List, Optional, Dict

from remote.core.exceptions import EnvironmentError, EnvironmentNotFoundError
from remote.core.session_manager import RemoteSessionManager
from remote.models.data_models import NPUDeviceInfo


class EnvironmentDetector:
    """Detects environment configuration on remote Ascend servers.

    Automatically detects CANN version, Python version, PyTorch version,
    NPU devices, and environment setup scripts.

    Example:
        session = RemoteSessionManager("dev@server")
        detector = EnvironmentDetector(session)

        # Detect all environment info
        env_info = detector.detect_all()
        print(f"CANN: {env_info['cann_version']}")
        print(f"Python: {env_info['python_version']}")
        print(f"NPU Devices: {len(env_info['npu_devices'])}")

        # Find environment setup script
        env_script = detector.find_env_setup_script()
        if env_script:
            print(f"Found env script: {env_script}")
    """

    # Common paths for environment scripts
    ENV_SCRIPT_PATHS = [
        "~/env_ms.sh",
        "~/work/env_ms.sh",
        "/home/*/work/env_ms.sh",
        "~/ascend_env.sh",
        "~/set_env.sh",
        "~/env.sh",
        "/usr/local/Ascend/ascend-toolkit/set_env.sh",
    ]

    # CANN installation paths
    CANN_PATHS = [
        "/usr/local/Ascend/ascend-toolkit/latest",
        "/usr/local/Ascend/ascend-toolkit",
        "~/Ascend/ascend-toolkit/latest",
        "/opt/Ascend/ascend-toolkit/latest",
    ]

    def __init__(self, session: RemoteSessionManager):
        """Initialize environment detector.

        Args:
            session: Connected SSH session manager
        """
        self.session = session
        self._cache: Dict[str, any] = {}

    def detect_all(self) -> Dict[str, any]:
        """Detect all environment information.

        Returns:
            Dict with all detected environment info
        """
        return {
            "cann_version": self.detect_cann_version(),
            "cann_path": self._get_cann_path(),
            "python_version": self.detect_python_version(),
            "pytorch_version": self.detect_pytorch_version(),
            "torch_npu_version": self.detect_torch_npu_version(),
            "npu_devices": self.detect_npu_devices(),
            "env_script": self.find_env_setup_script(),
            "gcc_version": self.detect_gcc_version(),
        }

    def detect_cann_version(self) -> Optional[str]:
        """Detect CANN version on remote server.

        Returns:
            str: CANN version or None if not found
        """
        if "cann_version" in self._cache:
            return self._cache["cann_version"]

        cann_path = self._get_cann_path()
        if not cann_path:
            return None

        # Try version.cfg
        version_file = f"{cann_path}/version.cfg"
        exit_code, stdout, _ = self.session.execute_command(
            f"cat {version_file} 2>/dev/null || echo 'NOT_FOUND'",
            timeout=10
        )

        if exit_code == 0 and stdout.strip() != "NOT_FOUND":
            # Parse version.cfg
            for line in stdout.splitlines():
                if "Version" in line or "version" in line:
                    version = line.split("=")[-1].strip()
                    self._cache["cann_version"] = version
                    return version

        # Try ascend_toolkit --version
        exit_code, stdout, _ = self.session.execute_command(
            f"source {cann_path}/set_env.sh 2>/dev/null && cat {version_file} 2>/dev/null | head -5",
            timeout=10
        )

        if exit_code == 0:
            for line in stdout.splitlines():
                if "Version" in line:
                    version = line.split("=")[-1].strip()
                    self._cache["cann_version"] = version
                    return version

        return None

    def detect_python_version(self) -> Optional[str]:
        """Detect Python version on remote server.

        Returns:
            str: Python version or None
        """
        if "python_version" in self._cache:
            return self._cache["python_version"]

        exit_code, stdout, _ = self.session.execute_command(
            "python --version 2>&1 || python3 --version 2>&1",
            timeout=10
        )

        if exit_code == 0:
            version = stdout.strip()
            self._cache["python_version"] = version
            return version

        return None

    def detect_pytorch_version(self) -> Optional[str]:
        """Detect PyTorch version on remote server.

        Returns:
            str: PyTorch version or None
        """
        if "pytorch_version" in self._cache:
            return self._cache["pytorch_version"]

        exit_code, stdout, _ = self.session.execute_command(
            "python -c 'import torch; print(torch.__version__)' 2>/dev/null",
            timeout=10
        )

        if exit_code == 0:
            version = stdout.strip()
            self._cache["pytorch_version"] = version
            return version

        return None

    def detect_torch_npu_version(self) -> Optional[str]:
        """Detect torch_npu version on remote server.

        Returns:
            str: torch_npu version or None
        """
        if "torch_npu_version" in self._cache:
            return self._cache["torch_npu_version"]

        # Try importing torch_npu
        exit_code, stdout, _ = self.session.execute_command(
            "python -c 'import torch_npu; print(torch_npu.__version__)' 2>/dev/null",
            timeout=10
        )

        if exit_code == 0:
            version = stdout.strip()
            self._cache["torch_npu_version"] = version
            return version

        return None

    def detect_npu_devices(self) -> List[NPUDeviceInfo]:
        """Detect NPU devices on remote server.

        Returns:
            List[NPUDeviceInfo]: List of NPU device info
        """
        if "npu_devices" in self._cache:
            return self._cache["npu_devices"]

        devices = []

        # Try npu-smi
        exit_code, stdout, _ = self.session.execute_command(
            "npu-smi info 2>/dev/null || echo 'NOT_AVAILABLE'",
            timeout=15
        )

        if exit_code == 0 and stdout.strip() != "NOT_AVAILABLE":
            devices = self._parse_npu_smi_output(stdout)

        # Fallback to lspci
        if not devices:
            exit_code, stdout, _ = self.session.execute_command(
                "lspci | grep -i ascend 2>/dev/null || echo 'NOT_FOUND'",
                timeout=10
            )

            if exit_code == 0 and "Ascend" in stdout:
                # Found devices but couldn't get detailed info
                pass

        self._cache["npu_devices"] = devices
        return devices

    def _parse_npu_smi_output(self, output: str) -> List[NPUDeviceInfo]:
        """Parse npu-smi info output."""
        devices = []

        # Parse device lines
        # Example format:
        # +-------------------+-----------------+------------------+
        # | NPU     Name      | Health          | Power(W)    ...  |
        # +-------------------+-----------------+------------------+
        # | 0       xxx       | OK              | 100         ...  |

        lines = output.splitlines()
        for i, line in enumerate(lines):
            if line.startswith("|") and "NPU" not in line and "+" not in line:
                parts = line.split("|")[1:-1]  # Remove empty first/last
                if len(parts) >= 4:
                    device_id_str = parts[0].strip()
                    name = parts[1].strip()

                    try:
                        device_id = int(device_id_str)
                    except ValueError:
                        continue

                    # Get memory info from detailed view
                    mem_total, mem_used = self._get_device_memory(device_id)

                    devices.append(NPUDeviceInfo(
                        device_id=device_id,
                        name=name,
                        total_memory=mem_total,
                        used_memory=mem_used,
                        free_memory=mem_total - mem_used,
                        utilization=0.0,  # Would need npu-smi info -t
                        temperature=None
                    ))

        return devices

    def _get_device_memory(self, device_id: int) -> tuple:
        """Get memory info for a specific device."""
        exit_code, stdout, _ = self.session.execute_command(
            f"npu-smi info -t memory -i {device_id} 2>/dev/null || echo '0 0'",
            timeout=10
        )

        if exit_code == 0:
            # Parse memory output
            lines = stdout.splitlines()
            for line in lines:
                if "Memory Capacity" in line or "total" in line.lower():
                    match = re.search(r'(\d+)\s*MB', line)
                    if match:
                        total = int(match.group(1))
                        used = 0  # Would need more parsing
                        return total, used

        return 0, 0

    def find_env_setup_script(self) -> Optional[str]:
        """Find environment setup script on remote server.

        Returns:
            str: Path to env script or None
        """
        if "env_script" in self._cache:
            return self._cache["env_script"]

        # Check common paths
        for path_pattern in self.ENV_SCRIPT_PATHS:
            # Expand wildcards
            if "*" in path_pattern:
                exit_code, stdout, _ = self.session.execute_command(
                    f"ls {path_pattern} 2>/dev/null | head -1",
                    timeout=5
                )
                if exit_code == 0 and stdout.strip():
                    script_path = stdout.strip().split()[0]
                    self._cache["env_script"] = script_path
                    return script_path
            else:
                exit_code, _, _ = self.session.execute_command(
                    f"test -f {path_pattern}",
                    timeout=5
                )
                if exit_code == 0:
                    self._cache["env_script"] = path_pattern
                    return path_pattern

        # Search for common env script names
        exit_code, stdout, _ = self.session.execute_command(
            "find ~ -maxdepth 3 -name 'env*.sh' -type f 2>/dev/null | head -5",
            timeout=15
        )

        if exit_code == 0 and stdout.strip():
            scripts = stdout.strip().split('\n')
            for script in scripts:
                if 'mindspore' in script.lower() or 'ascend' in script.lower():
                    self._cache["env_script"] = script
                    return script

            # Return first found
            if scripts:
                self._cache["env_script"] = scripts[0]
                return scripts[0]

        return None

    def detect_gcc_version(self) -> Optional[str]:
        """Detect GCC version on remote server.

        Returns:
            str: GCC version or None
        """
        if "gcc_version" in self._cache:
            return self._cache["gcc_version"]

        exit_code, stdout, _ = self.session.execute_command(
            "gcc --version 2>/dev/null | head -1 || echo 'NOT_FOUND'",
            timeout=10
        )

        if exit_code == 0 and stdout.strip() != "NOT_FOUND":
            version = stdout.strip()
            self._cache["gcc_version"] = version
            return version

        return None

    def _get_cann_path(self) -> Optional[str]:
        """Get CANN installation path."""
        if "cann_path" in self._cache:
            return self._cache["cann_path"]

        # Check environment variable
        exit_code, stdout, _ = self.session.execute_command(
            "echo $ASCEND_HOME_PATH",
            timeout=5
        )

        if exit_code == 0 and stdout.strip():
            path = stdout.strip()
            self._cache["cann_path"] = path
            return path

        # Check common paths
        for path in self.CANN_PATHS:
            exit_code, _, _ = self.session.execute_command(
                f"test -d {path}",
                timeout=5
            )
            if exit_code == 0:
                self._cache["cann_path"] = path
                return path

        return None

    def check_torch_npu_import(self) -> tuple:
        """Check if torch_npu can be imported successfully.

        Returns:
            Tuple of (success, error_message)
        """
        exit_code, stdout, stderr = self.session.execute_command(
            "python -c 'import torch; import torch_npu; print(\"OK\")' 2>&1",
            timeout=15
        )

        output = stdout + stderr

        if exit_code == 0 and "OK" in output:
            return True, None

        # Extract error
        error = output.strip()[-500:] if len(output) > 500 else output.strip()
        return False, error

    def get_environment_summary(self) -> str:
        """Get a formatted summary of environment.

        Returns:
            str: Formatted environment summary
        """
        info = self.detect_all()

        lines = [
            "Environment Summary:",
            "=" * 50,
            f"CANN Version: {info.get('cann_version', 'Not detected')}",
            f"Python Version: {info.get('python_version', 'Not detected')}",
            f"PyTorch Version: {info.get('pytorch_version', 'Not detected')}",
            f"torch_npu Version: {info.get('torch_npu_version', 'Not detected')}",
            f"GCC Version: {info.get('gcc_version', 'Not detected')}",
            f"NPU Devices: {len(info.get('npu_devices', []))}",
            f"Env Script: {info.get('env_script', 'Not found')}",
        ]

        return "\n".join(lines)
