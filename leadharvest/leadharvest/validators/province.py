"""
Chuẩn hóa và nhận diện Tỉnh / Thành phố Việt Nam (BA §2.2, §6 cột 9).

Quy tắc:
  1. Chuẩn hóa tên tỉnh/thành về danh sách quy chuẩn thống nhất (bỏ tiền tố Tỉnh/TP/Thành phố).
  2. Hỗ trợ ánh xạ các tên gọi cũ / biến thể / viết tắt (vd: "TP HCM", "Sài Gòn", "Hà Tây", "Bạc Liêu"...).
  3. Tự động nhận diện Tỉnh/Thành phố từ địa chỉ chi tiết nếu cột tỉnh bị thiếu.
"""

from __future__ import annotations

import re
from leadharvest.validators.text import clean_whitespace, strip_accents

# Danh mục các tỉnh/thành phố quy chuẩn hiện hành (đã bỏ tiền tố "Tỉnh", "Thành phố")
CANONICAL_PROVINCES: tuple[str, ...] = (
    "Hà Nội", "Hồ Chí Minh", "Hải Phòng", "Đà Nẵng", "Cần Thơ",
    "An Giang", "Bắc Giang", "Bắc Kạn", "Bạc Liêu", "Bắc Ninh",
    "Bến Tre", "Bình Định", "Bình Dương", "Bình Phước", "Bình Thuận",
    "Cà Mau", "Cao Bằng", "Đắk Lắk", "Đắk Nông", "Điện Biên",
    "Đồng Nai", "Đồng Tháp", "Gia Lai", "Hà Giang", "Hà Nam",
    "Hà Tĩnh", "Hải Dương", "Hậu Giang", "Hòa Bình", "Hưng Yên",
    "Khánh Hòa", "Kiên Giang", "Kon Tum", "Lai Châu", "Lâm Đồng",
    "Lạng Sơn", "Lào Cai", "Long An", "Nam Định", "Nghệ An",
    "Ninh Bình", "Ninh Thuận", "Phú Thọ", "Phú Yên", "Quảng Bình",
    "Quảng Nam", "Quảng Ngãi", "Quảng Ninh", "Quảng Trị", "Sóc Trăng",
    "Sơn La", "Tây Ninh", "Thái Bình", "Thái Nguyên", "Thanh Hóa",
    "Thừa Thiên Huế", "Tiền Giang", "Trà Vinh", "Tuyên Quang", "Vĩnh Long",
    "Vĩnh Phúc", "Yên Bái", "Bà Rịa - Vũng Tàu"
)

# Ánh xạ từ các biến thể không dấu / viết tắt / tên cũ về Tỉnh/Thành chuẩn
_PROVINCE_ALIAS_MAP: dict[str, str] = {
    # Viết tắt và biến thể TP.HCM
    "hcm": "Hồ Chí Minh",
    "tphcm": "Hồ Chí Minh",
    "tp hcm": "Hồ Chí Minh",
    "tp ho chi minh": "Hồ Chí Minh",
    "sai gon": "Hồ Chí Minh",
    "thanh pho ho chi minh": "Hồ Chí Minh",
    "ho chi minh": "Hồ Chí Minh",

    # Hà Nội
    "hn": "Hà Nội",
    "ha noi": "Hà Nội",
    "thanh pho ha noi": "Hà Nội",
    "tp ha noi": "Hà Nội",
    "ha tay": "Hà Nội",  # Sáp nhập

    # Đà Nẵng
    "da nang": "Đà Nẵng",
    "tp da nang": "Đà Nẵng",

    # Hải Phòng
    "hai phong": "Hải Phòng",
    "tp hai phong": "Hải Phòng",

    # Cần Thơ
    "can tho": "Cần Thơ",
    "tp can tho": "Cần Thơ",

    # Bà Rịa - Vũng Tàu
    "ba ria vung tau": "Bà Rịa - Vũng Tàu",
    "ba ria - vung tau": "Bà Rịa - Vũng Tàu",
    "vung tau": "Bà Rịa - Vũng Tàu",
    "brvt": "Bà Rịa - Vũng Tàu",

    # Thừa Thiên Huế
    "thua thien hue": "Thừa Thiên Huế",
    "tt hue": "Thừa Thiên Huế",
    "hue": "Thừa Thiên Huế",
}

# Tạo mapping tự động không dấu cho toàn bộ danh mục chuẩn
for p in CANONICAL_PROVINCES:
    _PROVINCE_ALIAS_MAP[strip_accents(p)] = p
    _PROVINCE_ALIAS_MAP[strip_accents(f"tinh {p}")] = p
    _PROVINCE_ALIAS_MAP[strip_accents(f"thanh pho {p}")] = p
    _PROVINCE_ALIAS_MAP[strip_accents(f"tp {p}")] = p


def normalize_province_name(raw_province: str | None) -> str | None:
    """
    Chuẩn hóa tên tỉnh/thành phố về tên quy chuẩn chính thức.
    Ví dụ: 'Tp. Hồ Chí Minh' -> 'Hồ Chí Minh', 'tỉnh bình dương' -> 'Bình Dương'.
    """
    if not raw_province:
        return None

    cleaned = clean_whitespace(raw_province)
    key = strip_accents(cleaned)
    # Loại bỏ các tiền tố phổ biến
    key = re.sub(r"^(?:tinh|tp\.?|thanh pho|t\.?p\.?)\s+", "", key).strip()

    if key in _PROVINCE_ALIAS_MAP:
        return _PROVINCE_ALIAS_MAP[key]

    # Kiểm tra partial match
    for k, v in _PROVINCE_ALIAS_MAP.items():
        if key == k:
            return v

    return None


def detect_province_from_address(address: str | None) -> str | None:
    """
    Trích xuất tỉnh/thành phố từ chuỗi địa chỉ chi tiết nếu trường tỉnh bị rỗng.
    Thường nằm ở cuối chuỗi địa chỉ (vd: '..., Phường Tân Tạo, Tp. Hồ Chí Minh').
    """
    if not address:
        return None

    # Tách các vế theo dấu phẩy hoặc gạch nối
    parts = [clean_whitespace(p) for p in re.split(r"[,;–-]", address) if clean_whitespace(p)]
    # Quét từ cuối địa chỉ lên đầu
    for part in reversed(parts):
        prov = normalize_province_name(part)
        if prov:
            return prov

    # Nếu tách dấu phẩy không tìm thấy, quét tìm tên tỉnh trong toàn bộ địa chỉ
    addr_no_accent = strip_accents(address)
    for p in sorted(CANONICAL_PROVINCES, key=lambda x: len(x), reverse=True):
        p_no_accent = strip_accents(p)
        pattern = rf"\b(?:tinh|tp|thanh pho)?\s*{re.escape(p_no_accent)}\b"
        if re.search(pattern, addr_no_accent):
            return p

    return None
