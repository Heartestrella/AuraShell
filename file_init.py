import sys
import os
import platform
import subprocess
import tempfile
import hashlib

def is_pyinstaller_bundle():
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

def has_non_ascii(s):
    try:
        s.encode('ascii')
    except UnicodeEncodeError:
        return True
    else:
        return False

script_path = sys.argv[0]
if has_non_ascii(script_path):
    if not is_pyinstaller_bundle():
        print("警告:脚本路径包含非 ASCII 字符.请移动项目至不包含非 ASCII 字符或纯英文的路径.")
        print(f"路径:{script_path}")
        sys.exit(1)
    else:
        current_dir = os.path.dirname(sys.executable)
        link_name = f"AuraShell"
        temp_dir = tempfile.gettempdir()
        if platform.system() == "Windows":
            ascii_path = os.path.join(temp_dir, link_name)
            if os.path.lexists(ascii_path):
                os.unlink(ascii_path)
            command = f'mklink /J "{ascii_path}" "{current_dir}"'
            subprocess.run( command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=0x08000000, shell=True )
        else:
            ascii_path = os.path.join(temp_dir,link_name)
            if os.path.lexists(ascii_path):
                os.unlink(ascii_path)
            os.symlink(current_dir, ascii_path, target_is_directory=True)
        executable_name = os.path.basename(sys.executable)
        new_executable_path = os.path.join(ascii_path, executable_name)
        if not os.path.exists(new_executable_path):
            raise FileNotFoundError(f"Failed to create a valid link. The new path does not exist: {new_executable_path}")
        args = [new_executable_path] + sys.argv[1:]
        subprocess.Popen(args)
        sys.exit(0)