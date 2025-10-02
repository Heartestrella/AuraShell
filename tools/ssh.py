import os
import re
import json
import traceback
import paramiko
from typing import Dict, List
from PyQt5.QtCore import QThread, QTimer, pyqtSignal
from tools.atool import resource_path
import binascii


class SSHWorker(QThread):
    result_ready = pyqtSignal(bytes)
    connected = pyqtSignal(bool, str)
    error_occurred = pyqtSignal(str)
    sys_resource = pyqtSignal(dict)
    file_tree_updated = pyqtSignal(dict)
    # host_key , processes_md5 key
    key_verification = pyqtSignal(str, str)
    stop_timer_sig = pyqtSignal()

    def __init__(self, session_info, parent=None, for_resources=False, for_file=False):
        super().__init__(parent)
        self.host = session_info.host
        self.user = session_info.username
        self.port = session_info.port
        self.password = session_info.password
        self.auth_type = session_info.auth_type
        self.key_path = session_info.key_path
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

    def run(self):
        try:
            self.conn = paramiko.SSHClient()
            self.conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            if self.auth_type == "password":
                self.conn.connect(self.host, username=self.user,
                                  password=self.password, timeout=10, port=self.port)
            else:
                self.conn.connect(self.host, username=self.user,
                                  key_filename=self.key_path, timeout=10, port=self.port)

            transport = self.conn.get_transport()
            self.channel = transport.open_session()
            self.channel.get_pty(term='xterm', width=120, height=30)
            self.channel.invoke_shell()
            self.connected.emit(True, "连接成功")

            # ---------- resources handling: ensure ./ .ssh/processes exists & is executable ----------
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

                    exists_remote_proc = True
                    try:
                        st = sftp.stat(self.remote_proc)
                        print(f"远端 processes 存在: {self.remote_proc}")
                    except IOError:
                        exists_remote_proc = False
                        print(f"远端 processes 不存在: {self.remote_proc}")

                    if exists_remote_proc:
                        try:
                            try:
                                current_mode = st.st_mode
                                new_mode = current_mode | 0o111
                                sftp.chmod(self.remote_proc, new_mode)
                            except Exception:
                                sftp.chmod(self.remote_proc, 0o755)
                            print(f"已将远端文件 {self.remote_proc} 设为可执行")
                        except Exception as e:
                            print(f"设为可执行失败: {e}")
                    else:

                        if not os.path.exists(self.local_proc):
                            err = f"本地 processes 文件不存在: {self.local_proc}"
                            print(err)
                            self.error_occurred.emit(err)
                        else:
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
                    try:
                        sftp.close()
                    except Exception:
                        pass
                except Exception as e:
                    tb = traceback.format_exc()
                    print(f"resources pre-check/upload 出错: {e}\n{tb}")
                    self.error_occurred.emit(
                        f"resources pre-check/upload 出错: {e}")

            self.timer = QTimer()
            self.stop_timer_sig.connect(self.timer.stop)
            self.timer.timeout.connect(self._check_output)
            self.timer.start(100)
            if self.for_resources:
                md5 = self.get_remote_md5(self.remote_proc)
                host_key = self.get_hostkey_fp_hex()
                self.key_verification.emit(md5, host_key)
                # print(md5, host_key)
                if self.user == "root":
                    cmd = f'./.ssh/processes.sh'
                    print("Running without sudo as root")
                else:
                    cmd = f'echo {self.password} | sudo -S ./.ssh/processes.sh'
                    print("Running with sudo as non-root")
                try:
                    self.run_command(cmd)
                    print("已启动远端 processes 可执行文件（./.ssh/processes）")
                except Exception as e:
                    print(f"启动 processes 失败：{e}")

            self.exec_()
            self._cleanup()

        except Exception as e:
            tb = traceback.format_exc()
            self.error_occurred.emit(f"{e}\n{tb}")

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
            if self.channel:
                self.channel.close()
        except Exception:
            pass
        try:
            if self.conn:
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
            if self.channel.recv_ready():
                chunk = self.channel.recv(4096)  # bytes
                self.result_ready.emit(chunk)
                if self.for_resources:
                    self._buffer += chunk
                    self._process_sys_resource_buffer()

            if self.channel.closed or self.channel.exit_status_ready():
                while self.channel.recv_ready():
                    chunk = self.channel.recv(4096)
                    self.result_ready.emit(chunk)
                    if self.for_resources:
                        self._buffer += chunk
                        self._process_sys_resource_buffer()
                self.quit()
        except Exception as e:
            self.error_occurred.emit(str(e))

    def _process_sys_resource_buffer(self):
        """
        Extract the ///Start ... End/// or ///SysInfo ... End/// JSON from _buffer 
        and emit the sys_resource signal
        """
        try:
            text = self._buffer.decode(errors='ignore')
            # print(text)
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
                except Exception:
                    pass

                last_end = match.end()
                self._buffer = self._buffer[last_end:]
        except Exception:
            pass

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
                return  # Path does not exist

        if parts and parts[-1] in current:
            del current[parts[-1]]

        self.file_tree_updated.emit(self.file_tree)

    def get_file_tree(self) -> Dict:
        return self.file_tree
