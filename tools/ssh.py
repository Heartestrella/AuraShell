import os
import re
import json
import traceback
import paramiko
from typing import Dict, List
from PyQt5.QtCore import QThread, QTimer, pyqtSignal


class SSHWorker(QThread):
    result_ready = pyqtSignal(bytes)
    connected = pyqtSignal(bool, str)
    error_occurred = pyqtSignal(str)
    sys_resource = pyqtSignal(dict)
    file_tree_updated = pyqtSignal(dict)

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
        self._buffer = b""  # 存储未完整的输出数据

        # 文件树结构
        self.file_tree: Dict = {}
        # 存储每个目录的内容
        self.dir_contents: Dict[str, List[str]] = {}

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
                    remote_proc = "./.ssh/processes"

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
                        st = sftp.stat(remote_proc)
                        print(f"远端 processes 存在: {remote_proc}")
                    except IOError:
                        exists_remote_proc = False
                        print(f"远端 processes 不存在: {remote_proc}")

                    if exists_remote_proc:
                        # 尝试把它设置为可执行
                        try:
                            # 使用 stat 返回的模式或直接设置 0o755
                            try:
                                current_mode = st.st_mode
                                new_mode = current_mode | 0o111
                                sftp.chmod(remote_proc, new_mode)
                            except Exception:
                                sftp.chmod(remote_proc, 0o755)
                            print(f"已将远端文件 {remote_proc} 设为可执行")
                        except Exception as e:
                            print(f"设为可执行失败: {e}")
                    else:
                        # 上传本地文件到 remote_proc
                        local_proc = os.path.join(
                            os.getcwd(), "resource", "resources_software", "linux64", "processes")
                        if not os.path.exists(local_proc):
                            # 如果没有文件，尝试发出错误提示（也可以决定 fallback 去执行 python3 processes.py）
                            err = f"本地 processes 文件不存在: {local_proc}"
                            print(err)
                            self.error_occurred.emit(err)
                        else:
                            try:
                                print(
                                    f"上传本地 {local_proc} 到远端 {remote_proc} ...")
                                sftp.put(local_proc, remote_proc)
                                # 设置权限为可执行
                                try:
                                    sftp.chmod(remote_proc, 0o755)
                                except Exception:
                                    # 某些 sftp 实现可能不允许 chmod，忽略
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

            # 启动资源脚本/程序（如果 for_resources 打开）
            self.timer = QTimer()
            self.timer.timeout.connect(self._check_output)
            self.timer.start(100)

            # 改为执行可执行程序（非 python3 processes.py）
            if self.for_resources:
                # 执行 ./ .ssh/processes（使用相对路径）
                try:
                    self.run_command("./.ssh/processes")
                    print("已启动远端 processes 可执行文件（./.ssh/processes）")
                except Exception as e:
                    print(f"启动 processes 失败，尝试回退：{e}")
                    # 最后回退：使用 python3 processes.py（尽量避免）
                    try:
                        self.run_command("python3 processes.py")
                    except Exception as e2:
                        print(f"回退执行 python3 也失败: {e2}")

            self.exec_()  # 进入线程事件循环

            # 退出后清理
            self._cleanup()

        except Exception as e:
            tb = traceback.format_exc()
            self.error_occurred.emit(f"{e}\n{tb}")

    def _cleanup(self):
        try:
            if self.timer:
                self.timer.stop()
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
        self.quit()

    def _check_output(self):
        try:
            if not self.channel:
                return
            if self.channel.recv_ready():
                chunk = self.channel.recv(4096)  # bytes
                self.result_ready.emit(chunk)    # 先发原始输出
                if self.for_resources:
                    self._buffer += chunk
                    self._process_sys_resource_buffer()

            # 检查远端关闭
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
        从 _buffer 中提取 ///Start ... End/// 的 JSON 并发射 sys_resource 信号
        """
        try:
            text = self._buffer.decode(errors='ignore')
            # print(f"Sys resources text {text}")
            pattern = re.compile(r'///Start(.*?)End///', re.DOTALL)
            matches = pattern.findall(text)
            for match in matches:
                try:
                    data = json.loads(match.strip())
                    # print(data)
                    self.sys_resource.emit(data)
                except Exception as e:
                    # JSON 解析失败，忽略
                    continue
            # 清理已处理部分
            if matches:
                last_end = text.rfind("End///") + len("End///")
                self._buffer = self._buffer[last_end:]
        except Exception:
            pass

    def run_command(self, command=None, add_newline=True):
        """command 可以是 str 或 bytes；若为 None 则发送换行"""
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

    # 新增方法：添加路径到文件树
    def add_path_to_tree(self, path: str):
        """添加路径到文件树，并获取每个父目录下的文件夹"""
        if not self.for_file:
            return

        # 分割路径
        parts = path.strip('/').split('/')

        # 确保根目录存在
        if '' not in self.file_tree:
            self.file_tree[''] = {}

        current = self.file_tree['']

        # 遍历路径的每一部分
        for i, part in enumerate(parts):
            full_path = '/' + '/'.join(parts[:i+1])

            # 如果这部分不存在于当前层级，添加它
            if part not in current:
                current[part] = {}

                # 获取该目录下的文件夹列表
                if i == len(parts) - 1:  # 只对最后一级目录获取内容
                    self._get_directory_contents(full_path, current[part])

            # 移动到下一层级
            current = current[part]

        # 发射更新后的文件树
        self.file_tree_updated.emit(self.file_tree)

    def _get_directory_contents(self, path: str, node: Dict):
        """获取指定目录下的文件夹列表"""
        try:
            # 执行 ls 命令获取目录内容（仅目录）
            # 使用 -p 标记并过滤末尾斜杠，返回目录名列表
            command = f"ls -1 -p {path} | grep '/$' | sed 's#/$##'"
            self.run_command(command)
            # 注意：这里输出会通过 channel 输出回到 _check_output -> result_ready，你需要在上层解析这些行
        except Exception as e:
            print(f"获取目录内容时出错: {e}")

    # 新增方法：从文件树中移除路径
    def remove_path_from_tree(self, path: str):
        """从文件树中移除路径及其子目录"""
        if not self.for_file:
            return

        parts = path.strip('/').split('/')
        current = self.file_tree.get('', {})

        # 遍历到要删除的节点的父节点
        for i, part in enumerate(parts[:-1]):
            if part in current:
                current = current[part]
            else:
                return  # 路径不存在

        # 删除目标节点
        if parts and parts[-1] in current:
            del current[parts[-1]]

        # 发射更新后的文件树
        self.file_tree_updated.emit(self.file_tree)

    # 新增方法：获取文件树
    def get_file_tree(self) -> Dict:
        """获取当前的文件树"""
        return self.file_tree
