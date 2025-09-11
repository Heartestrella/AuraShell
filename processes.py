import psutil
import time
import json


def get_usage_info(top_n=5):
    usage = {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "mem_percent": psutil.virtual_memory().percent,
        "top_processes": []
    }

    processes = []
    for p in psutil.process_iter(['name', 'cpu_percent', 'memory_percent']):
        try:
            name = p.info['name'] or "unknown"
            if name.lower().startswith("kworker"):
                continue
            processes.append({
                "cpu": p.info['cpu_percent'],
                "mem": p.info['memory_percent'],
                "name": name
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    processes = sorted(processes, key=lambda x: x['cpu'], reverse=True)[:top_n]
    usage["top_processes"] = processes

    return usage


if __name__ == "__main__":
    while True:
        info = get_usage_info(top_n=5)
        print("///Start" + json.dumps(info) + "End///")
        time.sleep(3)
