#!/bin/bash
TOP_N=4
INTERVAL=3

# 初始化网卡数据
declare -A rx_old tx_old
while true; do
    # CPU 使用率
    cpu_percent=$(LC_ALL=C top -bn2 -d0.2 | grep "Cpu(s)" | tail -n1 | awk '{print 100 - $8}')

    # 内存使用率
    mem_percent=$(free | awk '/Mem/ {printf("%.1f", $3/$2 * 100)}')

    # 前 N 个进程
    processes=$(ps -eo pid,comm,%cpu,%mem --sort=-%cpu \
    | awk 'NR>1 && $2 !~ /^kworker/ && $2 !~ /^rcu_/ {print $1, $2, $3, $4}' \
    | head -n $TOP_N \
    | awk '{printf "{\"pid\":%s,\"name\":\"%s\",\"cpu\":%s,\"mem\":%s},",$1,$2,$3,$4}' \
    | sed 's/,$//')
    processes="[$processes]"

    # 全部进程（不放在 top_processes 中）
    all_processes=$(ps -eo pid,comm,%cpu,%mem --no-headers \
    | awk '{printf "{\"pid\":%s,\"name\":\"%s\",\"cpu\":%s,\"mem\":%s},",$1,$2,$3,$4}' \
    | sed 's/,$//' \
    | awk 'BEGIN{printf "["}{print}END{printf "]"}')

    # 网卡流量（实时速率 KB/s）
    net_devs="["
    while read iface rx tx rest; do
        [[ $iface == Inter* || $iface == face ]] && continue
        iface=${iface%:}
        rx_cur=$rx
        tx_cur=$tx
        if [[ -n ${rx_old[$iface]} ]]; then
            rx_rate=$(( (rx_cur - rx_old[$iface]) / $INTERVAL / 1024 ))
            tx_rate=$(( (tx_cur - tx_old[$iface]) / $INTERVAL / 1024 ))
        else
            rx_rate=0
            tx_rate=0
        fi
        net_devs+="{\"iface\":\"$iface\",\"rx_kbps\":$rx_rate,\"tx_kbps\":$tx_rate},"
        rx_old[$iface]=$rx_cur
        tx_old[$iface]=$tx_cur
    done < /proc/net/dev
    net_devs=$(echo "$net_devs" | sed 's/,$//')"]"

    # 拼 JSON
    printf '///Start{"cpu_percent":%.1f,"mem_percent":%.1f,"top_processes":%s,"all_processes":%s,"net_usage":%s}End///\n' \
        "$cpu_percent" "$mem_percent" "$processes" "$all_processes" "$net_devs"

    sleep $INTERVAL
done
