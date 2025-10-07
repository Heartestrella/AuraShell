#!/bin/bash
TOP_N=4
INTERVAL=2

# --- 自动检测包管理器并安装依赖 ---
install_pkg() {
    if command -v apt-get >/dev/null 2>&1; then
        apt-get update -y
        apt-get install -y "$@"
    elif command -v dnf >/dev/null 2>&1; then
        dnf install -y "$@"
    elif command -v yum >/dev/null 2>&1; then
        yum install -y "$@"
    elif command -v pacman >/dev/null 2>&1; then
        pacman -Sy --noconfirm "$@"
    elif command -v zypper >/dev/null 2>&1; then
        zypper install -y "$@"
    else
        echo "❌ 未找到支持的包管理器，请手动安装: $*" >&2
    fi
}

check_and_install() {
    for cmd in "$@"; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            case $cmd in
                ss) install_pkg iproute2 iproute iproute-ss ;;
                iostat) install_pkg sysstat ;;
                lsblk) install_pkg util-linux ;;
                *) install_pkg "$cmd" ;;
            esac
        fi
    done
}

# 检查并安装必要命令
check_and_install ss lsblk iostat

# ================== 系统信息收集 ==================
print_system_info() {
    sys_name=$(uname -s)                        # 系统名
    kernel=$(uname -r)                          # 内核版本
    arch=$(uname -m)                            # 硬件架构
    hostname=$(hostname)                        # 主机名
    cpu_model=$(awk -F: '/model name/ {print $2; exit}' /proc/cpuinfo | sed 's/^ //')
    cpu_cores=$(nproc)                          # 核心数
    cpu_freq=$(awk -F: '/cpu MHz/ {printf "%.0f",$2; exit}' /proc/cpuinfo)MHz
    cpu_cache=$(awk -F: '/cache size/ {print $2; exit}' /proc/cpuinfo | sed 's/^ //')
    mem_total=$(awk '/MemTotal/ {printf "%.0f",$2/1024}' /proc/meminfo)MB
    ip_addr=$(hostname -I 2>/dev/null | awk '{print $1}')   # 取第一个 IPv4

    printf '///SysInfo{"system":"%s","kernel":"%s","arch":"%s","hostname":"%s","cpu_model":"%s","cpu_cores":%s,"cpu_freq":"%s","cpu_cache":"%s","mem_total":"%s","ip":"%s"}End///\n' \
        "$sys_name" "$kernel" "$arch" "$hostname" "$cpu_model" "$cpu_cores" "$cpu_freq" "$cpu_cache" "$mem_total" "$ip_addr"
}

# --- 首次输出系统信息 ---
print_system_info

# 初始化网卡数据
declare -A rx_old tx_old

# 初始化进程流量数据
declare -A proc_tx_old proc_rx_old

# 初始化磁盘读写
declare -A disk_read_old disk_write_old

# 改进的 JSON 转义函数
escape_json() {
    local str="$1"
    # 使用参数替换进行转义，避免 awk 正则警告
    str="${str//\\/\\\\}"    # 转义反斜杠
    str="${str//\"/\\\"}"    # 转义双引号
    str="${str//$'\t'/\\t}"  # 转义制表符
    str="${str//$'\r'/\\r}"  # 转义回车符
    str="${str//$'\n'/\\n}"  # 转义换行符
    # 移除控制字符
    str=$(echo "$str" | tr -d '\000-\037')
    echo "$str"
}

