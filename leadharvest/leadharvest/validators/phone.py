"""
Chuẩn hóa, phân loại và kiểm tra số điện thoại Việt Nam (BA §7).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from leadharvest.models.enums import PhoneType

MOBILE_PREFIXES: tuple[str, ...] = ("03", "05", "07", "08", "09")
MOBILE_LENGTH = 10

LANDLINE_PREFIX = "02"
LANDLINE_LENGTH = 11

HOTLINE_PREFIXES: tuple[str, ...] = ("1800", "1900")
HOTLINE_LENGTHS: tuple[int, ...] = (8, 10)

_SPLIT_PATTERN = re.compile(
    r"[;,/|\n\r]|\s[-–—]\s|\s(?:hoặc|hoac|or|và|va)\s|"
    r"(?:đt|dt|tel|điện thoại|dien thoai|mobile|hotline|di động|di dong|zalo|fax)\s*[:.]",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class PhoneNumber:
    number: str
    type: PhoneType

    def __str__(self) -> str:
        return f"{self.number} ({self.type.value})"


def normalize_digits(raw: str) -> str:
    digits = re.sub(r"\D", "", raw or "")
    if not digits:
        return ""

    if digits.startswith("0084"):
        digits = "0" + digits[4:]
    elif digits.startswith("840") and len(digits) in (12, 13):
        digits = digits[2:]
    elif digits.startswith("84") and len(digits) in (MOBILE_LENGTH + 1, LANDLINE_LENGTH + 1):
        digits = "0" + digits[2:]

    if digits.startswith(HOTLINE_PREFIXES):
        return digits

    if not digits.startswith("0"):
        if len(digits) == MOBILE_LENGTH - 1 and digits[0] in "35789":
            digits = "0" + digits
        elif len(digits) == LANDLINE_LENGTH - 1 and digits[0] == "2":
            digits = "0" + digits

    return digits


def _subscriber_part(number: str) -> str:
    if number.startswith(HOTLINE_PREFIXES):
        return number[4:]
    if number.startswith(LANDLINE_PREFIX):
        return number[-7:]
    return number[3:]


def is_junk_phone(number: str) -> bool:
    """
    Phát hiện chuỗi số giả lập / số rác (BA §7.1).
    Chỉ gắn cờ rác khi:
      - Số toàn một chữ số lặp lại (vd: 0900000000, 0281111111)
      - Toàn bộ số hoặc phần thuê bao dài (>= 6 chữ số) là dãy tăng/giảm liên tiếp (vd: 0123456789)
    """
    sub = _subscriber_part(number)
    if len(sub) < 4:
        return True
    if len(set(sub)) == 1:
        return True

    ascending = "0123456789012345"
    descending = "9876543210987654"

    # Kiểm tra toàn bộ số
    if number in ascending or number in descending:
        return True

    # Chỉ kiểm tra dãy số nếu phần thuê bao đủ dài (>= 6 ký tự) để không loại các số đẹp như đuôi 6789
    if len(sub) >= 6 and (sub in ascending or sub in descending):
        return True

    return False


def classify_phone(number: str) -> PhoneType | None:
    if not number or not number.isdigit():
        return None

    phone_type: PhoneType | None = None
    if len(number) == MOBILE_LENGTH and number.startswith(MOBILE_PREFIXES):
        phone_type = PhoneType.MOBILE
    elif len(number) == LANDLINE_LENGTH and number.startswith(LANDLINE_PREFIX):
        phone_type = PhoneType.LANDLINE
    elif number.startswith(HOTLINE_PREFIXES) and len(number) in HOTLINE_LENGTHS:
        phone_type = PhoneType.HOTLINE

    if phone_type is None or is_junk_phone(number):
        return None
    return phone_type


def split_raw_phone_text(raw: str) -> list[str]:
    return [part.strip() for part in _SPLIT_PATTERN.split(raw or "") if part and part.strip()]


def _tokens(part: str) -> list[str]:
    return [tok for tok in part.split() if re.search(r"\d", tok)]


def _parse_part(part: str, last_landline: str | None) -> tuple[list[PhoneNumber], str | None]:
    found: list[PhoneNumber] = []
    toks = _tokens(part)
    i = 0
    while i < len(toks):
        matched = False
        for j in range(i + 1, min(len(toks), i + 6) + 1):
            digits = normalize_digits("".join(toks[i:j]))
            phone_type = classify_phone(digits)
            if phone_type:
                found.append(PhoneNumber(digits, phone_type))
                if phone_type is PhoneType.LANDLINE:
                    last_landline = digits
                i = j
                matched = True
                break
            if len(digits) > LANDLINE_LENGTH + 2:
                break
        if matched:
            continue

        # Thử ghép mã vùng cho phần thuê bao số bàn (7 hoặc 8 số)
        frag = re.sub(r"\D", "", toks[i])
        # Không ghép nếu đoạn này rõ ràng là hotline hoặc số di động
        if (
            last_landline
            and len(frag) in (7, 8)
            and not frag.startswith(HOTLINE_PREFIXES)
            and not frag.startswith("0")
        ):
            candidate = last_landline[: LANDLINE_LENGTH - len(frag)] + frag
            if classify_phone(candidate) is PhoneType.LANDLINE:
                found.append(PhoneNumber(candidate, PhoneType.LANDLINE))
        i += 1
    return found, last_landline


def extract_phones(raw: str | Iterable[str] | None) -> list[PhoneNumber]:
    if raw is None:
        return []
    texts = [raw] if isinstance(raw, str) else list(raw)

    result: list[PhoneNumber] = []
    seen: set[str] = set()
    last_landline: str | None = None
    for text in texts:
        for part in split_raw_phone_text(text or ""):
            phones, last_landline = _parse_part(part, last_landline)
            for phone in phones:
                if phone.number not in seen:
                    seen.add(phone.number)
                    result.append(phone)
    return result


def assign_primary_secondary(
    phones: Iterable[PhoneNumber],
) -> tuple[PhoneNumber | None, PhoneNumber | None]:
    phones = list(phones)
    mobiles = [p for p in phones if p.type is PhoneType.MOBILE]
    landlines = [p for p in phones if p.type is PhoneType.LANDLINE]
    hotlines = [p for p in phones if p.type is PhoneType.HOTLINE]

    if mobiles:
        primary = mobiles[0]
        rest = mobiles[1:2] + landlines[:1] + hotlines[:1]
    elif landlines:
        primary = landlines[0]
        rest = hotlines[:1] + landlines[1:2]
    else:
        return None, (hotlines[0] if hotlines else None)

    return primary, (rest[0] if rest else None)
