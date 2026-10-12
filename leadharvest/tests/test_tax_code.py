"""
Unit tests kiểm tra toàn bộ logic Mã số thuế (MST) và chặn CCCD theo BA §5.3, §6, §8.
"""

from leadharvest.validators.tax_code import (
    parse_and_validate_tax_code,
    verify_tax_code_checksum,
)


def test_valid_enterprise_tax_code():
    # MST 10 chữ số
    info = parse_and_validate_tax_code("0300588569")
    assert info is not None
    assert info.cleaned == "0300588569"
    assert info.root_code == "0300588569"
    assert info.is_branch is False


def test_valid_branch_tax_code():
    # MST chi nhánh 13 số, format thành XXXXXXXXXX-YYY
    info = parse_and_validate_tax_code("0300588569-001")
    assert info is not None
    assert info.cleaned == "0300588569-001"
    assert info.root_code == "0300588569"
    assert info.is_branch is True

    # Trường hợp dính liền 13 số
    info2 = parse_and_validate_tax_code("0300588569002")
    assert info2 is not None
    assert info2.cleaned == "0300588569-002"
    assert info2.root_code == "0300588569"
    assert info2.is_branch is True


def test_reject_cccd_12_digits():
    # 12 chữ số là số định danh cá nhân / CCCD (BA §5.3: Cấm thu thập CCCD)
    assert parse_and_validate_tax_code("079123456789") is None
    assert parse_and_validate_tax_code("001099123456") is None


def test_invalid_tax_codes():
    assert parse_and_validate_tax_code("") is None
    assert parse_and_validate_tax_code("123") is None
    assert parse_and_validate_tax_code("ABCDEFGHIJ") is None
