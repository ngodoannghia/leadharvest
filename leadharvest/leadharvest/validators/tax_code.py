"""
Kiểm tra và chuẩn hóa Mã Số Thuế (MST) Việt Nam (BA §6 cột 8, §8.1).

Quy tắc:
  1. MST doanh nghiệp: 10 chữ số (chuẩn hóa thành 10 chữ số).
  2. MST chi nhánh / địa điểm trực thuộc: 13 chữ số, biểu diễn dạng "XXXXXXXXXX-YYY".
  3. MST 12 chữ số: là số Định danh cá nhân / CCCD của hộ kinh doanh cá thể.
     Theo BA §5.3 (Cấm thu thập CCCD/thông tin cá nhân nhạy cảm) -> KHÔNG xuất
     MST 12 số vào file giao khách (để None/rỗng).
  4. Trích xuất MST gốc (10 chữ số đầu) để phục vụ dedupe chéo chi nhánh (BA §8.1).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Trọng số tính số kiểm tra (checksum) của MST 10 chữ số theo Tổng cục Thuế Việt Nam
_TAX_CODE_WEIGHTS: tuple[int, ...] = (31, 29, 23, 19, 17, 13, 7, 5, 3)


@dataclass(frozen=True, slots=True)
class TaxCodeInfo:
    """Thông tin MST đã được chuẩn hóa và phân tích."""

    raw: str
    cleaned: str            # Chuỗi đã format: 10 số ("0123456789") hoặc 13 số ("0123456789-001")
    root_code: str         # 10 chữ số đầu (dùng cho dedupe)
    is_branch: bool        # True nếu là MST chi nhánh (13 số)
    is_valid_checksum: bool  # True nếu thuật toán checksum MST hợp lệ


def verify_tax_code_checksum(code10: str) -> bool:
    """
    Kiểm tra tính hợp lệ của số kiểm tra (chữ số thứ 10) trong MST 10 chữ số.
    Thuật toán chuẩn của Tổng cục Thuế VN:
      S = sum(d[i] * W[i] for i in 0..8)
      R = S % 11
      D10 = 10 - R (nếu 10 - R == 10 thì theo quy chuẩn sẽ không tạo ra MST này hoặc quy ước đặc biệt)
    """
    if len(code10) != 10 or not code10.isdigit():
        return False

    digits = [int(c) for c in code10]
    s = sum(digits[i] * _TAX_CODE_WEIGHTS[i] for i in range(9))
    r = s % 11
    expected_check_digit = 10 - r

    if expected_check_digit >= 10:
        # Trường hợp r == 0 hoặc 10, trong thực tế hệ số checksum trả về 0 hoặc bỏ qua
        return digits[9] == 0

    return digits[9] == expected_check_digit


def parse_and_validate_tax_code(raw: str | None) -> TaxCodeInfo | None:
    """
    Chuẩn hóa và kiểm tra mã số thuế.

    Trả về:
      - None nếu rỗng hoặc không phải định dạng MST hợp lệ, hoặc là CCCD 12 số (bị cấm).
      - `TaxCodeInfo` nếu hợp lệ.
    """
    if not raw:
        return None

    raw_clean = str(raw).strip()
    # Loại bỏ tiền tố "MST:", "Mã số thuế:", "Mã số DN:"
    raw_clean = re.sub(r"^(?:mst|mã số thuế|ma so thue|mã số dn|ma so dn)\s*[:.]?\s*", "", raw_clean, flags=re.IGNORECASE).strip()

    # Chỉ giữ lại chữ số
    digits = re.sub(r"\D", "", raw_clean)

    # 1. Chặn CCCD/Định danh cá nhân 12 số của hộ kinh doanh (BA §5.3)
    if len(digits) == 12:
        return None

    # 2. MST Doanh nghiệp 10 chữ số
    if len(digits) == 10:
        valid_checksum = verify_tax_code_checksum(digits)
        return TaxCodeInfo(
            raw=raw_clean,
            cleaned=digits,
            root_code=digits,
            is_branch=False,
            is_valid_checksum=valid_checksum,
        )

    # 3. MST Chi nhánh 13 chữ số (chuẩn hóa hiển thị XXXXXXXXXX-YYY)
    if len(digits) == 13:
        root = digits[:10]
        branch = digits[10:]
        formatted = f"{root}-{branch}"
        valid_checksum = verify_tax_code_checksum(root)
        return TaxCodeInfo(
            raw=raw_clean,
            cleaned=formatted,
            root_code=root,
            is_branch=True,
            is_valid_checksum=valid_checksum,
        )

    return None
