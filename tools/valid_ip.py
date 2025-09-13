import ipaddress
import re
from typing import Union


def is_valid_address(addr: str) -> Union[bool, str]:
    """
    Automatically determine and strictly validate whether an IPv4, IPv6 address or domain name is valid.

    Args:
        addr: The address string to validate

    Returns:
        Union[bool, str]: Returns the type string ("IPv4"/"IPv6"/"Domain") if the address is valid, otherwise returns False
    """
    if not isinstance(addr, str):
        return False

    addr = addr.strip()
    if not addr:
        return False

    # Remove possible port number (optional)
    if ':' in addr and ']' not in addr:  # Not an IPv6 address
        if addr.count(':') == 1:  # Could be IPv4:port or hostname:port
            host, port = addr.rsplit(':', 1)
            if port.isdigit() and 0 <= int(port) <= 65535:
                addr = host  # Only validate the host part

    # First try IPv4 (strict check)
    if _is_valid_ipv4(addr):
        return True

    # Then try IPv6
    if _is_valid_ipv6(addr):
        return True

    # Finally, validate domain name
    if _is_valid_domain(addr):
        return True

    return False


def _is_valid_ipv4(addr: str) -> bool:
    """Strictly validate IPv4 address"""
    # Basic format check
    if addr.count('.') != 3:
        return False

    parts = addr.split('.')
    if len(parts) != 4:
        return False

    for part in parts:
        # Check if it's a number
        if not part.isdigit():
            return False

        # Check for leading zeros (except single 0)
        if len(part) > 1 and part[0] == '0':
            return False

        # Check numeric range
        try:
            num = int(part)
            if not 0 <= num <= 255:
                return False
        except ValueError:
            return False

    return True


def _is_valid_ipv6(addr: str) -> bool:
    """Strictly validate IPv6 address"""
    try:
        # Use ipaddress module for strict validation
        ip = ipaddress.IPv6Address(addr)

        # Optional: exclude some special addresses
        if ip.is_unspecified or ip.is_loopback:
            return False

        return True

    except (ipaddress.AddressValueError, ValueError):
        return False


def _is_valid_domain(addr: str) -> bool:
    """Strictly validate domain name"""
    # Length check
    if len(addr) > 253:
        return False

    # Cannot start or end with a dot
    if addr.startswith('.') or addr.endswith('.'):
        return False

    # Split labels
    labels = addr.split('.')
    if len(labels) < 2:  # Must have at least second-level domain and TLD
        return False

    # Check each label
    for label in labels:
        # Label cannot be empty
        if not label:
            return False

        # Label length limit
        if len(label) > 63:
            return False

        # Label format check (letters, digits, hyphen)
        if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$', label):
            return False

        # Cannot start or end with hyphen
        if label.startswith('-') or label.endswith('-'):
            return False

    # Top-level domain check (at least 2 characters and must contain letters)
    tld = labels[-1]
    if len(tld) < 2 or not any(c.isalpha() for c in tld):
        return False

    # Check common invalid patterns
    if re.search(r'\.\.', addr):  # Consecutive dots
        return False

    return True


# Test function
def test_address_validation():
    """Test the address validation function"""
    test_cases = [
        # Valid IPv4
        ("192.168.1.1", "IPv4"),
        ("8.8.8.8", "IPv4"),
        ("255.255.255.255", "IPv4"),
        ("0.0.0.0", "IPv4"),

        # Invalid IPv4
        ("192.168.01.1", False),
        ("256.0.0.1", False),
        ("1234.132.1", False),
        ("192.168.1", False),

        # Valid IPv6
        ("2001:0db8:85a3:0000:0000:8a2e:0370:7334", "IPv6"),
        ("2001::1", "IPv6"),
        ("::1", "IPv6"),

        # Invalid IPv6
        ("2001::1::1", False),
        (":::", False),

        # Valid domain
        ("example.com", "Domain"),
        ("sub-domain.example.com", "Domain"),
        ("google.com", "Domain"),

        # Invalid domain
        ("-bad.example.com", False),
        ("bad-.example.com", False),
        ("too..many.dots.com", False),
        ("test.c", False),

        # Additional test cases
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

    print("Test Results:")
    print("=" * 60)
    all_passed = True

    for addr, expected in test_cases:
        result = is_valid_address(addr)
        status = "✓" if result == expected else "✗"
        if result != expected:
            all_passed = False

        print(f"{status} {addr:<45} -> Expected: {expected:<8} Actual: {result}")

    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All test cases passed!")
    else:
        print("✗ Some test cases failed!")

    return all_passed


if __name__ == "__main__":
    test_address_validation()
