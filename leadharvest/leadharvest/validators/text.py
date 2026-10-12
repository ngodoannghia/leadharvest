"""
Tiện ích chuẩn hóa văn bản tiếng Việt: khoảng trắng, dấu, tên cơ sở, địa chỉ.
"""

from __future__ import annotations

import re
import unicodedata

# Chuỗi "giữ chỗ" thường gặp trên các trang danh bạ — không được coi là dữ liệu thật.
PLACEHOLDER_VALUES: frozenset[str] = frozenset(
    {
        "", "-", "--", ".", "n/a", "na", "null", "none", "không có", "khong co",
        "đang cập nhật", "dang cap nhat", "chưa cập nhật", "chua cap nhat",
        "updating", "chưa có", "chua co",
    }
)


def nfc(text: str) -> str:
    """
    Đưa chuỗi về dạng Unicode NFC.

    Lý do: nhiều website lưu tiếng Việt ở dạng tổ hợp (NFD — chữ + dấu rời),
    khiến "Thủy" ở hai nguồn nhìn giống nhau nhưng so sánh `==` lại khác.
    """
    return unicodedata.normalize("NFC", text)


def clean_whitespace(text: str | None) -> str:
    """
    Gộp mọi khoảng trắng (tab, xuống dòng, nbsp, nhiều dấu cách) thành 1 dấu cách
    và cắt khoảng trắng hai đầu. Trả về chuỗi rỗng nếu input là None.
    """
    if not text:
        return ""
    text = nfc(str(text)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def is_placeholder(text: str | None) -> bool:
    """True nếu chuỗi rỗng hoặc chỉ là giá trị giữ chỗ ("Đang cập nhật", "N/A"...)."""
    return clean_whitespace(text).lower() in PLACEHOLDER_VALUES


def strip_accents(text: str) -> str:
    """
    Bỏ dấu tiếng Việt, chuyển về chữ thường — dùng cho so khớp mềm (tỉnh/thành, tên).

    Lưu ý: KHÔNG dùng cho phân loại ngành, vì bỏ dấu làm "may" (dệt may)
    trùng với "máy" (máy móc).
    """
    text = nfc(text).replace("đ", "d").replace("Đ", "D")
    decomposed = unicodedata.normalize("NFD", text)
    without_marks = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return without_marks.lower()


def normalize_company_name(name: str | None) -> str:
    """
    Chuẩn hóa tên doanh nghiệp/cơ sở (BA §6 cột 2: "bỏ khoảng trắng thừa").

    - Gộp khoảng trắng, bỏ dấu câu thừa ở hai đầu.
    - Giữ nguyên chữ hoa/thường như nguồn (tên pháp nhân thường viết HOA).
    """
    name = clean_whitespace(name)
    return name.strip(" .,;:-–_|/\\\"'")


def name_key(name: str) -> str:
    """
    Khóa so sánh tên để phát hiện cùng một pháp nhân giữa các nguồn.

    Bỏ dấu, bỏ tiền tố loại hình (công ty, TNHH, cổ phần...) và ký tự đặc biệt.
    Ví dụ: "CÔNG TY TNHH Thủy Sản ABC" và "Cty TNHH thuy san ABC" -> "thuy san abc".
    """
    key = strip_accents(name)
    key = re.sub(
        r"\b(cong ty|cty|co phan|cp|tnhh|mtv|mot thanh vien|trach nhiem huu han|"
        r"doanh nghiep tu nhan|dntn|hop tac xa|htx|chi nhanh|co\.?,? ?ltd|jsc|company|limited)\b",
        " ",
        key,
    )
    key = re.sub(r"[^a-z0-9 ]", " ", key)
    return re.sub(r"\s+", " ", key).strip()


def normalize_person_name(name: str | None) -> str:
    """
    Chuẩn hóa tên người đại diện/chủ cơ sở (BA §6 cột 3).

    - Bỏ danh xưng ở đầu (Ông, Bà, Anh, Chị, Mr, Mrs, Ms).
    - Viết hoa chữ cái đầu mỗi từ: "NGUYỄN văn a" -> "Nguyễn Văn A".
    """
    name = clean_whitespace(name)
    name = re.sub(r"^(ông|bà|anh|chị|mr\.?|mrs\.?|ms\.?)\s+", "", name, flags=re.IGNORECASE)
    return " ".join(word.capitalize() for word in name.split(" ")) if name else ""


# Các dấu hiệu cho thấy địa chỉ đủ cụ thể để Sales/giao nhận tìm được cơ sở (BA §3.2).
# Có ít nhất MỘT dấu hiệu cấp cơ sở (xã/phường/ấp/đường/lô/KCN...) mới đạt.
_SPECIFIC_ADDRESS_PATTERN = re.compile(
    r"(\bxã\b|\bphường\b|\bthị trấn\b|\bấp\b|\bthôn\b|\bkhóm\b|\bbản\b|\btổ\b|\bxóm\b|"
    r"\bkhu phố\b|\bkp\b|\bkcn\b|khu công nghiệp|cụm công nghiệp|\bccn\b|khu chế xuất|"
    r"\bđường\b|quốc lộ|\bql\b|tỉnh lộ|\bđt\s?\d|\blô\b|\bsố\s*\d|^\d+[a-z]?\b|\d+/\d+)",
    re.IGNORECASE,
)

# Tối thiểu 10 ký tự: loại các địa chỉ kiểu "Cà Mau", "TP.HCM".
MIN_ADDRESS_LENGTH = 10


def is_specific_address(address: str | None) -> bool:
    """
    Kiểm tra địa chỉ có "cụ thể" theo BA §3.2 hay không.

    Đạt khi:
      1. Không phải giá trị giữ chỗ và dài tối thiểu `MIN_ADDRESS_LENGTH` ký tự.
      2. Có ít nhất một dấu hiệu cấp cơ sở: xã/phường/thị trấn/ấp/thôn/khóm/tổ,
         đường/quốc lộ, lô/KCN/CCN, hoặc số nhà.

    Ví dụ đạt     : "Ấp 14, xã Vĩnh Mỹ, tỉnh Cà Mau"
    Ví dụ không đạt: "Tỉnh Cà Mau", "Việt Nam"
    """
    address = clean_whitespace(address)
    if is_placeholder(address) or len(address) < MIN_ADDRESS_LENGTH:
        return False
    return bool(_SPECIFIC_ADDRESS_PATTERN.search(address))
