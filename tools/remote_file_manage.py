# remote_file_manage.py
from PyQt5.QtCore import pyqtSignal, QThread, QMutex, QWaitCondition
import paramiko
import traceback
from typing import Dict, List, Optional
import stat
import os
from typing import Tuple


class RemoteFileManager(QThread):
    """
    远程文件管理器，负责构建和维护远程文件树
    通过 SSH 执行 ls 命令获取目录内容
    """
    file_tree_updated = pyqtSignal(dict, str)  # file tree , path
    error_occurred = pyqtSignal(str)
    sftp_ready = pyqtSignal()
    upload_progress = pyqtSignal(str, int)  # 文件路径, 进度百分比
    upload_finished = pyqtSignal(str, bool, str)  # 文件路径, 是否成功, 错误信息
    delete_finished = pyqtSignal(str, bool, str)  # 路径, 是否成功, 错误信息
    list_dir_finished = pyqtSignal(str, dict)  # path, result
    # path, result (e.g. "directory"/"file"/False)
    path_check_result = pyqtSignal(str, object)
    # remote_path , local_path , status , error msg
    download_finished = pyqtSignal(str, str, bool, str)
    # source_path, target_path, status, error msg
    copy_finished = pyqtSignal(str, str, bool, str)

    def __init__(self, session_info, parent=None, child_key=None):
        super().__init__(parent)
        self.session_info = session_info
        self.host = session_info.host
        self.user = session_info.username
        self.password = session_info.password
        self.port = session_info.port
        self.auth_type = session_info.auth_type
        self.key_path = session_info.key_path

        # SSH / SFTP 连接
        self.conn = None
        self.sftp = None

        # 文件树结构
        self.file_tree: Dict = {}

        # 线程控制
        self.mutex = QMutex()
        self.condition = QWaitCondition()
        self._is_running = True
        self._tasks = []

    # ---------------------------
    # 主线程循环
    # ---------------------------
    def run(self):
        try:
            # 建立 SSH 连接
            self.conn = paramiko.SSHClient()
            self.conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            if self.auth_type == "password":
                self.conn.connect(
                    self.host,
                    port=self.port,
                    username=self.user,
                    password=self.password,
                    timeout=30,
                    banner_timeout=30
                )
            else:
                self.conn.connect(
                    self.host,
                    port=self.port,
                    username=self.user,
                    key_filename=self.key_path,
                    timeout=30,
                    banner_timeout=30
                )

            # 建立 SFTP 连接
            self.sftp = self.conn.open_sftp()
            self.sftp_ready.emit()

            # 主循环
            while self._is_running:
                self.mutex.lock()
                if not self._tasks:
                    self.condition.wait(self.mutex)
                if self._tasks:
                    task = self._tasks.pop(0)
                    self.mutex.unlock()
                    try:
                        ttype = task.get('type')
                        if ttype == 'add_path':
                            self._add_path_to_tree(
                                task['path'], task["update_tree_sign"])
                        elif ttype == 'remove_path':
                            self._remove_path_from_tree(task['path'])
                        elif ttype == 'refresh':
                            self._refresh_paths_impl(task.get('paths'))
                        elif ttype == 'upload_file':
                            self._handle_upload_task(
                                task['local_path'],
                                task['remote_path'],
                                task.get('callback')
                            )
                        elif ttype == 'delete':
                            self._handle_delete_task(
                                task['path'],
                                task.get('callback')
                            )
                        elif ttype == "download_files":
                            self._download_files(task['path'])
                        elif ttype == 'list_dir':
                            print(f"处理：{[task['path']]}")
                            result = self.list_dir_simple(task['path'])

                            print(f"list dir : {result}")
                            self.list_dir_finished.emit(
                                task['path'], result or {})
                        elif ttype == 'check_path':
                            path_to_check = task['path']
                            try:
                                res = self.check_path_type(
                                    path_to_check)
                            except Exception as e:
                                res = False
                            self.path_check_result.emit(path_to_check, res)
                        elif ttype == 'copy_to':
                            self._handle_copy_task(
                                task['source_path'],
                                task['target_path'],
                                task.get('cut', False)
                            )
                        else:
                            print(f"Unknown task type: {ttype}")
                    except Exception as e:
                        self.error_occurred.emit(f"执行任务时出错: {e}")
                else:
                    self.mutex.unlock()

        except Exception as e:
            tb = traceback.format_exc()
            self.error_occurred.emit(f"远程文件管理器错误: {e}\n{tb}")
        finally:
            self._cleanup()

    # ---------------------------
    # 线程控制 & 清理
    # ---------------------------
    def stop(self):
        self._is_running = False
        self.condition.wakeAll()
        self.wait()

    def _cleanup(self):
        try:
            if self.sftp:
                self.sftp.close()
        except Exception:
            pass
        try:
            if self.conn:
                self.conn.close()
        except Exception:
            pass

    # ---------------------------
    # 公共任务接口
    # ---------------------------
    def copy_to(self, source_path: str, target_path: str, cut: bool = False):
        """
        异步复制/移动远程文件或目录，完成后触发 copy_finished 信号
        参数:
            source_path: 源路径
            target_path: 目标路径
            cut: True 表示移动（复制后删除源路径）
        """
        self.mutex.lock()
        self._tasks.append({
            'type': 'copy_to',
            'source_path': source_path,
            'target_path': target_path,
            'cut': cut
        })
        self.condition.wakeAll()
        self.mutex.unlock()

    def delete_path(self, path: str, callback=None):
        """
        删除远程路径（文件或目录）

        参数:
            path: str - 远程路径
            callback: 可选的回调函数，接收(是否成功, 错误信息)参数
        """
        self.mutex.lock()
        self._tasks.append({
            'type': 'delete',
            'path': path,
            'callback': callback
        })
        self.condition.wakeAll()
        self.mutex.unlock()

    def add_path(self, path: str, update_tree_sign=True):
        self.mutex.lock()
        self._tasks.append({'type': 'add_path', 'path': path,
                           "update_tree_sign": update_tree_sign})
        self.condition.wakeAll()
        self.mutex.unlock()

    def remove_path(self, path: str):
        self.mutex.lock()
        self._tasks.append({'type': 'remove_path', 'path': path})
        self.condition.wakeAll()
        self.mutex.unlock()

    def refresh_paths(self, paths: Optional[List[str]] = None):
        """刷新指定路径或所有目录"""
        self.mutex.lock()
        self._tasks.append({'type': 'refresh', 'paths': paths})
        self.condition.wakeAll()
        self.mutex.unlock()

    def check_path_async(self, path: str):
        self.mutex.lock()
        self._tasks.append({'type': 'check_path', 'path': path})
        self.condition.wakeAll()
        self.mutex.unlock()

    def list_dir_async(self, path: str):
        """异步列出目录"""
        self.mutex.lock()
        if any(t.get('type') == 'list_dir' and t.get('path') == path for t in self._tasks):
            self.mutex.unlock()
            return
        self._tasks.append({'type': 'list_dir', 'path': path})
        self.condition.wakeAll()
        self.mutex.unlock()

    def download_path_async(self, path: str):
        self.mutex.lock()
        self._tasks.append({'type': 'download_files', 'path': path})
        self.condition.wakeAll()
        self.mutex.unlock()

    def upload_file(self, local_path: str, remote_path: str, callback=None):
        """
        上传文件到远程服务器

        参数:
            local_path: 本地文件路径
            remote_path: 远程目标路径
            callback: 可选的回调函数，接收(是否成功, 错误信息)参数
        """
        self.mutex.lock()
        self._tasks.append({
            'type': 'upload_file',
            'local_path': local_path,
            'remote_path': remote_path,
            'callback': callback
        })
        self.condition.wakeAll()
        self.mutex.unlock()
    # ---------------------------
    # 文件上传实现
    # ---------------------------

    def _handle_upload_task(self, local_path: str, remote_path: str, callback=None):
        """
        处理文件上传任务（内部实现）- 支持文件和目录
        """
        if self.sftp is None:
            error_msg = "SFTP 连接未就绪"
            print(f"❌ 上传失败 - {error_msg}: {local_path} -> {remote_path}")
            self.upload_finished.emit(local_path, False, error_msg)
            if callback:
                callback(False, error_msg)
            return

        try:
            # 检查本地路径是否存在
            if not os.path.exists(local_path):
                error_msg = f"本地路径不存在: {local_path}"
                print(f"❌ 上传失败 - {error_msg}")
                self.upload_finished.emit(local_path, False, error_msg)
                if callback:
                    callback(False, error_msg)
                return

            # 判断是文件还是目录
            if os.path.isfile(local_path):
                self._upload_file(local_path, remote_path, callback)
            elif os.path.isdir(local_path):
                self._upload_directory(local_path, remote_path, callback)
            else:
                error_msg = f"路径不是文件也不是目录: {local_path}"
                print(f"❌ 上传失败 - {error_msg}")
                self.upload_finished.emit(local_path, False, error_msg)
                if callback:
                    callback(False, error_msg)

        except Exception as e:
            error_msg = f"上传过程错误: {str(e)}"
            print(f"❌ 上传失败 - {error_msg}")
            import traceback
            traceback.print_exc()
            self.upload_finished.emit(local_path, False, error_msg)
            if callback:
                callback(False, error_msg)

    def _upload_file(self, local_path: str, remote_path: str, callback=None):
        """上传单个文件"""
        try:
            # 获取文件信息用于调试
            file_size = os.path.getsize(local_path)
            print(f"📁 文件信息: {local_path}, 大小: {file_size} bytes")

            # 构建完整的远程文件路径
            remote_filename = os.path.basename(local_path)
            full_remote_path = f"{remote_path.rstrip('/')}/{remote_filename}"
            print(f"🎯 目标路径: {full_remote_path}")

            # 确保远程目录存在
            remote_dir = os.path.dirname(full_remote_path)
            print(f"📁 确保远程目录存在: {remote_dir}")
            dir_status, error = self._ensure_remote_directory_exists(
                remote_dir)
            if remote_dir and not dir_status:
                error_msg = f"无法创建远程目录: {remote_dir}\n{error}"
                print(f"❌ 上传失败 - {error_msg}")
                self.upload_finished.emit(local_path, False, error_msg)
                if callback:
                    callback(False, error_msg)
                return

            # 检查远程文件是否已存在
            try:
                self.sftp.stat(full_remote_path)
                print(f"⚠️  远程文件已存在: {full_remote_path}")
            except IOError:
                print("✅ 远程文件不存在，可以上传")

            # 自定义回调函数用于进度报告
            def progress_callback(bytes_so_far, total_bytes):
                if total_bytes > 0:
                    progress = int((bytes_so_far / total_bytes) * 100)
                    self.upload_progress.emit(local_path, progress)
                    if progress % 10 == 0:
                        print(f"📊 上传进度: {progress}%")

            # 执行上传
            print(f"🚀 开始上传文件: {local_path} -> {full_remote_path}")

            self.sftp.put(
                local_path,
                full_remote_path,
                callback=progress_callback
            )

            print(f"✅ 文件上传成功: {local_path} -> {full_remote_path}")
            self.upload_finished.emit(local_path, True, "")
            if callback:
                callback(True, "")

            # 上传完成后刷新远程目录
            if remote_dir:
                print("🔄 刷新远程目录...")
                self.refresh_paths([remote_dir])

        except Exception as upload_error:
            error_msg = f"文件上传错误: {str(upload_error)}"
            print(f"❌ 文件上传失败: {error_msg}")
            import traceback
            traceback.print_exc()
            self.upload_finished.emit(local_path, False, error_msg)
            if callback:
                callback(False, error_msg)

    def _upload_directory(self, local_dir: str, remote_dir: str, callback=None):
        """递归上传整个目录"""
        try:
            dir_name = os.path.basename(local_dir)
            target_remote_dir = f"{remote_dir.rstrip('/')}/{dir_name}"

            print(f"📁 开始上传目录: {local_dir} -> {target_remote_dir}")

            dir_status, error = self._ensure_remote_directory_exists(
                target_remote_dir)
            if not dir_status:
                error_msg = f"无法创建远程目录: {target_remote_dir}"
                print(f"❌ 目录上传失败 - {error_msg}\n{error}")
                self.upload_finished.emit(local_dir, False, error_msg)
                if callback:
                    callback(False, error_msg)
                return

            # 统计目录内容
            total_files = 0
            total_size = 0
            for root, dirs, files in os.walk(local_dir):
                total_files += len(files)
                for file in files:
                    file_path = os.path.join(root, file)
                    total_size += os.path.getsize(file_path)

            print(f"📊 目录统计: {total_files} 个文件, 总大小: {total_size} bytes")

            # 递归上传所有文件
            uploaded_files = 0
            uploaded_size = 0

            for root, dirs, files in os.walk(local_dir):
                # 创建对应的远程目录
                relative_path = os.path.relpath(root, local_dir)
                if relative_path == '.':
                    current_remote_dir = target_remote_dir
                else:
                    current_remote_dir = f"{target_remote_dir}/{relative_path}"
                dir_status, error = self._ensure_remote_directory_exists(
                    current_remote_dir)
                if not dir_status:
                    print(f"⚠️  跳过创建目录: {current_remote_dir}")
                    continue

                # 上传当前目录下的所有文件
                for file in files:
                    local_file_path = os.path.join(root, file)
                    remote_file_path = f"{current_remote_dir}/{file}"

                    try:
                        file_size = os.path.getsize(local_file_path)
                        self.sftp.put(local_file_path, remote_file_path)

                        uploaded_files += 1
                        uploaded_size += file_size

                        progress = int((uploaded_size / total_size)
                                       * 100) if total_size > 0 else 0
                        self.upload_progress.emit(local_dir, progress)

                        if uploaded_files % 10 == 0 or progress % 10 == 0:
                            print(
                                f"📊 目录上传进度: {progress}% ({uploaded_files}/{total_files} 文件)")

                    except Exception as file_error:
                        print(f"⚠️  文件上传失败 {local_file_path}: {file_error}")
                        # 继续上传其他文件

            print(f"✅ 目录上传完成: {local_dir} -> {target_remote_dir}")
            print(f"📊 上传结果: {uploaded_files}/{total_files} 个文件成功")

            self.upload_finished.emit(
                local_dir, True, f"成功上传 {uploaded_files}/{total_files} 个文件")
            if callback:
                callback(True, f"成功上传 {uploaded_files}/{total_files} 个文件")

            # 刷新远程目录
            self.refresh_paths([remote_dir])

        except Exception as dir_error:
            error_msg = f"目录上传错误: {str(dir_error)}"
            print(f"❌ 目录上传失败: {error_msg}")
            import traceback
            traceback.print_exc()
            self.upload_finished.emit(local_dir, False, error_msg)
            if callback:
                callback(False, error_msg)

    def _ensure_remote_directory_exists(self, remote_dir: str) -> Tuple[bool, str]:
        """
        确保远程目录存在，如果不存在则创建
        """
        try:
            # 尝试列出目录，如果不存在会抛出异常
            self.sftp.listdir(remote_dir)
            return True, ""
        except IOError:
            try:
                # 递归创建目录
                parts = remote_dir.strip('/').split('/')
                current_path = ''
                for part in parts:
                    current_path = current_path + '/' + part if current_path else '/' + part
                    try:
                        self.sftp.listdir(current_path)
                    except IOError:
                        self.sftp.mkdir(current_path)
                return True, ""
            except Exception as e:
                print(f"创建远程目录失败: {remote_dir}, 错误: {e}")
                return False, e
    # ---------------------------
    # 内部文件树操作
    # ---------------------------

    def _handle_copy_task(self, source_path: str, target_path: str, cut: bool = False):
        """
        内部处理复制/移动任务
        """
        if self.conn is None:
            error_msg = "SSH 连接未就绪"
            print(f"❌ 复制失败: {source_path} -> {target_path}, {error_msg}")
            self.copy_finished.emit(source_path, target_path, False, error_msg)
            return

        try:
            # 检查源路径
            path_type = self.check_path_type(source_path)
            if not path_type:
                error_msg = f"源路径不存在: {source_path}"
                print(f"❌ 复制失败: {error_msg}")
                self.copy_finished.emit(
                    source_path, target_path, False, error_msg)
                return

            print(f"📁 源路径类型: {path_type}")

            # 确保目标目录存在
            remote_dir = os.path.dirname(target_path.rstrip('/'))
            dir_status, error = self._ensure_remote_directory_exists(
                remote_dir)
            if remote_dir and not dir_status:
                error_msg = f"无法创建目标目录: {remote_dir}\n{error}"
                print(f"❌ 复制失败: {error_msg}")
                self.copy_finished.emit(
                    source_path, target_path, False, error_msg)
                return

            # 执行复制或移动
            cmd = f'cp -r "{source_path}" "{target_path}"'
            if cut:
                cmd = f'mv "{source_path}" "{target_path}"'

            print(f"🔧 执行命令: {cmd}")
            stdin, stdout, stderr = self.conn.exec_command(cmd)
            exit_status = stdout.channel.recv_exit_status()
            error_output = stderr.read().decode('utf-8').strip()

            if exit_status == 0:
                print(f"✅ 复制成功: {source_path} -> {target_path}")
                self.copy_finished.emit(source_path, target_path, True, "")

                # 刷新源和目标父目录
                parent_dirs = list(
                    {os.path.dirname(source_path), os.path.dirname(target_path)})
                self.refresh_paths(parent_dirs)

            else:
                error_msg = error_output if error_output else "未知错误"
                print(f"❌ 复制失败: {error_msg}")
                self.copy_finished.emit(
                    source_path, target_path, False, error_msg)

        except Exception as e:
            error_msg = f"复制过程错误: {str(e)}"
            print(f"❌ 复制失败: {error_msg}")
            import traceback
            traceback.print_exc()
            self.copy_finished.emit(source_path, target_path, False, error_msg)

    def _download_files(self, remote_path: str, local_base: str = "_ssh_download"):
        """
        同步下载文件或目录，完成后触发信号。
        返回: (local_path, status)
        """
        if self.sftp is None:
            print("SFTP 未连接，无法下载")
            return None, False

        local_base = os.path.abspath(local_base)
        os.makedirs(local_base, exist_ok=True)

        def _download_file(remote_file, local_file):
            try:
                self.sftp.get(remote_file, local_file)
                print(f"文件下载完成: {remote_file} -> {local_file}")
                return True
            except Exception as e:
                print(f"下载文件出错: {remote_file} -> {e}")
                return False

        def _download_dir(remote_dir, local_dir):
            os.makedirs(local_dir, exist_ok=True)
            success = True
            for entry in self.sftp.listdir_attr(remote_dir):
                remote_item = f"{remote_dir.rstrip('/')}/{entry.filename}"
                local_item = os.path.join(local_dir, entry.filename)

                if stat.S_ISDIR(entry.st_mode):
                    if not _download_dir(remote_item, local_item):
                        success = False
                else:
                    if not _download_file(remote_item, local_item):
                        success = False
            return success

        try:
            attr = self.sftp.stat(remote_path)
            filename = os.path.basename(remote_path.rstrip("/"))
            local_target = os.path.join(local_base, filename)

            if stat.S_ISDIR(attr.st_mode):
                status = _download_dir(remote_path, local_target)
            else:
                status = _download_file(remote_path, local_target)

            self.download_finished.emit(remote_path, local_target, status, "")
            return local_target, status

        except Exception as e:
            print(f"下载失败 {remote_path}: {e}")
            self.download_finished.emit(remote_path, "", False, e)
            return "", False

    def _add_path_to_tree(self, path: str, update_tree_sign: bool = True):
        parts = [p for p in path.strip("/").split("/") if p]
        if "" not in self.file_tree:
            self.file_tree[""] = {}
        current = self.file_tree[""]

        # 列出根目录
        try:
            self._get_directory_contents("/", current)
        except Exception as e:
            print(f"列出根目录时出错: {e}")

        # 逐级添加
        full_path_parts = []
        for part in parts:
            full_path_parts.append(part)
            full_path = "/" + "/".join(full_path_parts)
            if part not in current or not isinstance(current[part], dict):
                current[part] = {}
            try:
                self._get_directory_contents(full_path, current[part])
            except Exception as e:
                print(f"列出目录 {full_path} 时出错: {e}")
            current = current[part]
        if update_tree_sign:
            self.file_tree_updated.emit(self.file_tree, path)

    def _remove_path_from_tree(self, path: str):
        parts = path.strip('/').split('/')
        current = self.file_tree.get('', {})
        for part in parts[:-1]:
            if part in current:
                current = current[part]
            else:
                return
        if parts and parts[-1] in current:
            del current[parts[-1]]
        self.file_tree_updated.emit(self.file_tree, path)

    def _get_directory_contents(self, path: str, node: Dict):
        try:
            for attr in self.sftp.listdir_attr(path):
                name = attr.filename
                full_path = f"{path.rstrip('/')}/{name}"
                if stat.S_ISLNK(attr.st_mode):
                    try:
                        target = self.sftp.stat(full_path)
                        if stat.S_ISDIR(target.st_mode):
                            node[name] = node.get(name, {})
                        else:
                            node[name] = "is_file"
                    except Exception:
                        node[name] = "is_symlink_broken"
                elif stat.S_ISDIR(attr.st_mode):
                    node[name] = node.get(name, {})
                else:
                    node[name] = "is_file"
        except Exception as e:
            print(f"获取目录内容时出错: {e}")

    # ---------------------------
    # 刷新功能
    # ---------------------------
    def _refresh_paths_impl(self, paths: Optional[List[str]] = None):
        """线程内部刷新目录"""
        if self.sftp is None:
            print("_refresh_paths_impl: sftp 未就绪")
            return

        # 构建刷新列表
        if paths is None:
            to_refresh = []

            def walk_existing(node: Dict, cur_path: str):
                if not isinstance(node, dict):
                    return
                pathstr = '/' if cur_path == '' else cur_path
                to_refresh.append(pathstr)
                # 只遍历已有非空子目录
                for name, child in node.items():
                    if isinstance(child, dict) and child:  # 只有非空字典才继续
                        child_path = (cur_path.rstrip('/') + '/' +
                                      name) if cur_path else '/' + name
                        walk_existing(child, child_path)

            walk_existing(self.file_tree.get('', {}), '')
        else:
            to_refresh = [
                '/' + p.strip('/') if p.strip('/') else '/' for p in paths]

        # 去重
        dirs = list(dict.fromkeys(to_refresh))

        # 遍历刷新
        for directory in dirs:
            try:
                node = self._find_node_by_path(directory)
                if node is None:
                    if directory == '/':
                        if '' not in self.file_tree:
                            self.file_tree[''] = {}
                        node = self.file_tree['']
                    else:
                        parts = [p for p in directory.strip(
                            '/').split('/') if p]
                        if '' not in self.file_tree:
                            self.file_tree[''] = {}
                        cur = self.file_tree['']
                        for part in parts:
                            if part not in cur or cur[part] == "is_file":
                                cur[part] = {}
                            cur = cur[part]
                        node = cur

                try:
                    entries = self.sftp.listdir_attr(directory)
                except IOError as e:
                    print(
                        f"_refresh_paths_impl: listdir_attr({directory}) failed: {e}")
                    continue

                new_map = {}
                for attr in entries:
                    name = attr.filename
                    full = directory.rstrip(
                        '/') + '/' + name if directory != '/' else '/' + name
                    try:
                        if stat.S_ISLNK(attr.st_mode):
                            try:
                                tattr = self.sftp.stat(full)
                                if stat.S_ISDIR(tattr.st_mode):
                                    new_map[name] = node.get(name, {}) if isinstance(
                                        node.get(name), dict) else {}
                                else:
                                    new_map[name] = "is_file"
                            except Exception:
                                new_map[name] = "is_symlink_broken"
                        elif stat.S_ISDIR(attr.st_mode):
                            new_map[name] = node.get(name, {}) if isinstance(
                                node.get(name), dict) else {}
                        else:
                            new_map[name] = "is_file"
                    except Exception:
                        new_map[name] = "is_file"

                if not isinstance(node, dict):
                    if directory == '/':
                        self.file_tree[''] = new_map
                    else:
                        parent_path = '/' + \
                            '/'.join(directory.strip('/').split('/')
                                     [:-1]) if '/' in directory.strip('/') else '/'
                        parent_node = self._find_node_by_path(parent_path)
                        last_name = directory.strip('/').split('/')[-1]
                        if isinstance(parent_node, dict):
                            parent_node[last_name] = new_map
                else:
                    node.clear()
                    node.update(new_map)

            except Exception as e:
                print(f"_refresh_paths_impl error for {directory}: {e}")

        self.file_tree_updated.emit(self.file_tree, "")

    # ---------------------------
    # 辅助方法
    # ---------------------------
    def _find_node_by_path(self, path: str) -> Optional[Dict]:
        if not path:
            return None
        if path == '/' or path.strip('/') == '':
            return self.file_tree.get('', {})

        parts = [p for p in path.strip('/').split('/') if p]
        node = self.file_tree.get('', {})
        for part in parts:
            if not isinstance(node, dict):
                return None
            if part not in node:
                return None
            node = node[part]
        return node if isinstance(node, dict) else None

    def get_file_tree(self) -> Dict:
        return self.file_tree

    def check_path_type(self, path: str):
        try:
            attr = self.sftp.lstat(path)
            if stat.S_ISDIR(attr.st_mode):
                return "directory"
            elif stat.S_ISREG(attr.st_mode):
                return "file"
            elif stat.S_ISLNK(attr.st_mode):
                try:
                    target = self.sftp.stat(path)
                    return "directory" if stat.S_ISDIR(target.st_mode) else "file"
                except Exception:
                    return "symlink_broken"
            else:
                return False
        except IOError:
            return False

    def get_default_path(self) -> Optional[str]:
        try:
            if self.conn is None:
                print("SSH 连接未建立")
                return None
            stdin, stdout, stderr = self.conn.exec_command("pwd")
            exit_status = stdout.channel.recv_exit_status()
            path = stdout.read().decode('utf-8').strip()
            error = stderr.read().decode('utf-8').strip()
            if exit_status != 0 or error:
                print(f"执行 pwd 出错: {error}")
                return None
            return path
        except Exception as e:
            print(f"获取默认路径失败: {e}")
            return None

    def list_dir_simple(self, path: str) -> Optional[Dict[str, bool]]:
        """
        列出目录内容，返回 {name: True/False}
        True 表示目录，False 表示文件/其他
        """
        if self.sftp is None:
            print("list_dir_simple: sftp 未就绪")
            return None
        print(path)
        result: Dict[str, bool] = {}
        try:
            items = self.sftp.listdir_attr(path)
            # print(items)
            for attr in items:
                name = attr.filename
                full_path = f"{path.rstrip('/')}/{name}"

                if stat.S_ISDIR(attr.st_mode):
                    result[name] = True
                elif stat.S_ISLNK(attr.st_mode):
                    try:
                        target = self.sftp.stat(full_path)
                        result[name] = stat.S_ISDIR(target.st_mode)
                    except Exception:
                        result[name] = False
                else:
                    result[name] = False
            print(f"处理result完成 {result}")
            return result
        except Exception as e:
            print(f"list_dir_simple 获取目录内容时出错: {e}")
            return None

    # ---------------------------
    # 删除功能实现
    # ---------------------------

    def _handle_delete_task(self, remote_path: str, callback=None):
        """
        处理删除任务（内部实现）
        """
        if self.conn is None:
            error_msg = "SSH 连接未就绪"
            print(f"❌ 删除失败 - {error_msg}: {remote_path}")
            self.delete_finished.emit(remote_path, False, error_msg)
            if callback:
                callback(False, error_msg)
            return

        try:
            print(f"🗑️  开始删除: {remote_path}")

            # 先检查路径是否存在
            try:
                path_type = self.check_path_type(remote_path)
                if not path_type:
                    error_msg = f"路径不存在: {remote_path}"
                    print(f"❌ 删除失败 - {error_msg}")
                    self.delete_finished.emit(remote_path, False, error_msg)
                    if callback:
                        callback(False, error_msg)
                    return

                print(f"📁 路径类型: {path_type}")

            except Exception as e:
                error_msg = f"检查路径时出错: {str(e)}"
                print(f"❌ 删除失败 - {error_msg}")
                self.delete_finished.emit(remote_path, False, error_msg)
                if callback:
                    callback(False, error_msg)
                return

            # 执行删除命令
            cmd = f'rm -rf "{remote_path}"'
            print(f"🔧 执行命令: {cmd}")

            stdin, stdout, stderr = self.conn.exec_command(cmd)
            exit_status = stdout.channel.recv_exit_status()
            error_output = stderr.read().decode('utf-8').strip()

            if exit_status == 0:
                print(f"✅ 删除成功: {remote_path}")
                self.delete_finished.emit(remote_path, True, "")

                # 刷新父目录
                parent_dir = os.path.dirname(remote_path)
                if parent_dir:
                    print(f"🔄 刷新父目录: {parent_dir}")
                    self.refresh_paths([parent_dir])

                if callback:
                    callback(True, "")
            else:
                error_msg = f"删除命令执行失败: {error_output}" if error_output else "未知错误"
                print(f"❌ 删除失败 - {error_msg}")
                self.delete_finished.emit(remote_path, False, error_msg)
                if callback:
                    callback(False, error_msg)

        except Exception as e:
            error_msg = f"删除过程错误: {str(e)}"
            print(f"❌ 删除失败 - {error_msg}")
            import traceback
            traceback.print_exc()
            self.delete_finished.emit(remote_path, False, error_msg)
            if callback:
                callback(False, error_msg)

    # ---------------------------
    # 辅助方法 - 添加安全的路径处理
    # ---------------------------
    def _sanitize_path(self, path: str) -> str:
        """
        对路径进行基本的清理和安全检查
        """
        if not path or path.strip() == "":
            return ""

        # 移除多余的斜杠和空格
        sanitized = path.strip().rstrip('/')

        # 基本的安全检查（防止删除关键目录）
        critical_paths = ['/', '/root', '/home',
                          '/etc', '/bin', '/sbin', '/usr', '/var']
        if sanitized in critical_paths:
            raise ValueError(f"禁止删除关键目录: {sanitized}")

        return sanitized

    # 修改现有的 remove_path_force 方法，使其使用新的删除逻辑
    def remove_path_force(self, path: str) -> bool:
        """
        尝试删除指定路径（文件或文件夹），使用 rm -rf
        返回 True 表示删除成功，False 表示失败
        """
        try:
            sanitized_path = self._sanitize_path(path)
            if not sanitized_path:
                return False

            # 使用新的删除方法
            success = False
            error_msg = ""

            # 创建同步等待机制
            from PyQt5.QtCore import QEventLoop, QTimer
            loop = QEventLoop()

            def delete_callback(s, e):
                nonlocal success, error_msg
                success = s
                error_msg = e
                loop.quit()

            self.delete_path(sanitized_path, delete_callback)

            # 设置超时
            QTimer.singleShot(30000, loop.quit)  # 30秒超时

            loop.exec_()

            return success

        except Exception as e:
            print(f"删除路径 {path} 出错: {e}")
            return False
