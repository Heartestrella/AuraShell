import os
import re
import json
import traceback
import paramiko
from typing import Dict, List
from PyQt5.QtCore import QThread, QTimer, pyqtSignal
from tools.atool import resource_path
import binascii
import socks
import socket
import uuid
import time
from tools.session_manager import Session


class SSHWorker(QThread):
    result_ready = pyqtSignal(bytes)
    connected = pyqtSignal(bool, str)
    error_occurred = pyqtSignal(str)
    sys_resource = pyqtSignal(dict)
    file_tree_updated = pyqtSignal(dict)
    auth_error = pyqtSignal(str)
    # host_key , processes_md5 key
    key_verification = pyqtSignal(str, str)
    stop_timer_sig = pyqtSignal()
    command_output_ready = pyqtSignal(str, int)
    force_complete = pyqtSignal(str)

    def __init__(self, session_info, parent=None, for_resources=False, for_file=False, jumpbox=False):
        super().__init__(parent)
        self.host = session_info.host
        self.user = session_info.username
        self.port = session_info.port
        self.password = session_info.password
        self.auth_type = session_info.auth_type
        self.key_path = session_info.key_path
        self.jumpbox: Session = jumpbox
        self.proxy_type = getattr(session_info, 'proxy_type', 'None')
        self.proxy_host = getattr(session_info, 'proxy_host', '')
        self.proxy_port = getattr(session_info, 'proxy_port', 0)
        self.proxy_username = getattr(session_info, 'proxy_username', '')
        self.proxy_password = getattr(session_info, 'proxy_password', '')
        self.ssh_default_path = session_info.ssh_default_path
        # print(f"{self.host}  {self.user}  {self.password}")
        self.conn = None
        self.channel = None
        self.timer = None
        self.for_resources = for_resources
        self.for_file = for_file
        self._buffer = b""  # Storing incomplete output data

        # File tree structure
        self.file_tree: Dict = {}
        # Store the contents of each directory
        self.dir_contents: Dict[str, List[str]] = {}

        self.is_capturing = False
        self.capture_buffer = b""
        self.start_marker = ""
        self.end_marker = ""
        self.command_completed = False
        self.completion_timer = None
        self.last_output_time = None

    def get_hostkey_fp_hex(self) -> str:
        try:
            transport = self.conn.get_transport()
            if transport is None:
                return None
            host_key = transport.get_remote_server_key()
            if host_key is None:
                return None
            fp_bytes = host_key.get_fingerprint()
            if not fp_bytes:
                return None
            fp_hex = binascii.hexlify(fp_bytes).decode().lower()
            return fp_hex
        except Exception:
            return None

    def get_remote_md5(self, path):
        try:
            cmd = f"md5sum {path} 2>/dev/null | awk '{{print $1}}'"
            stdin, stdout, stderr = self.conn.exec_command(cmd, timeout=10)
            result = stdout.read().decode().strip()
            if result:
                return result
            else:
                return None
        except Exception:
            return None

    def handle_force_complete(self, request_id: str):
        if self.is_capturing:
            self._process_capture_buffer(force=True)

    def run(self):
        try:
            self.force_complete.connect(self.handle_force_complete)
            self.conn = paramiko.SSHClient()
            self.conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            sock = self._create_socket()

            if isinstance(self.jumpbox, Session):  # jumbox maybe is None:str
                self.jumpbox_ssh = paramiko.SSHClient()
                self.jumpbox_ssh.set_missing_host_key_policy(
                    paramiko.AutoAddPolicy())

                host = self.jumpbox.host
                user = self.jumpbox.username
                port = self.jumpbox.port
                password = self.jumpbox.password
                auth_type = self.jumpbox.auth_type
                key_path = self.jumpbox.key_path

                print(f"🔗 连接到跳板机: {user}@{host}:{port}")

                # 连接到跳板机
                if auth_type == "password":
                    self.jumpbox_ssh.connect(
                        host, port, user, password, timeout=10, sock=sock)
                else:
                    self.jumpbox_ssh.connect(
                        host, port, user, key_filename=key_path, timeout=10, sock=sock)

                print("✅ 跳板机连接成功")

                print(f"🔄 创建到目标服务器 {self.host}:{self.port} 的隧道")
                jumpbox_transport = self.jumpbox_ssh.get_transport()
                dest_addr = (self.host, self.port)
                jumpbox_channel = jumpbox_transport.open_channel(
                    kind="direct-tcpip",
                    dest_addr=dest_addr,
                    src_addr=(host, port)
                )

                print("✅ 隧道创建成功")

                print(f"🔗 通过隧道连接到目标服务器: {self.user}@{self.host}:{self.port}")
                try:
                    if self.auth_type == "password":
                        self.conn.connect(
                            self.host,
                            username=self.user,
                            password=self.password,
                            timeout=10,
                            port=self.port,
                            sock=jumpbox_channel
                        )
                    else:
                        self.conn.connect(
                            self.host,
                            username=self.user,
                            key_filename=self.key_path,
                            timeout=10,
                            port=self.port,
                            sock=jumpbox_channel
                        )
                    print("✅ 目标服务器连接成功")

                except paramiko.AuthenticationException as e:
                    error_msg = self.tr(
                        f"Target server authentication failed: {e}")
                    self.auth_error.emit(error_msg)
                    self._cleanup()
                    return
                except (socket.timeout, paramiko.SSHException) as e:
                    error_msg = self.tr(
                        f"Target server connection failed: {e}")
                    self.auth_error.emit(error_msg)
                    self._cleanup()
                    return

            else:
                print(
                    f"🔗 Connect directly to the server: {self.user}@{self.host}:{self.port}")
                try:
                    if self.auth_type == "password":
                        self.conn.connect(
                            self.host,
                            username=self.user,
                            password=self.password,
                            timeout=10,
                            port=self.port,
                            sock=sock
                        )
                    else:
                        self.conn.connect(
                            self.host,
                            username=self.user,
                            key_filename=self.key_path,
                            timeout=10,
                            port=self.port,
                            sock=sock
                        )
                    print("✅ Direct connection successful")

                except paramiko.AuthenticationException as e:
                    error_msg = self.tr(f"Authentication failed: {e}")
                    self.auth_error.emit(error_msg)
                    self._cleanup()
                    return
                except (socket.timeout, paramiko.SSHException) as e:
                    error_msg = self.tr(f"Connection failed: {e}")
                    self.auth_error.emit(error_msg)
                    self._cleanup()
                    return

            transport = self.conn.get_transport()
            transport.set_keepalive(30)
            self.channel = transport.open_session()
            self.channel.get_pty(term='xterm', width=120, height=30)
            self.channel.invoke_shell()

            # ---------- resources handling ----------
            if self.for_resources:
                try:
                    sftp = self.conn.open_sftp()
                    remote_dir = "./.ssh"
                    self.remote_proc = "./.ssh/processes.sh"
                    self.local_proc = resource_path(os.path.join(
                        "resource", "processes.sh"))
                    # ensure remote .ssh dir exists
                    try:
                        sftp.stat(remote_dir)
                    except IOError:
                        try:
                            sftp.mkdir(remote_dir, mode=0o700)
                            print(f"创建远端目录 {remote_dir}")
                        except Exception as e:
                            print(f"无法创建远端目录 {remote_dir}: {e}")
                    if not os.path.exists(self.local_proc):
                        err = f"本地 processes 文件不存在: {self.local_proc}"
                        print(err)
                        self.error_occurred.emit(err)
                    else:
                        try:
                            print(
                                f"上传本地 {self.local_proc} 到远端 {self.remote_proc} ...")
                            with open(self.local_proc, 'rb') as f:
                                content = f.read()
                            content = content.replace(b'\r\n', b'\n')
                            import tempfile
                            with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.sh') as tmp:
                                tmp.write(content)
                                tmp_path = tmp.name
                            try:
                                sftp.put(tmp_path, self.remote_proc)
                                sftp.chmod(self.remote_proc, 0o755)
                                print("✅ 上传并设置可执行成功")
                            finally:
                                try:
                                    os.unlink(tmp_path)
                                except Exception:
                                    pass
                        except Exception as e:
                            tb = traceback.format_exc()
                            err = f"上传 processes 失败: {e}\n{tb}"
                            print(err)
                            self.error_occurred.emit(err)
                    try:
                        sftp.close()
                    except Exception:
                        pass
                except Exception as e:
                    tb = traceback.format_exc()
                    print(f"resources pre-check/upload 出错: {e}\n{tb}")
                    self.error_occurred.emit(
                        f"resources pre-check/upload 出错: {e}")
            else:
                cd_folder: str = self.ssh_default_path.replace("\\", "/")
                if "/" in cd_folder:
                    self.run_command(f"cd {cd_folder}")
                self.connected.emit(True, "Connect Success")

            self.timer = QTimer()
            self.stop_timer_sig.connect(self.timer.stop)
            self.timer.timeout.connect(self._check_output)
            self.timer.start(100)

            if self.for_resources:
                md5 = self.get_remote_md5(self.remote_proc)
                host_key = self.get_hostkey_fp_hex()
                self.key_verification.emit(md5, host_key)
                script_path = self.remote_proc
                check_cmd = f"test -x {script_path} && echo 'EXISTS' || echo 'NOT_FOUND'"
                self.run_command(check_cmd)
                if self.user == "root":
                    cmd = f'{script_path}'
                    print(f"Running without sudo as root: {cmd}")
                else:
                    cmd = f'echo {self.password} | sudo -S bash {script_path}'
                    print(f"Running with sudo as non-root: {cmd}")
                try:
                    self.run_command(cmd)
                    print(f"已启动远端 processes 可执行文件({script_path})")
                except Exception as e:
                    print(f"启动 processes 失败：{e}")
                    self.error_occurred.emit(f"启动 processes 失败：{e}")

            self.exec_()
            self._cleanup()

        except socks.ProxyError as e:
            error_msg = f"Proxy Error: {e}"
            self.error_occurred.emit(error_msg)
        except Exception as e:
            tb = traceback.format_exc()
            self.error_occurred.emit(f"{e}\n{tb}")

    def _create_socket(self):
        if self.proxy_type == 'None' or not self.proxy_host or not self.proxy_port:
            return None
        sock = socks.socksocket()
        sock.settimeout(15)
        proxy_type_map = {
            'HTTP': socks.HTTP,
            'SOCKS4': socks.SOCKS4,
            'SOCKS5': socks.SOCKS5
        }
        proxy_type = proxy_type_map.get(self.proxy_type)
        if not proxy_type:
            return None
        use_remote_dns = self.proxy_type in ['SOCKS4', 'SOCKS5']
        sock.set_proxy(
            proxy_type=proxy_type,
            addr=self.proxy_host,
            port=self.proxy_port,
            rdns=use_remote_dns,
            username=self.proxy_username if self.proxy_username else None,
            password=self.proxy_password if self.proxy_password else None
        )
        try:
            sock.connect((self.host, self.port))
            return sock
        except Exception as e:
            self.error_occurred.emit(f"Proxy connection failed: {e}")
            return None

    def update_script(self):
        sftp = self.conn.open_sftp()
        try:
            print(
                f"上传本地 {self.local_proc} 到远端 {self.remote_proc} ...")
            sftp.put(self.local_proc, self.remote_proc)
            try:
                sftp.chmod(self.remote_proc, 0o755)
            except Exception:
                pass
            print("上传并设置可执行成功")
        except Exception as e:
            tb = traceback.format_exc()
            err = f"上传 processes 失败: {e}\n{tb}"
            print(err)
            self.error_occurred.emit(err)

    def disconnect_all_signals(self):
        signals = [
            self.result_ready,
            self.connected,
            self.error_occurred,
            self.sys_resource,
            self.file_tree_updated,
            self.key_verification,
            self.stop_timer_sig,
        ]
        for sig in signals:
            try:
                sig.disconnect()
            except TypeError:
                pass

    def _cleanup(self):
        try:
            if hasattr(self, "stop_timer_sig"):
                self.stop_timer_sig.emit()
        except Exception:
            pass
        try:
            if hasattr(self, "completion_timer") and self.completion_timer:
                self.completion_timer.stop()
                self.completion_timer = None
        except Exception:
            pass
        try:
            if self.channel:
                self.channel.close()
        except Exception:
            pass
        try:
            if self.conn:
                transport = self.conn.get_transport()
                if transport:
                    transport.set_keepalive(0)
                self.conn.close()
        except Exception:
            pass
        self.disconnect_all_signals()
        # try:
        #     signals = [
        #         'result_ready', 'connected', 'error_occurred', 'sys_resource', 'file_tree_updated', 'stop_timer_sig'
        #     ]
        #     for sig_name in signals:
        #         sig = getattr(self, sig_name, None)
        #         if sig:
        #             try:
        #                 sig.disconnect()
        #             except Exception:
        #                 pass
        # except Exception:
        #     pass
        try:
            if self.isRunning():
                self.quit()
                # self.wait(2000)
        except Exception:
            pass

    def _check_output(self):
        try:
            if not self.channel:
                return
            if self.conn and self.conn.get_transport():
                if not self.conn.get_transport().is_active():
                    self.error_occurred.emit("SSH连接已断开")
                    self.quit()
                    return
            if self.channel.recv_ready():
                chunk = self.channel.recv(4096)
                self.result_ready.emit(chunk)
                if self.is_capturing:
                    self.capture_buffer += chunk
                    self._process_capture_buffer()
                elif self.for_resources:
                    self._buffer += chunk
                    self._process_sys_resource_buffer()
            if self.channel.closed or self.channel.exit_status_ready():
                while self.channel.recv_ready():
                    chunk = self.channel.recv(4096)
                    self.result_ready.emit(chunk)
                    if self.is_capturing:
                        self.capture_buffer += chunk
                        self._process_capture_buffer()
                    elif self.for_resources:
                        self._buffer += chunk
                        self._process_sys_resource_buffer()
                self.quit()
        except Exception as e:
            self.error_occurred.emit(str(e))

    def _process_sys_resource_buffer(self):
        try:
            text = self._buffer.decode(errors='ignore')
            pattern = re.compile(r'///(SysInfo|Start)(.*?)End///', re.DOTALL)
            match = pattern.search(text)
            if match:
                tag, payload = match.groups()
                try:
                    data = json.loads(payload.strip())
                    if tag == "SysInfo":
                        data = {"type": "sysinfo", **data}
                    else:
                        data = {"type": "info", **data}
                    self.sys_resource.emit(data)
                except Exception as e:
                    print(f"Error processing system resource data: {e}")
                    print("--- Failing payload ---")
                    print(repr(payload.strip()))
                last_end = match.end()
                self._buffer = self._buffer[last_end:]
        except Exception as e:
            print(f"Error in _process_sys_resource_buffer: {e}")

    def run_command(self, command=None, add_newline=True):
        """command can be str or bytes; if None, a newline is sent"""
        try:
            if not self.channel or self.channel.closed:
                return
            if command is None:
                payload = b"\n"
            else:
                if isinstance(command, bytes):
                    payload = command
                    if add_newline:
                        payload += b"\n"
                else:
                    payload = command.encode("utf-8")
                    if add_newline:
                        payload += b"\n"
            self.channel.send(payload)
        except Exception as e:
            self.error_occurred.emit(str(e))

    def resize_pty(self, cols: int, rows: int):
        try:
            if self.channel:
                self.channel.resize_pty(width=cols, height=rows)
        except Exception:
            pass

    def close(self):
        self._cleanup()

    def add_path_to_tree(self, path: str):
        """添加路径到文件树，并获取每个父目录下的文件夹"""
        if not self.for_file:
            return

        parts = path.strip('/').split('/')

        if '' not in self.file_tree:
            self.file_tree[''] = {}

        current = self.file_tree['']
        for i, part in enumerate(parts):
            full_path = '/' + '/'.join(parts[:i+1])
            if part not in current:
                current[part] = {}
                if i == len(parts) - 1:
                    self._get_directory_contents(full_path, current[part])

            current = current[part]

        self.file_tree_updated.emit(self.file_tree)

    def _get_directory_contents(self, path: str, node: Dict):
        try:
            command = f"ls -1 -p {path} | grep '/$' | sed 's#/$##'"
            self.run_command(command)
        except Exception as e:
            print(f"获取目录内容时出错: {e}")

    def remove_path_from_tree(self, path: str):
        if not self.for_file:
            return
        parts = path.strip('/').split('/')
        current = self.file_tree.get('', {})
        for i, part in enumerate(parts[:-1]):
            if part in current:
                current = current[part]
            else:
                return
        if parts and parts[-1] in current:
            del current[parts[-1]]
        self.file_tree_updated.emit(self.file_tree)

    def get_file_tree(self) -> Dict:
        return self.file_tree

    def is_connection_active(self) -> bool:
        """检查SSH连接是否仍然活跃"""
        try:
            if not self.conn or not self.conn.get_transport():
                return False
            return self.conn.get_transport().is_active()
        except Exception:
            return False

    def execute_command_and_capture(self, command: str):
        if self.is_capturing:
            self.error_occurred.emit(
                "Another command capture is already in progress.")
            return
        unique_id = str(uuid.uuid4())
        self.start_marker = f"START_CMD_MARKER_{unique_id}"
        self.end_marker = f"END_CMD_MARKER_{unique_id}"
        self.is_capturing = True
        self.capture_buffer = b""
        self.command_completed = False
        self.last_output_time = time.time()
        wrapped_command = f'echo "{self.start_marker}"\n{command}\n'
        self.run_command(wrapped_command, add_newline=False)
        if self.completion_timer:
            self.completion_timer.stop()
        self.completion_timer = QTimer(self)
        self.completion_timer.timeout.connect(
            self._check_interactive_completion)
        self.completion_timer.start(500)

    def _process_capture_buffer(self, force=False):
        try:
            if len(self.capture_buffer) > 0:
                self.last_output_time = time.time()
            start_bytes = self.start_marker.encode()
            end_bytes = self.end_marker.encode()
            start_idx = self.capture_buffer.rfind(start_bytes)
            if start_idx == -1:
                return
            content_after_start = self.capture_buffer[start_idx + len(
                start_bytes):]
            end_idx = content_after_start.find(end_bytes)
            if end_idx == -1 and not force:
                return
            if force:
                exit_code_part = b''
                end_idx = len(content_after_start)
            else:
                exit_code_part = content_after_start[end_idx + len(end_bytes):]
            exit_code_match = re.search(rb':(\d+)[\r\n]', exit_code_part)
            if not exit_code_match and not force:
                return
            actual_content_bytes = content_after_start[:end_idx]
            if actual_content_bytes.startswith(b'\r\n'):
                actual_content_bytes = actual_content_bytes[2:]
            elif actual_content_bytes.startswith(b'\n'):
                actual_content_bytes = actual_content_bytes[1:]
            elif actual_content_bytes.startswith(b'\r'):
                actual_content_bytes = actual_content_bytes[1:]
            lines = actual_content_bytes.split(b'\n')
            if len(lines) > 1:
                last_line = lines[-1].strip()
                if (not last_line or
                    b'EXIT_CODE' in last_line or
                        b'$' in last_line and b'#' in last_line):
                    actual_content_bytes = b'\n'.join(lines[:-1])
            actual_content_bytes = actual_content_bytes.rstrip(b'\r\n \t')
            exit_code = int(exit_code_match.group(
                1).decode()) if exit_code_match else 0
            output_str = actual_content_bytes.decode('utf-8', errors='replace')
            output_str = re.sub(r'\x1b\[[0-9;]*m', '', output_str)
            output_str = re.sub(r'\x1b\[\??[0-9;]*[a-zA-Z]', '', output_str)
            output_str = re.sub(
                r'\x1b\][^\x07\x1b]*[\x07\x1b]', '', output_str)
            output_str = re.sub(r'\x1b[PX^_][^\x1b]*\x1b\\', '', output_str)
            self.command_output_ready.emit(output_str, exit_code)
            self._reset_capture_state()
        except Exception as e:
            self.error_occurred.emit(f"Error processing command output: {e}")
            self._reset_capture_state()

    def _reset_capture_state(self):
        self.is_capturing = False
        self.capture_buffer = b""
        self.start_marker = ""
        self.end_marker = ""
        self.command_completed = False
        if self.completion_timer:
            self.completion_timer.stop()
            self.completion_timer = None

    def _check_interactive_completion(self):
        try:
            if not self.is_capturing or self.command_completed:
                return
            text = self.capture_buffer.decode('utf-8', errors='ignore').strip()
            lines = text.splitlines()
            if not lines:
                return
            last_line = re.sub(
                r'\x1b\[[0-9;?]*[a-zA-Z]', '', lines[-1]).strip()
            prompt_patterns = [
                r'(?:\([^\)]+\)\s)?\S+@\S+:.*[\$#]\s*$',
                r'\[\S+@\S+\s+\S+\][\$#]\s*$',
            ]
            for pattern in prompt_patterns:
                if re.search(pattern, last_line):
                    self.command_completed = True
                    if self.completion_timer:
                        self.completion_timer.stop()
                    self.run_command(
                        f'EXIT_CODE=$?; echo "{self.end_marker}:$EXIT_CODE"')
                    return
        except Exception as e:
            print(f"Error checking interactive completion: {e}")

    def execute_silent_command(self, command: str, timeout=15):
        if not self.is_connection_active():
            return None, "SSH connection is not active.", -1
        try:
            if not self.conn:
                return None, "SSH main connection is not available.", -1
            stdin, stdout, stderr = self.conn.exec_command(
                command, timeout=timeout)
            exit_code = stdout.channel.recv_exit_status()
            output = stdout.read().decode('utf-8', errors='ignore')
            error = stderr.read().decode('utf-8', errors='ignore')
            return output, error, exit_code
        except Exception as e:
            return None, str(e), -1

    def send_interrupt(self):
        """Sends an interrupt signal (Ctrl+C) to the channel."""
        try:
            if self.channel and not self.channel.closed:
                self.channel.send(b'\x03')
        except Exception as e:
            self.error_occurred.emit(f"Failed to send interrupt: {e}")
