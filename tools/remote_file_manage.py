# remote_file_manage.py
from PyQt5.QtCore import pyqtSignal, QThread, QMutex, QWaitCondition, QThreadPool
from tools.transfer_worker import TransferWorker
from tools.setting_config import SCM
import paramiko
import traceback
from typing import Dict, List, Optional
import stat
import os
from typing import Tuple
from datetime import datetime
import shlex


class RemoteFileManager(QThread):
    """
    Remote file manager, responsible for building and maintaining remote file trees
    """
    file_tree_updated = pyqtSignal(dict, str)  # file tree , path
    error_occurred = pyqtSignal(str)
    sftp_ready = pyqtSignal()
    upload_progress = pyqtSignal(str, int)  # File path, progress percentage
    download_progress = pyqtSignal(str, int)  # File path, progress percentage
    # File path, success, error message
    upload_finished = pyqtSignal(str, bool, str)
    # Path, success, error message
    delete_finished = pyqtSignal(str, bool, str)
    list_dir_finished = pyqtSignal(str, list)  # path, result
    # path, result (e.g. "directory"/"file"/False)
    path_check_result = pyqtSignal(str, object)
    # remote_path , local_path , status , error msg,open it
    download_finished = pyqtSignal(str, str, bool, str, bool)
    # source_path, target_path, status, error msg
    copy_finished = pyqtSignal(str, str, bool, str)
    # Original path, new path, success, error message
    rename_finished = pyqtSignal(str, str, bool, str)
    # path, info(dict), status(bool), error_msg(str)
    file_info_ready = pyqtSignal(str, dict, bool, str)
    # path , type
    file_type_ready = pyqtSignal(str, str)
    # path , status , error_msg
    mkdir_finished = pyqtSignal(str, bool, str)
    # target_zip_path
    start_to_compression = pyqtSignal(str)
    # remote_path_path
    start_to_uncompression = pyqtSignal(str)

    def __init__(self, session_info, parent=None, child_key=None):
        super().__init__(parent)
        self.session_info = session_info
        self.host = session_info.host
        self.user = session_info.username
        self.password = session_info.password
        self.port = session_info.port
        self.auth_type = session_info.auth_type
        self.key_path = session_info.key_path

        self.conn = None
        self.sftp = None

        # File_tree
        self.file_tree: Dict = {}

        # UID/GID Caching
        self.uid_map: Dict[int, str] = {}
        self.gid_map: Dict[int, str] = {}

        # Thread Control
        self.mutex = QMutex()
        self.condition = QWaitCondition()
        self._is_running = True
        self._tasks = []

        # Thread pool for handling concurrent transfers
        self.thread_pool = QThreadPool()
        config = SCM().read_config()
        max_threads = config.get("max_concurrent_transfers", 4)
        self.thread_pool.setMaxThreadCount(max_threads)

    # ---------------------------
    # Main thread loop
    # ---------------------------
    def run(self):
        try:
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

            self.sftp = self.conn.open_sftp()
            self.sftp_ready.emit()
            self._fetch_user_group_maps()
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
                            self._dispatch_transfer_task(
                                'upload',
                                task['local_path'],
                                task['remote_path'],
                                task['compression']
                            )
                        elif ttype == 'delete':
                            self._handle_delete_task(
                                task['path'],
                                task.get('callback')
                            )
                        elif ttype == "download_files":
                            self._dispatch_transfer_task(
                                'download',
                                None,  # local_path is not used by download worker
                                task['path'],
                                task["compression"],
                                open_it=task["open_it"]
                            )
                        elif ttype == 'list_dir':
                            # print(f"Handle:{[task['path']]}")
                            result = self.list_dir_detailed(task['path'])
                            # print(f"List dir : {result}")
                            self.list_dir_finished.emit(
                                task['path'], result or [])
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
                        elif ttype == 'rename':
                            self._handle_rename_task(
                                task['path'],
                                task['new_name'],
                                task.get('callback')
                            )
                        elif ttype == 'file_info':
                            path, info_dict, status, error_msg = self._get_file_info(
                                task['path'])
                            self.file_info_ready.emit(
                                path, info_dict, status, error_msg)
                        elif ttype == 'file_type':
                            self.classify_file_type_using_file(task['path'])
                        elif ttype == 'mkdir':
                            self._handle_mkdir_task(
                                task['path'], task.get('callback'))
                        else:
                            print(f"Unknown task type: {ttype}")
                    except Exception as e:
                        self.error_occurred.emit(
                            f"Error while executing task: {e}")
                else:
                    self.mutex.unlock()

        except Exception as e:
            tb = traceback.format_exc()
            self.error_occurred.emit(f"Remote File Manager Error: {e}\n{tb}")
        finally:
            self._cleanup()

    # ---------------------------
    # Thread Control & Cleanup
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
    # Transfer Worker Management
    # ---------------------------
        # try:
        #     signals = [
        #         'file_tree_updated', 'error_occurred', 'sftp_ready', 'upload_progress',
        #         'upload_finished', 'delete_finished', 'list_dir_finished', 'path_check_result',
        #         'download_finished', 'copy_finished', 'rename_finished', 'file_info_ready',
        #         'file_type_ready', 'mkdir_finished', 'start_to_compression', 'start_to_uncompression'
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

    def _dispatch_transfer_task(self, action, local_path, remote_path, compression, open_it=False):
        """Creates and starts TransferWorker(s) for uploads or downloads."""
        
        paths_to_process = []
        if action == 'upload':
            paths_to_process = local_path if isinstance(local_path, list) else [local_path]
        elif action == 'download':
            paths_to_process = remote_path if isinstance(remote_path, list) else [remote_path]

        # If compression is enabled for a list, treat it as a single task.
        if compression and isinstance(paths_to_process, list) and len(paths_to_process) > 1:
            self._create_and_start_worker(action, paths_to_process, remote_path, compression, open_it)
        else:
            # For non-compressed lists or single items, create a worker for each item.
            for path_item in paths_to_process:
                item_local_path = path_item if action == 'upload' else None
                item_remote_path = path_item if action == 'download' else remote_path
                self._create_and_start_worker(action, item_local_path, item_remote_path, compression, open_it)

    def _create_and_start_worker(self, action, local_path, remote_path, compression, open_it=False):
        """Helper to create, connect signals, and start a single TransferWorker."""
        worker = TransferWorker(
            self.session_info,
            action,
            local_path,
            remote_path,
            compression
        )

        if action == 'upload':
            worker.signals.finished.connect(self.upload_finished)
            # Refresh the parent directory of the remote path upon successful upload.
            worker.signals.finished.connect(
                lambda path, success, msg: self.refresh_paths(
                    [os.path.dirname(remote_path.rstrip('/'))]) if success and remote_path else None
            )
            worker.signals.progress.connect(self.upload_progress)
            worker.signals.start_to_compression.connect(self.start_to_compression)
            worker.signals.start_to_uncompression.connect(self.start_to_uncompression)

        elif action == 'download':
            worker.signals.finished.connect(
                lambda identifier, success, msg: self.download_finished.emit(
                    identifier, msg if success else "", success, "" if success else msg, open_it
                )
            )
            worker.signals.progress.connect(self.download_progress)

        self.thread_pool.start(worker)

    # ---------------------------
    # Public task API
    # ---------------------------

    def mkdir(self, path: str, callback=None):
        self.mutex.lock()
        self._tasks.append({
            'type': 'mkdir',
            'path': path,
            "callback": callback,
        })
        self.condition.wakeAll()
        self.mutex.unlock()

    def get_file_type(self, path: str):
        self.mutex.lock()
        self._tasks.append({'type': 'file_type', 'path': path})
        self.condition.wakeAll()
        self.mutex.unlock()

    def get_file_info(self, path: str):
        """
        The result is sent via the file_info_ready signal.
        """
        self.mutex.lock()
        self._tasks.append({'type': 'file_info', 'path': path})
        self.condition.wakeAll()
        self.mutex.unlock()

    def copy_to(self, source_path: str, target_path: str, cut: bool = False):
        """
    Asynchronously copies or moves a remote file or directory.

    This method queues a copy or move task to be executed in the background.
    When the operation is complete, the `copy_finished` signal is emitted.

    Args:
        source_path (str): The source path of the file or directory to copy/move.
        target_path (str): The destination path where the file or directory will be copied/moved.
        cut (bool, optional): If True, moves the file or directory (deletes the source after copying).
                              If False, copies the file or directory without deleting the source.
                              Defaults to False.

    Signals:
        copy_finished (str, str, bool, str): Emitted upon completion with parameters:
            - source_path (str): The original source path.
            - target_path (str): The target path.
            - success (bool): True if the operation succeeded, False otherwise.
            - error_msg (str): Error message if the operation failed, empty string otherwise.
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

    def delete_path(self, path, callback=None):
        """
        Asynchronously deletes a remote file or directory.

        This method queues a delete task to be executed in the background.
        Upon completion, the `delete_finished` signal is emitted.

        Args:
            path (str): The remote path of the file or directory to delete.
            callback (callable, optional): A function to be called when the deletion
                is complete. The callback receives two arguments:
                - success (bool): True if deletion succeeded, False otherwise.
                - error_msg (str): Error message if deletion failed, empty string otherwise.

        Signals:
            delete_finished (str, bool, str): Emitted upon completion with parameters:
                - path (str): The path that was deleted.
                - success (bool): True if deletion succeeded, False otherwise.
                - error_msg (str): Error message if deletion failed, empty string otherwise.
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
        """Refresh the specified path or all directories if paths is None"""
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
        """List a directory"""
        self.mutex.lock()
        if any(t.get('type') == 'list_dir' and t.get('path') == path for t in self._tasks):
            self.mutex.unlock()
            return
        self._tasks.append({'type': 'list_dir', 'path': path})
        self.condition.wakeAll()
        self.mutex.unlock()

    def download_path_async(self, path: str, open_it: bool = False, compression=False):
        self.mutex.lock()
        self._tasks.append(
            {'type': 'download_files', 'path': path, "open_it": open_it, "compression": compression})
        self.condition.wakeAll()
        self.mutex.unlock()

    def rename(self, path: str, new_name: str, callback=None):
        """
        Asynchronously renames a remote file or directory.

        This method queues a rename task to be executed in the background.
        Upon completion, the `rename_finished` signal is emitted.

        Args:
            path (str): The remote path of the file or directory to rename.
            new_name (str): The new name for the file or directory.
            callback (callable, optional): A function to be called when the rename
                is complete. The callback receives two arguments:
                - success (bool): True if rename succeeded, False otherwise.
                - error_msg (str): Error message if rename failed, empty string otherwise.

        Signals:
            rename_finished (str, str, bool, str): Emitted upon completion with parameters:
                - original_path (str): The original path.
                - new_path (str): The new path after renaming.
                - success (bool): True if rename succeeded, False otherwise.
                - error_msg (str): Error message if rename failed, empty string otherwise.
        """

        self.mutex.lock()
        self._tasks.append({
            'type': 'rename',
            'path': path,
            'new_name': new_name,
            'callback': callback
        })
        self.condition.wakeAll()
        self.mutex.unlock()

    def upload_file(self, local_path, remote_path: str, compression: bool, callback=None):
        """
        Uploads a local file to the remote server asynchronously.

        This method queues an upload task to be executed in the background.
        Upon completion, the `upload_finished` signal is emitted.

        Args:
            local_path (str or list): Path to the local file to upload.
            remote_path (str): Target path on the remote server.
            callback (callable, optional): Function to call when upload is complete.
                Receives two arguments:
                - success (bool): True if upload succeeded, False otherwise.
                - error_msg (str): Error message if upload failed, empty string otherwise.

        Signals:
            upload_finished (str, bool, str): Emitted upon completion with parameters:
                - local_path (str): The local file path.
                - success (bool): True if upload succeeded, False otherwise.
                - error_msg (str): Error message if upload failed, empty string otherwise.
        """

        self.mutex.lock()
        self._tasks.append({
            'type': 'upload_file',
            'local_path': local_path,
            'remote_path': remote_path,
            'compression': compression,
            'callback': callback
        })
        self.condition.wakeAll()
        self.mutex.unlock()

    def classify_file_type_using_file(self, path: str) -> str:
        """
        Use remote `file` command to detect a simplified file type and emit the result.

        Returns one of:
        - "image/video"
        - "text"
        - "executable"
        - "unknown"

        Emits: file_type_ready(path, type)
        """
        # safety: ensure conn exists
        if self.conn is None:
            self.file_type_ready.emit(path, "unknown")
            return "unknown"

        # quote path for shell safety
        safe_path = shlex.quote(path)

        try:
            # 1) Try MIME type first (follow symlink with -L)
            cmd_mime = f"file -b --mime-type -L {safe_path}"
            stdin, stdout, stderr = self.conn.exec_command(cmd_mime)
            exit_status = stdout.channel.recv_exit_status()
            mime_out = stdout.read().decode('utf-8', errors='ignore').strip().lower()
            _err = stderr.read().decode('utf-8', errors='ignore').strip()

            if exit_status == 0 and mime_out:
                # image/video by MIME
                if mime_out.startswith("image") or mime_out.startswith("video"):
                    self.file_type_ready.emit(path, "image/video")
                    return "image/video"

                # text-like MIME (text/* or some application types that are textual)
                if (mime_out.startswith("text")
                    or mime_out in {"application/json", "application/xml", "application/javascript"}
                        or mime_out.endswith("+xml") or mime_out.endswith("+json")):
                    self.file_type_ready.emit(path, "text")
                    return "text"

                # common executable-related MIME strings
                if ("executable" in mime_out
                            or "x-executable" in mime_out
                            or mime_out.startswith("application/x-sharedlib")
                            or "x-mach-binary" in mime_out
                            or "pe" in mime_out  # covers various PE-like mimes
                        ):
                    self.file_type_ready.emit(path, "executable")
                    return "executable"

            # 2) Fallback: use human-readable `file -b -L` output
            cmd_hr = f"file -b -L {safe_path}"
            stdin, stdout, stderr = self.conn.exec_command(cmd_hr)
            exit_status2 = stdout.channel.recv_exit_status()
            hr_out = stdout.read().decode('utf-8', errors='ignore').lower()
            _err2 = stderr.read().decode('utf-8', errors='ignore').strip()

            if exit_status2 == 0 and hr_out:
                # executable indicators
                if ("executable" in hr_out
                    or "elf" in hr_out
                    or "pe32" in hr_out
                    or "ms-dos" in hr_out
                        or "mach-o" in hr_out):
                    self.file_type_ready.emit(path, "executable")
                    return "executable"

                # image/video indicators
                if ("png" in hr_out or "jpeg" in hr_out or "jpg" in hr_out
                    or "gif" in hr_out or "bitmap" in hr_out
                    or "svg" in hr_out or "png image" in hr_out
                        or "video" in hr_out or "matroska" in hr_out or "mp4" in hr_out):
                    self.file_type_ready.emit(path, "image/video")
                    return "image/video"

                # text indicators
                if ("text" in hr_out or "ascii" in hr_out or "utf-8" in hr_out
                        or "script" in hr_out or "json" in hr_out or "xml" in hr_out):
                    self.file_type_ready.emit(path, "text")
                    return "text"

            # 3) 最后兜底：检查执行权限（远端 stat via sftp）
            try:
                attr = self.sftp.lstat(path)
                if bool(attr.st_mode & stat.S_IXUSR):
                    self.file_type_ready.emit(path, "executable")
                    return "executable"
            except Exception:
                # ignore stat errors here
                pass

            # default
            self.file_type_ready.emit(path, "unknown")
            return "unknown"

        except Exception as e:
            print(f"Failed to run remote file command for {path}: {e}")
            self.file_type_ready.emit(path, "unknown")
            return "unknown"

    def _handle_mkdir_task(self, path: str, callback=None):
        """
        Asynchronously create a remote directory (mkdir -p behavior) via SFTP.

        Emits:
            mkdir_finished(path, status, error_msg)
        """
        if self.sftp is None:
            error_msg = "SFTP connection not ready"
            print(f"❌ Mkdir failed - {error_msg}: {path}")
            self.mkdir_finished.emit(path, False, error_msg)
            if callback:
                callback(False, error_msg)
            return

        try:
            # Recursively create directories like 'mkdir -p'
            parts = path.strip("/").split("/")
            current_path = ""
            for part in parts:
                current_path += f"/{part}"
                try:
                    self.sftp.stat(current_path)
                except FileNotFoundError:
                    try:
                        self.sftp.mkdir(current_path)
                        print(f"✅ Created directory: {current_path}")
                    except Exception as mkdir_exc:
                        error_msg = f"Failed to create directory {current_path}: {mkdir_exc}"
                        print(f"❌ Mkdir failed - {error_msg}")
                        self.mkdir_finished.emit(path, False, error_msg)
                        if callback:
                            callback(False, error_msg)
                        return

            # Success
            self.mkdir_finished.emit(path, True, "")
            if callback:
                callback(True, "")

        except Exception as e:
            error_msg = f"Error during mkdir: {str(e)}"
            print(f"❌ Mkdir failed - {error_msg}")
            import traceback
            traceback.print_exc()
            self.mkdir_finished.emit(path, False, error_msg)
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

    def _get_file_info(self, path: str):
        """
        获取文件/目录信息，跨平台兼容
        """
        if self.sftp is None:
            return None, "", False, "SFTP 未就绪"

        try:
            attr = self.sftp.lstat(path)

            # 权限 rwxr-xr-x 格式
            perm = stat.filemode(attr.st_mode)

            # 用户和组（跨平台）
            owner, group = self._get_owner_group(attr.st_uid, attr.st_gid)

            # 是否可执行
            is_executable = bool(attr.st_mode & stat.S_IXUSR)

            # 最后修改时间
            mtime = datetime.fromtimestamp(
                attr.st_mtime).strftime("%Y-%m-%d %H:%M:%S")

            # 是否符号链接
            is_symlink = stat.S_ISLNK(attr.st_mode)
            symlink_target = None
            if is_symlink:
                try:
                    symlink_target = self.sftp.readlink(path)
                except Exception:
                    symlink_target = "<unresolved>"

            info = {
                "path": path,
                "filename": os.path.basename(path.rstrip('/')),
                "size": self._human_readable_size(attr.st_size),
                "owner": owner,
                "group": group,
                "permissions": perm,
                "is_executable": is_executable,
                "last_modified": mtime,
                "is_directory": stat.S_ISDIR(attr.st_mode),
                "is_symlink": is_symlink,
                "symlink_target": symlink_target
            }

            return path, info, True, ""

        except Exception as e:
            return path, {}, False, f"获取文件信息失败: {e}"

    def _handle_rename_task(self, path: str, new_name: str, callback=None):
        """
        处理重命名任务（内部实现）
        """
        if self.sftp is None:
            error_msg = "SFTP 连接未就绪"
            print(f"❌ 重命名失败 - {error_msg}: {path} -> {new_name}")
            self.rename_finished.emit(path, new_name, False, error_msg)
            if callback:
                callback(False, error_msg)
            return

        try:
            # 检查源路径是否存在
            try:
                self.sftp.stat(path)
            except IOError:
                error_msg = f"源路径不存在: {path}"
                print(f"❌ 重命名失败 - {error_msg}")
                self.rename_finished.emit(path, new_name, False, error_msg)
                if callback:
                    callback(False, error_msg)
                return

            # 构建新路径
            parent_dir = os.path.dirname(path.rstrip('/'))
            new_path = f"{parent_dir}/{new_name}" if parent_dir != '/' else f"/{new_name}"

            print(f"🔁 开始重命名: {path} -> {new_path}")

            # 执行重命名
            self.sftp.rename(path, new_path)

            print(f"✅ 重命名成功: {path} -> {new_path}")
            self.rename_finished.emit(path, new_path, True, "")

            # 刷新父目录
            if parent_dir:
                print(f"🔄 刷新父目录: {parent_dir}")
                self.refresh_paths([parent_dir])

            if callback:
                callback(True, "")

        except Exception as e:
            error_msg = f"重命名过程错误: {str(e)}"
            print(f"❌ 重命名失败 - {error_msg}")
            import traceback
            traceback.print_exc()
            self.rename_finished.emit(path, new_name, False, error_msg)
            if callback:
                callback(False, error_msg)

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
    def _remote_untar(self, remote_tar_path: str, target_dir: str, remove_tar: bool = True):
        """
        在远程服务器解压 tar.gz 文件

        :param remote_tar_path: 远程 tar.gz 文件完整路径
        :param target_dir: 解压到目标目录
        :param remove_tar: 是否解压后删除远程 tar.gz 文件
        """
        try:
            self.start_to_uncompression.emit(remote_tar_path)
            # 确保目标目录存在
            mkdir_cmd = f'mkdir -p "{target_dir}"'
            self._exec_remote_command(mkdir_cmd)

            # 解压 tar.gz
            untar_cmd = f'tar -xzf "{remote_tar_path}" -C "{target_dir}"'
            out, err = self._exec_remote_command(untar_cmd)

            if err:
                print(f"⚠️ Remote untar error: {err}")
            else:
                print(
                    f"✅ Remote untar completed: {remote_tar_path} -> {target_dir}")

            # 删除远程 tar.gz
            if remove_tar:
                rm_cmd = f'rm -f "{remote_tar_path}"'
                self._exec_remote_command(rm_cmd)
                print(f"🗑️ Remote tar.gz removed: {remote_tar_path}")

        except Exception as e:
            print(f"❌ Remote untar failed: {e}")
            import traceback
            traceback.print_exc()

    def _exec_remote_command(self, command: str):
        """
        在远程服务器执行命令
        :param command: shell 命令字符串
        :return: (stdout, stderr)
        """
        if not hasattr(self, "conn") or self.conn is None:
            print("SSH connection is not established")

        stdin, stdout, stderr = self.conn.exec_command(command)
        out = stdout.read().decode(errors="ignore")
        err = stderr.read().decode(errors="ignore")
        return out, err

    def _human_readable_size(self, size_bytes: int) -> str:
        """将字节数转换为可读的格式"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        for unit in ["KB", "MB", "GB", "TB"]:
            size_bytes /= 1024.0
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
        return f"{size_bytes:.2f} PB"

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

    def _fetch_user_group_maps(self):
        """
        Fetch and parse /etc/passwd and /etc/group to cache UID/GID mappings.
        """
        if self.conn is None:
            return

        # Fetch /etc/passwd
        try:
            stdin, stdout, stderr = self.conn.exec_command("cat /etc/passwd")
            passwd_content = stdout.read().decode('utf-8', errors='ignore')
            for line in passwd_content.strip().split('\n'):
                parts = line.split(':')
                if len(parts) >= 3:
                    username, _, uid = parts[0], parts[1], parts[2]
                    self.uid_map[int(uid)] = username
        except Exception as e:
            print(f"Could not fetch or parse /etc/passwd: {e}")

        # Fetch /etc/group
        try:
            stdin, stdout, stderr = self.conn.exec_command("cat /etc/group")
            group_content = stdout.read().decode('utf-8', errors='ignore')
            for line in group_content.strip().split('\n'):
                parts = line.split(':')
                if len(parts) >= 3:
                    groupname, _, gid = parts[0], parts[1], parts[2]
                    self.gid_map[int(gid)] = groupname
        except Exception as e:
            print(f"Could not fetch or parse /etc/group: {e}")

    def _get_owner_group(self, uid, gid):
        owner = self.uid_map.get(uid, str(uid))
        group = self.gid_map.get(gid, str(gid))
        return owner, group

    def list_dir_detailed(self, path: str) -> Optional[List[dict]]:
        if self.sftp is None:
            print("list_dir_detailed: sftp not ready")
            return None
        detailed_result = []
        try:
            for attr in self.sftp.listdir_attr(path):
                owner, group = self._get_owner_group(attr.st_uid, attr.st_gid)
                is_dir = stat.S_ISDIR(attr.st_mode)
                if stat.S_ISLNK(attr.st_mode):
                    try:
                        full_path = f"{path.rstrip('/')}/{attr.filename}"
                        target_attr = self.sftp.stat(full_path)
                        if stat.S_ISDIR(target_attr.st_mode):
                            is_dir = True
                    except Exception as e:
                        print(
                            f"Could not stat symlink target for {attr.filename}: {e}")

                detailed_result.append({
                    "name": attr.filename,
                    "is_dir": is_dir,
                    "size": attr.st_size,
                    "mtime": datetime.fromtimestamp(attr.st_mtime).strftime('%Y/%m/%d %H:%M'),
                    "perms": stat.filemode(attr.st_mode),
                    "owner": f"{owner}/{group}"
                })
            return detailed_result
        except Exception as e:
            print(
                f"list_dir_detailed error when getting directory contents: {e}")
            return None

    # ---------------------------
    # 删除功能实现
    # ---------------------------

    def _handle_delete_task(self, paths, callback=None):
        """
        Handles the deletion task for one or more remote paths.
        """
        if self.conn is None:
            error_msg = "SSH connection is not ready"
            print(f"❌ Deletion failed - {error_msg}: {paths}")
            self.delete_finished.emit(str(paths), False, error_msg)
            if callback:
                callback(False, error_msg)
            return

        if isinstance(paths, str):
            paths = [paths]

        all_successful = True
        errors = []
        parent_dirs_to_refresh = set()

        for path in paths:
            try:
                print(f"🗑️ Starting deletion of: {path}")

                path_type = self.check_path_type(path)
                if not path_type:
                    error_msg = f"Path does not exist: {path}"
                    print(f"❌ Deletion failed - {error_msg}")
                    errors.append(error_msg)
                    all_successful = False
                    continue

                print(f"📁 Path type: {path_type}")
                cmd = f'rm -rf "{path}"'
                print(f"🔧 Executing command: {cmd}")

                stdin, stdout, stderr = self.conn.exec_command(cmd)
                exit_status = stdout.channel.recv_exit_status()
                error_output = stderr.read().decode('utf-8').strip()

                if exit_status == 0:
                    print(f"✅ Deletion successful: {path}")
                    parent_dir = os.path.dirname(path)
                    if parent_dir:
                        parent_dirs_to_refresh.add(parent_dir)
                else:
                    error_msg = f"Deletion command failed for {path}: {error_output}" if error_output else "Unknown error"
                    print(f"❌ Deletion failed - {error_msg}")
                    errors.append(error_msg)
                    all_successful = False

            except Exception as e:
                error_msg = f"Error during deletion of {path}: {str(e)}"
                print(f"❌ Deletion failed - {error_msg}")
                traceback.print_exc()
                errors.append(error_msg)
                all_successful = False

        final_error_message = "; ".join(errors)
        display_path = "Multiple files" if len(paths) > 1 else paths[0]
        self.delete_finished.emit(
            display_path, all_successful, final_error_message)

        if parent_dirs_to_refresh:
            print(f"🔄 Refreshing parent directories: {parent_dirs_to_refresh}")
            self.refresh_paths(list(parent_dirs_to_refresh))

        if callback:
            callback(all_successful, final_error_message)

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
