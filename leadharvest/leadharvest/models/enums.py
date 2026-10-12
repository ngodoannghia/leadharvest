"""
Các hằng số dạng Enum dùng chung trong toàn dự án LeadHarvest.

Mọi giá trị hiển thị (value) đều bám sát tài liệu BA (BA_baoBiHongHai.md) để
khi xuất file giao khách không cần map lại.
"""

from __future__ import annotations

from enum import Enum


class Segment(str, Enum):
    """
    Sáu phân khúc mục tiêu (BA §4).

    - `value` là tên hiển thị trên cột "Nhóm Ngành" và cũng là tên tab Excel.
    - Kế thừa `str` để so sánh trực tiếp với chuỗi và serialize JSON dễ dàng.
    """

    NONG_SAN = "Nông sản"
    DET_MAY = "Dệt may"
    THUY_SAN = "Thủy sản"
    PHAN_BON = "Phân bón"
    CAO_SU = "Cao su"
    CAY_TRONG = "Cây trồng"

    @property
    def slug(self) -> str:
        """Tên không dấu, dùng đặt tên file CSV (vd: `nong_san`)."""
        return self.name.lower()

    @property
    def min_quota(self) -> int:
        """Sản lượng sàn theo phân khúc (BA §2.1)."""
        return SEGMENT_MIN_QUOTA[self]

    @property
    def qa_sample_size(self) -> int:
        """Số dòng bốc mẫu kiểm tra phân loại khi nghiệm thu (BA §10.2)."""
        return SEGMENT_QA_SAMPLE[self]


# Thứ tự tab trong file giao khách = thứ tự bảng sản lượng tại BA §2.1.
SEGMENT_ORDER: tuple[Segment, ...] = (
    Segment.NONG_SAN,
    Segment.DET_MAY,
    Segment.THUY_SAN,
    Segment.PHAN_BON,
    Segment.CAO_SU,
    Segment.CAY_TRONG,
)

# BA §2.1 — Sản lượng tối thiểu theo phân khúc (tổng 4.300).
SEGMENT_MIN_QUOTA: dict[Segment, int] = {
    Segment.NONG_SAN: 1200,
    Segment.DET_MAY: 1200,
    Segment.THUY_SAN: 500,
    Segment.PHAN_BON: 500,
    Segment.CAO_SU: 400,
    Segment.CAY_TRONG: 500,
}

# BA §2.1 — Sản lượng sàn toàn dự án sau làm sạch + khử trùng.
TOTAL_MIN_QUOTA: int = 5000

# BA §7.3 — Tối thiểu 90% dòng bàn giao có ít nhất một số di động.
MIN_MOBILE_RATIO: float = 0.90

# BA §10.2 — Phân bổ 100 dòng mẫu kiểm tra phân loại.
SEGMENT_QA_SAMPLE: dict[Segment, int] = {
    Segment.NONG_SAN: 20,
    Segment.DET_MAY: 20,
    Segment.THUY_SAN: 15,
    Segment.PHAN_BON: 15,
    Segment.CAO_SU: 15,
    Segment.CAY_TRONG: 15,
}


class PhoneType(str, Enum):
    """
    Loại số điện thoại (BA §6, §7).

    - MOBILE   : di động 10 số, đầu 03/05/07/08/09.
    - LANDLINE : số bàn 11 số, đầu 02x (theo mã vùng mới từ 2017).
    - HOTLINE  : tổng đài 1800/1900 — CHỈ được phép nằm ở cột phụ.
    """

    MOBILE = "MOBILE"
    LANDLINE = "LANDLINE"
    HOTLINE = "HOTLINE"


# BA §6 — Cột "Loại SĐT Chính" chỉ nhận MOBILE hoặc LANDLINE.
PRIMARY_PHONE_TYPES: frozenset[PhoneType] = frozenset({PhoneType.MOBILE, PhoneType.LANDLINE})


class DataStatus(str, Enum):
    """
    Trạng thái dữ liệu (BA §6.1).

    Chỉ có một giá trị duy nhất được phép xuất trong file giao khách.
    Giá trị này KHÔNG cam kết cơ sở đang mở cửa tại thời điểm Sales gọi.
    """

    PUBLIC_VALID = "Công khai hợp lệ"


