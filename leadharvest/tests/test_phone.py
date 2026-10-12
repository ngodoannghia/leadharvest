"""
Unit tests kiểm tra toàn bộ logic chuẩn hóa & xác thực SĐT theo BA §7.
"""

from leadharvest.models.enums import PhoneType
from leadharvest.validators.phone import (
    assign_primary_secondary,
    classify_phone,
    extract_phones,
    is_junk_phone,
    normalize_digits,
)


def test_normalize_digits():
    # Chuyển đổi +84, 84, 0084 về đầu 0
    assert normalize_digits("+84909123456") == "0909123456"
    assert normalize_digits("84909123456") == "0909123456"
    assert normalize_digits("0084909123456") == "0909123456"
    assert normalize_digits("842839102901") == "02839102901"
    # Dấu chấm, khoảng trắng, gạch nối
    assert normalize_digits("(+84-28) 3622.0940") == "02836220940"
    # Hotline giữ nguyên
    assert normalize_digits("1800 1122") == "18001122"
    assert normalize_digits("1900.6789") == "19006789"


def test_classify_phone_mobile():
    # Số di động 10 số, đầu 03, 05, 07, 08, 09
    assert classify_phone("0909123456") == PhoneType.MOBILE
    assert classify_phone("0389123456") == PhoneType.MOBILE
    assert classify_phone("0567123456") == PhoneType.MOBILE
    assert classify_phone("0778123456") == PhoneType.MOBILE
    assert classify_phone("0899123456") == PhoneType.MOBILE


def test_classify_phone_landline():
    # Số bàn 11 số, đầu 02
    assert classify_phone("02839102901") == PhoneType.LANDLINE  # TP.HCM
    assert classify_phone("02438512345") == PhoneType.LANDLINE  # Hà Nội
    assert classify_phone("02903123456") == PhoneType.LANDLINE  # Cà Mau

    # Số bàn 10 số kiểu cũ (trước 2017) -> KHÔNG hợp lệ
    assert classify_phone("0283910290") is None


def test_classify_phone_hotline():
    assert classify_phone("18001122") == PhoneType.HOTLINE
    assert classify_phone("19006789") == PhoneType.HOTLINE
    assert classify_phone("1800558899") == PhoneType.HOTLINE


def test_is_junk_phone():
    # Số rác lặp lại toàn 1 chữ số
    assert is_junk_phone("0900000000") is True
    assert is_junk_phone("02811111111") is True
    # Dãy tăng tuần tự
    assert is_junk_phone("0901234567") is True
    # Số thật
    assert is_junk_phone("0939096809") is False
    assert is_junk_phone("02839102901") is False


def test_extract_multiple_phones():
    raw = "(+84-28) 36220940 – 45 / 0909.123.456 / 1900.5678"
    phones = extract_phones(raw)
    numbers = [p.number for p in phones]

    assert "02836220940" in numbers
    assert "0909123456" in numbers
    assert "19005678" in numbers


def test_assign_primary_secondary():
    # Trường hợp 1: Có cả Mobile và Landline -> Mobile làm chính, Landline làm phụ
    raw = "02839102901 / 0939096809"
    phones = extract_phones(raw)
    p, s = assign_primary_secondary(phones)
    assert p is not None and p.number == "0939096809" and p.type == PhoneType.MOBILE
    assert s is not None and s.number == "02839102901" and s.type == PhoneType.LANDLINE

    # Trường hợp 2: Chỉ có Landline -> Landline làm chính
    phones_landline_only = extract_phones("02839102901")
    p, s = assign_primary_secondary(phones_landline_only)
    assert p is not None and p.type == PhoneType.LANDLINE
    assert s is None

    # Trường hợp 3: Chỉ có Hotline -> p là None (BA cấm Hotline ở cột chính)
    phones_hotline_only = extract_phones("19005678")
    p, s = assign_primary_secondary(phones_hotline_only)
    assert p is None
    assert s is not None and s.type == PhoneType.HOTLINE
