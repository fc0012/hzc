"""SSH客户端模块"""
from typing import List, Dict, Optional
import paramiko
from paramiko import SSHClient as ParamikoSSHClient, AutoAddPolicy


class SSHClient:
    """SSH客户端，用于远程执行命令"""

    def __init__(self, username: str = "root", port: int = 22, timeout: int = 10):
        self.username = username
        self.port = port
        self.timeout = timeout

    def execute_command(
        self, host: str, command: str, password: str = None, key_path: str = None
    ) -> tuple[int, str, str]:
        """
        在远程服务器上执行命令

        返回: (exit_code, stdout, stderr)
        """
        client = ParamikoSSHClient()
        client.set_missing_host_key_policy(AutoAddPolicy())

        try:
            # 连接服务器
            if key_path:
                client.connect(
                    hostname=host,
                    port=self.port,
                    username=self.username,
                    key_filename=key_path,
                    timeout=self.timeout,
                )
            elif password:
                client.connect(
                    hostname=host,
                    port=self.port,
                    username=self.username,
                    password=password,
                    timeout=self.timeout,
                )
            else:
                # 尝试使用默认SSH密钥
                client.connect(
                    hostname=host,
                    port=self.port,
                    username=self.username,
                    timeout=self.timeout,
                    look_for_keys=True,
                )

            # 执行命令
            stdin, stdout, stderr = client.exec_command(command, timeout=self.timeout)
            exit_code = stdout.channel.recv_exit_status()
            stdout_text = stdout.read().decode("utf-8", errors="ignore")
            stderr_text = stderr.read().decode("utf-8", errors="ignore")

            return exit_code, stdout_text, stderr_text

        except Exception as e:
            return -1, "", str(e)
        finally:
            client.close()

    def check_processes(
        self, host: str, process_names: List[str], **kwargs
    ) -> List[Dict]:
        """
        检查指定进程是否在运行

        返回进程状态列表
        """
        if not process_names:
            return []

        # 构建ps命令，检查所有指定进程
        process_pattern = "|".join(process_names)
        command = f"ps aux | grep -E '({process_pattern})' | grep -v grep"

        exit_code, stdout, stderr = self.execute_command(host, command, **kwargs)

        if exit_code != 0:
            # 连接失败或命令执行失败
            return [
                {
                    "name": name,
                    "is_running": False,
                    "pid": None,
                    "cpu_percent": 0.0,
                    "memory_percent": 0.0,
                }
                for name in process_names
            ]

        # 解析ps输出
        lines = stdout.strip().split("\n") if stdout.strip() else []
        running_processes = {}

        for line in lines:
            parts = line.split()
            if len(parts) >= 11:
                user, pid, cpu, mem, vsz, rss, tty, stat, start, time, *cmd = parts
                cmd_str = " ".join(cmd)

                # 匹配进程名
                for name in process_names:
                    if name in cmd_str:
                        running_processes[name] = {
                            "name": name,
                            "is_running": True,
                            "pid": int(pid),
                            "cpu_percent": float(cpu),
                            "memory_percent": float(mem),
                        }
                        break

        # 构建结果
        result = []
        for name in process_names:
            if name in running_processes:
                result.append(running_processes[name])
            else:
                result.append(
                    {
                        "name": name,
                        "is_running": False,
                        "pid": None,
                        "cpu_percent": 0.0,
                        "memory_percent": 0.0,
                    }
                )

        return result

    def get_system_info(self, host: str, **kwargs) -> Dict:
        """获取系统基本信息"""
        commands = {
            "uptime": "uptime -p",
            "load": "cat /proc/loadavg | awk '{print $1,$2,$3}'",
            "memory": "free -m | awk 'NR==2{print $2,$3,$4}'",
            "disk": "df -h / | awk 'NR==2{print $2,$3,$4,$5}'",
        }

        result = {}
        for key, cmd in commands.items():
            exit_code, stdout, stderr = self.execute_command(host, cmd, **kwargs)
            if exit_code == 0:
                result[key] = stdout.strip()
            else:
                result[key] = None

        return result