class RejectCategory(str, Enum):
    """
    Nhóm lý do loại bản ghi — khớp các chỉ số bắt buộc trong QA report (BA §9).
    """

    DUPLICATE = "trung_lap"
    MISSING_INFO = "thieu_thong_tin"
    WRONG_SEGMENT = "sai_nganh"
    INACTIVE = "ngung_hoat_dong"


class RejectReason(str, Enum):
    """
    Lý do chi tiết khiến một bản ghi bị loại hoặc một trường không đạt verify.

    Mỗi lý do được gom về một `RejectCategory` để thống kê trong QA report.
    Lý do chi tiết chỉ lưu nội bộ (BA §6.2), không xuất cho khách.
    """

    # --- Trùng lặp (BA §8) ---
    DUPLICATE_PHONE = "DUPLICATE_PHONE"            # trùng SĐT với bản ghi đã giữ
    DUPLICATE_TAX_CODE = "DUPLICATE_TAX_CODE"      # trùng MST gốc cùng tỉnh
    TAX_CODE_BRANCH_LIMIT = "TAX_CODE_BRANCH_LIMIT"  # vượt quá 2 chi nhánh khác tỉnh

    # --- Thiếu / sai thông tin (BA §3.2, §3.3, §7) ---
    MISSING_NAME = "MISSING_NAME"                  # không xác định được tên cơ sở
    MISSING_ADDRESS = "MISSING_ADDRESS"            # không có địa chỉ
    ADDRESS_NOT_SPECIFIC = "ADDRESS_NOT_SPECIFIC"  # địa chỉ quá chung chung
    MISSING_PROVINCE = "MISSING_PROVINCE"          # không xác định được tỉnh/thành
    NO_VALID_PHONE = "NO_VALID_PHONE"              # không có SĐT hợp lệ nào
    HOTLINE_ONLY = "HOTLINE_ONLY"                  # chỉ có 1800/1900 -> không có cột chính
    INVALID_PHONE = "INVALID_PHONE"                # SĐT sai định dạng / sai loại
    INVALID_TAX_CODE = "INVALID_TAX_CODE"          # MST sai định dạng / sai checksum
    INVALID_FIELD = "INVALID_FIELD"                # lỗi schema khác (status, contact...)

    # --- Sai ngành (BA §3.2, §4) ---
    WRONG_SEGMENT = "WRONG_SEGMENT"                # không khớp phân khúc nào
    EXCLUDED_KEYWORD = "EXCLUDED_KEYWORD"          # dính từ khóa loại trừ (bán lẻ, quán ăn...)

    # --- Ngừng hoạt động (BA §2.3) ---
    INACTIVE = "INACTIVE"                          # giải thể / ngừng hoạt động / đóng cửa

    @property
    def category(self) -> RejectCategory:
        """Gom lý do chi tiết về nhóm thống kê của QA report."""
        return _REASON_CATEGORY[self]


_REASON_CATEGORY: dict[RejectReason, RejectCategory] = {
    RejectReason.DUPLICATE_PHONE: RejectCategory.DUPLICATE,
    RejectReason.DUPLICATE_TAX_CODE: RejectCategory.DUPLICATE,
    RejectReason.TAX_CODE_BRANCH_LIMIT: RejectCategory.DUPLICATE,
    RejectReason.MISSING_NAME: RejectCategory.MISSING_INFO,
    RejectReason.MISSING_ADDRESS: RejectCategory.MISSING_INFO,
    RejectReason.ADDRESS_NOT_SPECIFIC: RejectCategory.MISSING_INFO,
    RejectReason.MISSING_PROVINCE: RejectCategory.MISSING_INFO,
    RejectReason.NO_VALID_PHONE: RejectCategory.MISSING_INFO,
    RejectReason.HOTLINE_ONLY: RejectCategory.MISSING_INFO,
    RejectReason.INVALID_PHONE: RejectCategory.MISSING_INFO,
    RejectReason.INVALID_TAX_CODE: RejectCategory.MISSING_INFO,
    RejectReason.INVALID_FIELD: RejectCategory.MISSING_INFO,
    RejectReason.WRONG_SEGMENT: RejectCategory.WRONG_SEGMENT,
    RejectReason.EXCLUDED_KEYWORD: RejectCategory.WRONG_SEGMENT,
    RejectReason.INACTIVE: RejectCategory.INACTIVE,
}
