# transfer_worker.py
import traceback
import paramiko
import os
import stat
import tarfile
import tempfile
from PyQt5.QtCore import QObject, QRunnable, pyqtSignal


class TransferSignals(QObject):
    """
    Defines signals available for a transfer worker.
    """
    progress = pyqtSignal(str, int)  # local_path_or_identifier, percentage
    # local_path_or_identifier, success, message
    finished = pyqtSignal(str, bool, str)
    # target_zip_path (for compression)
    start_to_compression = pyqtSignal(str)
    # remote_path (for uncompression)
    start_to_uncompression = pyqtSignal(str)


class TransferWorker(QRunnable):
    """
    A QRunnable worker for performing a single file/directory transfer operation (upload or download)
    in a separate thread from the QThreadPool.
    """

    def __init__(self, session_info, action, local_path, remote_path, compression, download_context=None, upload_context=None):
        super().__init__()
        self.session_info = session_info
        self.action = action  # 'upload' or 'download'
        self.local_path = local_path
        self.remote_path = remote_path
        self.compression = compression
        self.download_context = download_context
        self.upload_context = upload_context
        self.signals = TransferSignals()

        # SSH/SFTP clients will be created in the run() method to ensure they are thread-local
        self.conn = None
        self.sftp = None

    def run(self):
        """The main work of the thread. Establishes a new SSH connection and performs the transfer."""
        try:
            self.conn = paramiko.SSHClient()
            self.conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            if self.session_info.auth_type == "password":
                self.conn.connect(
                    self.session_info.host,
                    port=self.session_info.port,
                    username=self.session_info.username,
                    password=self.session_info.password,
                    timeout=30,
                    banner_timeout=30
                )
            else:
                self.conn.connect(
                    self.session_info.host,
                    port=self.session_info.port,
                    username=self.session_info.username,
                    key_filename=self.session_info.key_path,
                    timeout=30,
                    banner_timeout=30
                )
            self.sftp = self.conn.open_sftp()

            if self.action == 'upload':
                # The identifier for signals will be the original local_path (str or list)
                identifier = str(self.local_path)
                self._handle_upload_task(
                    identifier, self.local_path, self.remote_path, self.compression, self.upload_context)
            elif self.action == 'download':
                # The identifier for signals will be the original remote_path (str or list)
                identifier = str(self.remote_path)
                self._download_files(
                    identifier, self.remote_path, self.compression)

        except Exception as e:
            tb = traceback.format_exc()
            error_msg = f"TransferWorker Error: {e}\n{tb}"
            print(f"❌ {error_msg}")
            identifier = str(self.local_path if self.action ==
                             'upload' else self.remote_path)
            self.signals.finished.emit(identifier, False, error_msg)
        finally:
            if self.sftp:
                self.sftp.close()
            if self.conn:
                self.conn.close()

    # ==================================================================================
    # == The following methods are adapted from RemoteFileManager for standalone execution ==
    # ==================================================================================

    def _handle_upload_task(self, identifier, local_path, remote_path, compression, upload_context=None):
        try:
            if isinstance(local_path, list):
                if compression:
                    # For compressed lists, the whole list is one task.
                    self._upload_list_compressed(
                        identifier, local_path, remote_path)
                else:
                    # For uncompressed lists, each item is a sub-task.
                    all_successful = True
                    error_messages = []
                    for path in local_path:
                        # Each item will emit its own finished signal.
                        # We capture the result here to give a final status for the whole batch.
                        success, message = self._upload_item(
                            path, path, remote_path, compression=False, upload_context=upload_context)
                        if not success:
                            all_successful = False
                            error_messages.append(message)
                    # Optionally, emit a final signal for the whole batch if needed,
                    # but individual signals are now sent. For now, we rely on individual signals.

            elif isinstance(local_path, str):
                self._upload_item(identifier, local_path,
                                  remote_path, compression, upload_context)

        except Exception as e:
            tb = traceback.format_exc()
            error_msg = f"Error during upload task: {e}\n{tb}"
            print(f"❌ {error_msg}")
            self.signals.finished.emit(identifier, False, error_msg)

    def _upload_item(self, identifier, item_path, remote_path, compression, upload_context=None):
        """Returns (bool, str) for success status and message, and also emits signals."""
        if not os.path.exists(item_path):
            error_msg = f"Local path does not exist: {item_path}"
            self.signals.finished.emit(item_path, False, error_msg)
            return False, error_msg

        try:
            if compression:
                self._upload_compressed(item_path, item_path, remote_path)
            else:
                if os.path.isfile(item_path):
                    self._upload_file(
                        item_path, item_path, remote_path, upload_context)
                elif os.path.isdir(item_path):
                    # This should no longer be called for non-compressed directory uploads
                    # as the dispatcher breaks them down into files.
                    self._upload_directory(item_path, item_path, remote_path)

            return True, ""
        except Exception as e:
            error_msg = f"Failed to upload {item_path}: {e}"
            self.signals.finished.emit(item_path, False, error_msg)
            return False, error_msg

    def _upload_list_compressed(self, identifier, path_list, remote_path):

        tmp_fd, tmp_tar_path = tempfile.mkstemp(suffix=".tar.gz")
        os.close(tmp_fd)
        self.signals.start_to_compression.emit(tmp_tar_path)
        try:
            with tarfile.open(tmp_tar_path, mode="w:gz") as tf:
                for path in path_list:
                    if not os.path.exists(path):
                        continue
                    arcname = os.path.basename(path)
                    tf.add(path, arcname=arcname)
            self._upload_file(identifier, tmp_tar_path, remote_path)
            remote_zip_path = f"{remote_path.rstrip('/')}/{os.path.basename(tmp_tar_path)}"
            self._remote_untar(remote_zip_path, remote_path)

        except Exception as e:
            raise e
        finally:
            if os.path.exists(tmp_tar_path):
                os.remove(tmp_tar_path)

    def _upload_compressed(self, identifier, local_path, remote_path):
        tmp_fd, tmp_tar_path = tempfile.mkstemp(suffix=".tar.gz")
        os.close(tmp_fd)
        self.signals.start_to_compression.emit(tmp_tar_path)
        try:
            with tarfile.open(tmp_tar_path, mode="w:gz") as tf:
                arcname = os.path.basename(local_path)
                tf.add(local_path, arcname=arcname)

            self._upload_file(identifier, tmp_tar_path, remote_path)
            remote_zip_path = f"{remote_path.rstrip('/')}/{os.path.basename(tmp_tar_path)}"
            self._remote_untar(remote_zip_path, remote_path)
        except Exception as e:
            raise e
        finally:
            if os.path.exists(tmp_tar_path):
                os.remove(tmp_tar_path)

    def _upload_file(self, identifier, local_path, remote_path, upload_context=None):
        try:
            if upload_context:
                # Reconstruct the target path to preserve directory structure
                relative_path = os.path.relpath(local_path, upload_context)
                # The root of the uploaded dir should also be created
                upload_root_name = os.path.basename(upload_context)
                full_remote_path = os.path.join(
                    remote_path, upload_root_name, relative_path).replace('\\', '/')
            else:
                # Original behavior for single file uploads
                remote_filename = os.path.basename(local_path)
                full_remote_path = os.path.join(
                    remote_path, remote_filename).replace('\\', '/')
            
            # Ensure the parent directory of the target file exists
            self._ensure_remote_directory_exists(os.path.dirname(full_remote_path))

            def progress_callback(bytes_so_far, total_bytes):
                if total_bytes > 0:
                    progress = int((bytes_so_far / total_bytes) * 100)
                    self.signals.progress.emit(identifier, progress)

            self.sftp.put(local_path, full_remote_path,
                          callback=progress_callback)
            self.signals.finished.emit(identifier, True, "")

        except Exception as e:
            tb = traceback.format_exc()
            error_msg = f"File upload error: {e}\n{tb}"
            self.signals.finished.emit(identifier, False, error_msg)

    def _upload_directory(self, identifier, local_dir, remote_dir):
        try:
            dir_name = os.path.basename(local_dir)
            target_remote_dir = os.path.join(
                remote_dir, dir_name).replace('\\', '/')
            self._ensure_remote_directory_exists(target_remote_dir)

            total_size = sum(os.path.getsize(os.path.join(root, file))
                             for root, _, files in os.walk(local_dir) for file in files)
            uploaded_size = 0

            for root, dirs, files in os.walk(local_dir):
                relative_path = os.path.relpath(root, local_dir)
                current_remote_dir = os.path.join(target_remote_dir, relative_path).replace(
                    '\\', '/') if relative_path != '.' else target_remote_dir

                self._ensure_remote_directory_exists(current_remote_dir)

                for file in files:
                    local_file_path = os.path.join(root, file)
                    remote_file_path = os.path.join(
                        current_remote_dir, file).replace('\\', '/')

                    file_size = os.path.getsize(local_file_path)
                    self.sftp.put(local_file_path, remote_file_path)
                    uploaded_size += file_size
                    progress = int((uploaded_size / total_size)
                                   * 100) if total_size > 0 else 100
                    self.signals.progress.emit(identifier, progress)

            self.signals.finished.emit(
                identifier, True, "Directory upload completed.")
        except Exception as e:
            tb = traceback.format_exc()
            error_msg = f"Directory upload error: {e}\n{tb}"
            self.signals.finished.emit(identifier, False, error_msg)

    def _download_files(self, identifier, remote_path, compression):
        local_base = "_ssh_download"
        os.makedirs(local_base, exist_ok=True)
        paths = [remote_path] if isinstance(remote_path, str) else remote_path

        try:
            if compression:
                # Simplified compression logic for now
                remote_tar = self._remote_tar(paths)
                if not remote_tar:
                    raise Exception("Failed to create remote tar file.")

                local_tar_path = os.path.join(
                    local_base, os.path.basename(remote_tar))

                def progress_callback(bytes_so_far, total_bytes):
                    if total_bytes > 0:
                        progress = int((bytes_so_far / total_bytes) * 100)
                        # We can perhaps divide progress for different stages
                        # Assuming download is the main part
                        self.signals.progress.emit(identifier, progress)

                self.sftp.get(remote_tar, local_tar_path,
                              callback=progress_callback)

                with tarfile.open(local_tar_path, "r:gz") as tar:
                    tar.extractall(local_base)

                self._exec_remote_command(f'rm -f "{remote_tar}"')
                os.remove(local_tar_path)

                self.signals.finished.emit(identifier, True, local_base)

            else:  # Non-compressed
                # For non-compressed, _download_item will handle its own signals.
                for p in paths:
                    # Each item is its own task, so the identifier is the path itself.
                    self._download_item(p, p, local_base)
                # A batch 'finished' signal is not sent here, to allow individual tracking.

        except Exception as e:
            tb = traceback.format_exc()
            error_msg = f"Error during download task: {e}\n{tb}"
            print(f"❌ {error_msg}")
            self.signals.finished.emit(identifier, False, error_msg)

    def _download_item(self, identifier, remote_item_path, local_base_path):
        """Downloads a single item (file or directory) and emits a finished signal for it."""
        try:
            # Determine local path, preserving directory structure if context is given
            if self.download_context:
                if remote_item_path.startswith(self.download_context):
                    # The download root itself should be included in the local path
                    download_root_name = os.path.basename(
                        self.download_context.rstrip('/'))
                    relative_path = os.path.relpath(
                        remote_item_path, self.download_context)
                    local_target = os.path.join(
                        local_base_path, download_root_name, relative_path)
                else:  # Fallback for safety
                    local_target = os.path.join(
                        local_base_path, os.path.basename(remote_item_path.rstrip("/")))
            else:
                local_target = os.path.join(
                    local_base_path, os.path.basename(remote_item_path.rstrip("/")))

            # Ensure local directory exists
            os.makedirs(os.path.dirname(local_target), exist_ok=True)

            # Since dispatcher now only sends files for non-compressed, we can simplify this.
            # We still check to be robust.
            attr = self.sftp.stat(remote_item_path)
            if stat.S_ISDIR(attr.st_mode):
                # This part should ideally not be hit in the new flow for non-compressed downloads
                self._download_directory(
                    identifier, remote_item_path, local_target)
            else:
                self._download_file(
                    identifier, remote_item_path, local_target)

            self.signals.finished.emit(identifier, True, local_target)
        except Exception as e:
            tb = traceback.format_exc()
            error_msg = f"Failed to download {remote_item_path}: {e}\n{tb}"
            self.signals.finished.emit(identifier, False, error_msg)

    def _download_file(self, identifier, remote_file, local_file):
        def progress_callback(bytes_so_far, total_bytes):
            if total_bytes > 0:
                progress = int((bytes_so_far / total_bytes) * 100)
                self.signals.progress.emit(identifier, progress)

        self.sftp.get(remote_file, local_file, callback=progress_callback)

    def _download_directory(self, identifier, remote_dir, local_dir):
        os.makedirs(local_dir, exist_ok=True)
        # This simplified version won't have accurate progress for directory downloads
        # A more complex implementation would be needed to calculate total size first.
        for entry in self.sftp.listdir_attr(remote_dir):
            remote_item = f"{remote_dir.rstrip('/')}/{entry.filename}"
            local_item = os.path.join(local_dir, entry.filename)
            if stat.S_ISDIR(entry.st_mode):
                self._download_directory(identifier, remote_item, local_item)
            else:
                # No progress for individual files in a dir download for now
                self.sftp.get(remote_item, local_item)

    def _remote_tar(self, paths):
        if not paths:
            return None

        common_path = os.path.dirname(paths[0]).replace('\\', '/')
        tar_name = f"archive_{os.path.basename(paths[0])}.tar.gz"
        remote_tar_path = f"{common_path}/{tar_name}"

        files_to_tar = ' '.join([f'"{os.path.basename(p)}"' for p in paths])

        cmd = f'cd "{common_path}" && tar -czf "{tar_name}" {files_to_tar}'
        out, err = self._exec_remote_command(cmd)
        if err:
            print(f"Error creating remote tar: {err}")
            return None
        return remote_tar_path

    def _ensure_remote_directory_exists(self, remote_dir):
        parts = remote_dir.strip('/').split('/')
        current_path = ''
        for part in parts:
            current_path = f"{current_path}/{part}" if current_path else f"/{part}"
            try:
                self.sftp.stat(current_path)
            except FileNotFoundError:
                self.sftp.mkdir(current_path)

    def _remote_untar(self, remote_tar_path, target_dir):
        self.signals.start_to_uncompression.emit(remote_tar_path)
        self._ensure_remote_directory_exists(target_dir)
        untar_cmd = f'tar -xzf "{remote_tar_path}" -C "{target_dir}"'
        self._exec_remote_command(untar_cmd)
        rm_cmd = f'rm -f "{remote_tar_path}"'
        self._exec_remote_command(rm_cmd)

    def _exec_remote_command(self, command):
        stdin, stdout, stderr = self.conn.exec_command(command)
        out = stdout.read().decode(errors="ignore")
        err = stderr.read().decode(errors="ignore")
        return out, err
