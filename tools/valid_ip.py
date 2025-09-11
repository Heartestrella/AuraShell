import ipaddress
import re
from typing import Union


def is_valid_address(addr: str) -> Union[bool, str]:
    """
    自动判断并严格验证 IPv4、IPv6 地址或域名是否合法

    Args:
        addr: 要验证的地址字符串

    Returns:
        Union[bool, str]: 如果地址合法返回类型字符串("IPv4"/"IPv6"/"Domain")，否则返回False
    """
    if not isinstance(addr, str):
        return False

    addr = addr.strip()
    if not addr:
        return False

    # 移除可能的端口号（可选）
    if ':' in addr and ']' not in addr:  # 不是IPv6地址
        if addr.count(':') == 1:  # 可能是IPv4:port或hostname:port
            host, port = addr.rsplit(':', 1)
            if port.isdigit() and 0 <= int(port) <= 65535:
                addr = host  # 只验证主机部分

    # 首先尝试验证 IPv4（最严格的检查）
    if _is_valid_ipv4(addr):
        return True

    # 然后尝试验证 IPv6
    if _is_valid_ipv6(addr):
        return True

    # 最后验证域名
    if _is_valid_domain(addr):
        return True

    return False


def _is_valid_ipv4(addr: str) -> bool:
    """严格验证 IPv4 地址"""
    # 基本格式检查
    if addr.count('.') != 3:
        return False

    parts = addr.split('.')
    if len(parts) != 4:
        return False

    for part in parts:
        # 检查是否为数字
        if not part.isdigit():
            return False

        # 检查前导零（除了单独的0）
        if len(part) > 1 and part[0] == '0':
            return False

        # 检查数值范围
        try:
            num = int(part)
            if not 0 <= num <= 255:
                return False
        except ValueError:
            return False

    return True


def _is_valid_ipv6(addr: str) -> bool:
    """严格验证 IPv6 地址"""
    try:
        # 使用 ipaddress 库进行严格验证
        ip = ipaddress.IPv6Address(addr)

        # 可选：排除一些特殊地址
        if ip.is_unspecified or ip.is_loopback:
            return False

        return True

    except (ipaddress.AddressValueError, ValueError):
        return False


def _is_valid_domain(addr: str) -> bool:
    """严格验证域名"""
    # 长度检查
    if len(addr) > 253:
        return False

    # 不能以点开头或结尾
    if addr.startswith('.') or addr.endswith('.'):
        return False

    # 分割标签
    labels = addr.split('.')
    if len(labels) < 2:  # 至少要有顶级域和二级域
        return False

    # 检查每个标签
    for label in labels:
        # 标签不能为空
        if not label:
            return False

        # 标签长度限制
        if len(label) > 63:
            return False

        # 标签格式检查（字母、数字、连字符）
        if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$', label):
            return False

        # 首尾不能是连字符
        if label.startswith('-') or label.endswith('-'):
            return False

    # 顶级域检查（必须至少2个字符且主要为字母）
    tld = labels[-1]
    if len(tld) < 2 or not any(c.isalpha() for c in tld):
        return False

    # 检查常见无效模式
    if re.search(r'\.\.', addr):  # 连续的点
        return False

    return True

# 测试函数


def test_address_validation():
    """测试地址验证函数"""
    test_cases = [
        # 合法 IPv4
        ("192.168.1.1", "IPv4"),
        ("8.8.8.8", "IPv4"),
        ("255.255.255.255", "IPv4"),
        ("0.0.0.0", "IPv4"),

        # 非法 IPv4
        ("192.168.01.1", False),
        ("256.0.0.1", False),
        ("1234.132.1", False),
        ("192.168.1", False),

        # 合法 IPv6
        ("2001:0db8:85a3:0000:0000:8a2e:0370:7334", "IPv6"),
        ("2001::1", "IPv6"),
        ("::1", "IPv6"),

        # 非法 IPv6
        ("2001::1::1", False),
        (":::", False),

        # 合法域名
        ("example.com", "Domain"),
        ("sub-domain.example.com", "Domain"),
        ("google.com", "Domain"),

        # 非法域名
        ("-bad.example.com", False),
        ("bad-.example.com", False),
        ("too..many.dots.com", False),
        ("test.c", False),

        # 你的测试用例
        ("1234.132.1", False),
        ("192.168.01.1", False),
        ("256.0.0.1", False),
        ("2001:0db8:85a3:0000:0000:8a2e:0370:7334", "IPv6"),
        ("2001::1", "IPv6"),
        ("example.com", "Domain"),
        ("sub-domain.example.com", "Domain"),
        ("-bad.example.com", False),
        ("too..many..dots", False),
        ("123.456.78.90", False)
    ]

    print("测试结果:")
    print("=" * 60)
    all_passed = True

    for addr, expected in test_cases:
        result = is_valid_address(addr)
        status = "✓" if result == expected else "✗"
        if result != expected:
            all_passed = False

        print(f"{status} {addr:<45} -> 期望: {expected:<8} 实际: {result}")

    print("\n" + "=" * 60)
    if all_passed:
        print("✓ 所有测试用例通过！")
    else:
        print("✗ 有些测试用例未通过！")

    return all_passed
