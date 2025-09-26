#!/bin/bash
TOP_N=4
INTERVAL=3

# 初始化网卡数据
declare -A rx_old tx_old

# 初始化进程流量数据
declare -A proc_tx_old proc_rx_old

while true; do
    # --- CPU 使用率 ---
    cpu_percent=$(LC_ALL=C top -bn2 -d0.2 | grep "Cpu(s)" | tail -n1 | awk '{print 100 - $8}')

    # --- 内存使用率 ---
    mem_percent=$(free | awk '/Mem/ {printf("%.1f", $3/$2 * 100)}')

    # --- 前 N 个进程 ---
    processes=$(ps -eo pid,comm,%cpu,%mem --sort=-%cpu \
        | awk 'NR>1 && $2 !~ /^kworker/ && $2 !~ /^rcu_/ {print $1, $2, $3, $4}' \
        | head -n $TOP_N \
        | awk '{printf "{\"pid\":%s,\"name\":\"%s\",\"cpu\":%s,\"mem\":%s},",$1,$2,$3,$4}' \
        | sed 's/,$//')
    processes="[$processes]"

    # --- 全部进程 ---
    all_processes=$(ps -eo user,pid,comm,%cpu,%mem,cmd --no-headers \
        | awk '
            function escape_json(str) {
                gsub(/\\/,"\\\\",str);
                gsub(/\"/,"\\\"",str);
                gsub(/\t/,"\\t",str);
                gsub(/\r/,"\\r",str);
                gsub(/\n/,"\\n",str);
                return str;
            }
            BEGIN{print "["; first=1}
            {
                user=$1; pid=$2; name=$3; cpu=$4; mem=$5;
                $1=$2=$3=$4=$5="";
                sub(/^ +/,"",$0);       
                cmd=escape_json($0);    
                if (!first) printf ",";
                printf "{\"user\":\"%s\",\"pid\":%s,\"name\":\"%s\",\"cpu\":%s,\"mem\":%s,\"command\":\"%s\"}", user,pid,name,cpu,mem,cmd;
                first=0
            }
            END{print "]"}
        ')



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
    done < /proc/net/dev
    net_devs=$(echo "$net_devs" | sed 's/,$//')"]"

    # --- 网络进程信息 ---
    connections="["
    # 获取所有 TCP/UDP socket 对应 PID 和本地/远程地址
    while read -r line; do
        # ss 输出：Netid State Recv-Q Send-Q Local Address:Port Peer Address:Port Process
        proto=$(echo "$line" | awk '{print $1}')
        state=$(echo "$line" | awk '{print $2}')
        local=$(echo "$line" | awk '{print $5}')
        remote=$(echo "$line" | awk '{print $6}')
        users=$(echo "$line" | awk '{print $7}')
        pid=$(echo "$users" | grep -o 'pid=[0-9]\+' | cut -d= -f2 | head -n1)
        pname=$(echo "$users" | grep -o '"[^"]\+"' | tr -d '"' | head -n1)
        [[ -z "$pid" ]] && continue
        [[ -z "$pname" ]] && pname="unknown"

        # 分割 IP 和端口
        local_ip=$(echo "$local" | rev | cut -d: -f2- | rev)
        local_port=$(echo "$local" | rev | cut -d: -f1 | rev)
        remote_ip=$(echo "$remote" | rev | cut -d: -f2- | rev)
        remote_port=$(echo "$remote" | rev | cut -d: -f1 | rev)

        # 连接数量
        conn_count=$(ss -tunp | grep "pid=$pid" | wc -l)

        # --- 每个进程的上传/下载速率 ---
        # 计算 proc 网络流量
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
        # 计算速率
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
    done < <(ss -tunp -H)

    connections=$(echo "$connections" | sed 's/,$//')"]"

    # --- 输出 JSON ---
    printf '///Start{"cpu_percent":%.1f,"mem_percent":%.1f,"top_processes":%s,"all_processes":%s,"net_usage":%s,"connections":%s}End///\n' \
        "$cpu_percent" "$mem_percent" "$processes" "$all_processes" "$net_devs" "$connections"

    sleep $INTERVAL
done
