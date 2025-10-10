import sys
import os
import time
import subprocess
import shutil
import psutil

def main():
    if len(sys.argv) != 4:
        sys.stderr.write("Usage: updater.py <pid> <source_path> <target_path>\n")
        return
    pid = int(sys.argv[1])
    source_path = sys.argv[2]
    target_path = sys.argv[3]
    if os.path.isdir(target_path):
        app_dir = target_path
    else:
        app_dir = os.path.dirname(target_path)
    lock_file = os.path.join(app_dir, 'update.lock')
    try:
        with open(lock_file, 'w') as f:
            f.write(str(os.getpid()))
        while psutil.pid_exists(pid):
            time.sleep(1)
        if os.path.isdir(source_path):
            shutil.copytree(source_path, target_path, dirs_exist_ok=True)
        else:
            shutil.copy2(source_path, target_path)
        executable = target_path
        if os.path.isdir(target_path):
            executable = os.path.join(target_path, os.path.basename(sys.executable))
        subprocess.Popen([executable])
    except Exception as e:
        file = 'update.log'
        with open(file, 'a') as f:
            f.write(f"Failed to update: {e}\n")
    finally:
        if os.path.exists(lock_file):
            os.remove(lock_file)

if __name__ == "__main__":
    main()