"""
PII Hashing Service

Privacy-preserving identity resolution using hashed personally identifiable information.
This allows matching customers across systems without storing PII in plaintext.

Supports hashing:
- Email addresses
- Names
- Physical addresses

All hashes are salted with a secret key for additional security.
"""

import hashlib
import os
import re
from typing import Optional


# Salt for hashing - should be stored in environment variable in production
PII_HASH_SALT = os.getenv("PII_HASH_SALT", "quimbi-pii-hash-salt-change-in-production")


def normalize_email(email: str) -> str:
    """
    Normalize email address for consistent hashing.

    - Convert to lowercase
    - Strip whitespace
    - Remove dots in Gmail addresses (gmail treats foo.bar@gmail.com = foobar@gmail.com)

    Args:
        email: Raw email address

    Returns:
        Normalized email address
    """
    if not email:
        return ""

    email = email.lower().strip()

    # Handle Gmail dot normalization
    if email.endswith("@gmail.com"):
        local, domain = email.split("@")
        local = local.replace(".", "")
        email = f"{local}@{domain}"

    return email


def normalize_name(name: str) -> str:
    """
    Normalize name for consistent hashing.

    - Convert to lowercase
    - Remove all whitespace, punctuation, special characters
    - Remove common suffixes (Jr, Sr, III, etc.)

    Args:
        name: Raw name (e.g., "Molly Stevens", "John Smith, Jr.")

    Returns:
        Normalized name (e.g., "mollystevens", "johnsmith")
    """
    if not name:
        return ""

    # Convert to lowercase
    name = name.lower()

    # Remove suffixes
    suffixes = [", jr", ", sr", " jr", " sr", " ii", " iii", " iv", " phd", " md", " esq"]
    for suffix in suffixes:
        name = name.replace(suffix, "")

    # Remove all non-alphanumeric characters
    name = re.sub(r'[^a-z0-9]', '', name)

    return name


def normalize_address(address: str) -> str:
    """
    Normalize physical address for consistent hashing.

    - Convert to lowercase
    - Remove all whitespace, punctuation
    - Normalize common abbreviations (St -> street, Ave -> avenue, etc.)
    - Remove apartment/unit numbers

    Args:
        address: Raw address (e.g., "6004 Twin Valley Cv., Austin TX 78731")

    Returns:
        Normalized address (e.g., "6004twinvalleycoveaustintx78731")
    """
    if not address:
        return ""

    # Convert to lowercase
    address = address.lower()

    # Normalize common abbreviations
    abbreviations = {
        'st.': 'street',
        'st': 'street',
        'ave.': 'avenue',
        'ave': 'avenue',
        'blvd.': 'boulevard',
        'blvd': 'boulevard',
        'rd.': 'road',
        'rd': 'road',
        'dr.': 'drive',
        'dr': 'drive',
        'ct.': 'court',
        'ct': 'court',
        'cv.': 'cove',
        'cv': 'cove',
        'ln.': 'lane',
        'ln': 'lane',
        'pl.': 'place',
        'pl': 'place',
        'apt.': '',
        'apt': '',
        '#': '',
        'unit': '',
    }

    for abbr, full in abbreviations.items():
        address = address.replace(f' {abbr} ', f' {full} ')
        address = address.replace(f' {abbr}', f' {full}')

    # Remove all non-alphanumeric characters
    address = re.sub(r'[^a-z0-9]', '', address)

    return address


def hash_pii(value: str, salt: Optional[str] = None) -> str:
    """
    Hash PII value using SHA256 with salt for privacy-preserving identity resolution.

    Args:
        value: PII value to hash (already normalized)
        salt: Optional salt (defaults to PII_HASH_SALT)

    Returns:
        64-character hexadecimal hash
    """
    if not value:
        return ""

    if salt is None:
        salt = PII_HASH_SALT

    # Combine salt and value
    salted_value = f"{salt}{value}"

    # Hash using SHA256
    hash_obj = hashlib.sha256(salted_value.encode('utf-8'))
    return hash_obj.hexdigest()


def hash_email(email: str) -> str:
    """
    Hash email address for privacy-preserving identity resolution.

    Args:
        email: Raw email address

    Returns:
        64-character hexadecimal hash

    Example:
        >>> hash_email("Molly@MoonTowerCoaching.com")
        "a1b2c3d4..."
    """
    normalized = normalize_email(email)
    return hash_pii(normalized)


def hash_name(name: str) -> str:
    """
    Hash name for privacy-preserving identity resolution.

    Args:
        name: Raw name (e.g., "Molly Stevens")

    Returns:
        64-character hexadecimal hash

    Example:
        >>> hash_name("Molly Stevens")
        "e5f6g7h8..."
    """
    normalized = normalize_name(name)
    return hash_pii(normalized)


def hash_address(address: str) -> str:
    """
    Hash physical address for privacy-preserving identity resolution.

    Args:
        address: Raw address (e.g., "6004 Twin Valley Cv., Austin TX 78731")

    Returns:
        64-character hexadecimal hash

    Example:
        >>> hash_address("6004 Twin Valley Cv., Austin TX 78731")
        "i9j0k1l2..."
    """
    normalized = normalize_address(address)
    return hash_pii(normalized)


# Example usage and testing
if __name__ == "__main__":
    # Test email hashing
    print("Email Hashing:")
    print(f"  molly@moontowercoaching.com -> {hash_email('molly@moontowercoaching.com')}")
    print(f"  Molly@MoonTowerCoaching.com -> {hash_email('Molly@MoonTowerCoaching.com')}")
    print(f"  molly@moontowercoaching.com == Molly@MoonTowerCoaching.com: {hash_email('molly@moontowercoaching.com') == hash_email('Molly@MoonTowerCoaching.com')}")
    print()

    # Test name hashing
    print("Name Hashing:")
    print(f"  Molly Stevens -> {hash_name('Molly Stevens')}")
    print(f"  molly stevens -> {hash_name('molly stevens')}")
    print(f"  Molly Stevens == molly stevens: {hash_name('Molly Stevens') == hash_name('molly stevens')}")
    print()

    # Test address hashing
    print("Address Hashing:")
    print(f"  6004 Twin Valley Cv., Austin TX 78731 -> {hash_address('6004 Twin Valley Cv., Austin TX 78731')}")
    print(f"  6004 Twin Valley Cove Austin TX 78731 -> {hash_address('6004 Twin Valley Cove Austin TX 78731')}")
    print(f"  Normalized addresses match: {hash_address('6004 Twin Valley Cv., Austin TX 78731') == hash_address('6004 Twin Valley Cove Austin TX 78731')}")
