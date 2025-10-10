import sys
import os
import time
import subprocess
import shutil
import psutil

def main():
    if len(sys.argv) != 4:
        print("Usage: updater.py <pid> <source_path> <target_path>")
        return

    pid = int(sys.argv[1])
    source_path = sys.argv[2]
    target_path = sys.argv[3]
    
    app_dir = os.path.dirname(target_path)
    lock_file = os.path.join(app_dir, 'update.lock')

    try:
        with open(lock_file, 'w') as f:
            f.write(str(os.getpid()))

        while psutil.pid_exists(pid):
            time.sleep(0.5)

        backup_path = f"{target_path}.bak"
        if os.path.exists(backup_path):
            if os.path.isdir(backup_path):
                shutil.rmtree(backup_path)
            else:
                os.remove(backup_path)
        
        os.rename(target_path, backup_path)

        if os.path.isdir(source_path):
            shutil.copytree(source_path, target_path)
        else:
            shutil.copy(source_path, target_path)

        executable = target_path
        if os.path.isdir(target_path):
             executable = os.path.join(target_path, 'AuraShell.exe')

        subprocess.Popen([executable])

    except Exception as e:
        print(f"Update failed: {e}")
        # Attempt to rollback
        if os.path.exists(backup_path):
            try:
                if os.path.exists(target_path):
                    if os.path.isdir(target_path):
                        shutil.rmtree(target_path)
                    else:
                        os.remove(target_path)
                os.rename(backup_path, target_path)
            except Exception as rollback_e:
                print(f"Rollback failed: {rollback_e}")
    finally:
        if os.path.exists(lock_file):
            os.remove(lock_file)

if __name__ == "__main__":
    main()