while true; do
    # --- CPU 使用率 ---
    cpu_percent=$(LC_ALL=C top -bn2 -d0.2 | grep "Cpu(s)" | tail -n1 | awk '{print 100 - $8}')

    # --- 内存使用率 ---
    mem_percent=$(free | awk '/Mem/ {printf("%.1f", $3/$2 * 100)}')

    # --- 前 N 个进程 ---
    processes=$(ps -eo pid,comm,%cpu,%mem --sort=-%cpu | awk -v top_n="$TOP_N" 'NR>1 && $2 !~ /^kworker/ && $2 !~ /^rcu_/ {count++; if (count <= top_n) {printf "{\"pid\":%s,\"name\":\"%s\",\"cpu\":%s,\"mem\":%s},",$1,$2,$3,$4}}' | sed 's/,$//')
    processes="[$processes]"

    # --- 全部进程 --- (使用改进的方法)
    all_processes="["
    while IFS= read -r line; do
        [[ -z "$line" ]] && continue
        
        user=$(echo "$line" | awk '{print $1}')
        pid=$(echo "$line" | awk '{print $2}')
        name=$(echo "$line" | awk '{print $3}')
        cpu=$(echo "$line" | awk '{print $4}')
        mem=$(echo "$line" | awk '{print $5}')
        
        # 获取完整命令（从第6列开始）
        cmd=$(echo "$line" | awk '{$1=$2=$3=$4=$5=""; print $0}' | sed 's/^ *//')
        
        # 转义 JSON 特殊字符
        cmd_escaped=$(escape_json "$cmd")
        name_escaped=$(escape_json "$name")
        user_escaped=$(escape_json "$user")
        
        all_processes+="{\"user\":\"$user_escaped\",\"pid\":$pid,\"name\":\"$name_escaped\",\"cpu\":$cpu,\"mem\":$mem,\"command\":\"$cmd_escaped\"},"
    done < <(ps -eo user,pid,comm,%cpu,%mem,cmd --no-headers | head -50)  # 限制进程数量避免过大
    
    all_processes=$(echo "$all_processes" | sed 's/,$//')"]"

    # --- 磁盘使用情况 + 读写速率 ---
    disks="["
    while read -r filesystem size used avail usep mount; do
        [[ "$filesystem" == "tmpfs" || "$filesystem" == "udev" ]] && continue

        dev=$(basename "$filesystem")

        read_sectors=$(awk -v d="$dev" '$3==d {print $6}' /proc/diskstats 2>/dev/null)
        write_sectors=$(awk -v d="$dev" '$3==d {print $10}' /proc/diskstats 2>/dev/null)

        [[ -z "$read_sectors" ]] && read_sectors=0
        [[ -z "$write_sectors" ]] && write_sectors=0

        if [[ -n ${disk_read_old[$dev]} ]]; then
            read_kbps=$(( (read_sectors - disk_read_old[$dev]) * 512 / 1024 / INTERVAL ))
            write_kbps=$(( (write_sectors - disk_write_old[$dev]) * 512 / 1024 / INTERVAL ))
        else
            read_kbps=0
            write_kbps=0
        fi

        disk_read_old[$dev]=$read_sectors
        disk_write_old[$dev]=$write_sectors

        disks+="{\"device\":\"$filesystem\",\"mount\":\"$mount\",\"size_kb\":$size,\"used_kb\":$used,\"avail_kb\":$avail,\"used_percent\":\"$usep\",\"read_kbps\":$read_kbps,\"write_kbps\":$write_kbps},"
    done < <(df -k --output=source,size,used,avail,pcent,target | tail -n +2 | head -10)  # 限制磁盘数量

    disks=$(echo "$disks" | sed 's/,$//')"]"

    # --- 网卡流量（KB/s） ---
    net_devs="["
    while read iface rx tx rest; do
        [[ $iface == Inter* || $iface == face ]] && continue
        iface=${iface%:}
        rx_cur=$rx
        tx_cur=$tx
        if [[ -n ${rx_old[$iface]} ]]; then
            rx_rate=$(( (rx_cur - rx_old[$iface]) / INTERVAL / 1024 ))
            tx_rate=$(( (tx_cur - tx_old[$iface]) / INTERVAL / 1024 ))
        else
            rx_rate=0
            tx_rate=0
        fi
        net_devs+="{\"iface\":\"$iface\",\"rx_kbps\":$rx_rate,\"tx_kbps\":$tx_rate},"
        rx_old[$iface]=$rx_cur
        tx_old[$iface]=$tx_cur
    done < <(grep -v lo /proc/net/dev)  # 排除回环接口
    net_devs=$(echo "$net_devs" | sed 's/,$//')"]"

    # --- 网络进程信息 ---
    connections="["
    while read -r line; do
        proto=$(echo "$line" | awk '{print $1}')
        state=$(echo "$line" | awk '{print $2}')
        local=$(echo "$line" | awk '{print $5}')
        remote=$(echo "$line" | awk '{print $6}')
        users=$(echo "$line" | awk '{print $7}')
        pid=$(echo "$users" | grep -o 'pid=[0-9]\+' | cut -d= -f2 | head -n1)
        pname=$(echo "$users" | grep -o '"[^"]\+"' | tr -d '"' | head -n1)
        [[ -z "$pid" ]] && continue
        [[ -z "$pname" ]] && pname="unknown"

        local_ip=$(echo "$local" | rev | cut -d: -f2- | rev)
        local_port=$(echo "$local" | rev | cut -d: -f1 | rev)
        remote_ip=$(echo "$remote" | rev | cut -d: -f2- | rev)
        remote_port=$(echo "$remote" | rev | cut -d: -f1 | rev)

        conn_count=$(ss -tunp | grep "pid=$pid" | wc -l)

        proc_rx=0
        proc_tx=0
        if [[ -r /proc/$pid/net/dev ]]; then
            while read iface rx tx; do
                [[ $iface == Inter* || $iface == face ]] && continue
                iface=${iface%:}
                proc_rx=$((proc_rx + rx))
                proc_tx=$((proc_tx + tx))
            done < <(awk 'NR>2 {print $1, $2, $10}' /proc/$pid/net/dev 2>/dev/null)
        fi
        if [[ -n ${proc_rx_old[$pid]} ]]; then
            rx_rate=$(( (proc_rx - proc_rx_old[$pid]) / INTERVAL / 1024 ))
            tx_rate=$(( (proc_tx - proc_tx_old[$pid]) / INTERVAL / 1024 ))
        else
            rx_rate=0
            tx_rate=0
        fi
        proc_rx_old[$pid]=$proc_rx
        proc_tx_old[$pid]=$proc_tx

        connections+="{\"pid\":$pid,\"name\":\"$pname\",\"local_ip\":\"$local_ip\",\"local_port\":\"$local_port\",\"remote_ip\":\"$remote_ip\",\"remote_port\":\"$remote_port\",\"connections\":$conn_count,\"upload_kbps\":$tx_rate,\"download_kbps\":$rx_rate},"
    done < <(ss -tunp -H | head -20)  # 限制连接数量

    connections=$(echo "$connections" | sed 's/,$//')"]"

    # --- 输出 JSON ---
    printf '///Start{"cpu_percent":%.1f,"mem_percent":%.1f,"top_processes":%s,"all_processes":%s,"disk_usage":%s,"net_usage":%s,"connections":%s}End///\n' \
        "$cpu_percent" "$mem_percent" "$processes" "$all_processes" "$disks" "$net_devs" "$connections"

    sleep $INTERVAL
done