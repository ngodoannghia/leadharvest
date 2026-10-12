"""
SCHEMA FILE BÀN GIAO CHÍNH THỨC — LEADOUTPUT (BA §6)

Đặc tả:
  File Google Sheets và file Excel/CSV bàn giao cho khách hàng (Bao Bì Hồng Hải)
  bắt buộc phải gồm đúng 11 cột theo đúng thứ tự sau.
  Class này chịu trách nhiệm:
    1. Định nghĩa chuẩn 11 trường dữ liệu xuất cho khách hàng.
    2. Thực thi toàn bộ các logic kiểm tra (Validation rules) nghiêm ngặt từ BA.
    3. Cung cấp hàm tính điểm chất lượng bản ghi (Richness Score) để chọn bản ghi tối ưu khi khử trùng lặp.
    4. Xuất dòng dữ liệu với header tiếng Việt chuẩn quy định.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from leadharvest.models.enums import (
    DataStatus,
    PhoneType,
    PRIMARY_PHONE_TYPES,
    RejectReason,
    Segment,
)
from leadharvest.validators import phone as phone_validator
from leadharvest.validators.province import CANONICAL_PROVINCES
from leadharvest.validators.tax_code import parse_and_validate_tax_code
from leadharvest.validators.text import (
    clean_whitespace,
    is_placeholder,
    is_specific_address,
)


@dataclass(frozen=True, slots=True)
class ValidationError:
    """Chi tiết một lỗi kiểm tra dữ liệu của bản ghi."""

    field_name: str         # Tên trường bị lỗi (vd: 'phone_primary', 'address')
    reason: RejectReason    # Mã lý do theo quy chuẩn thống kê QA Report
    message: str            # Mô tả chi tiết lỗi bằng tiếng Việt


@dataclass
class LeadOutput:
    """
    Class đại diện cho 1 dòng dữ liệu bàn giao hoàn chỉnh (BA §6).
    
    Tất cả các trường dữ liệu ở đây là trường công khai đã qua chuẩn hóa,
    tuyệt đối không chứa URL cào, tên nguồn hay checkpoint kỹ thuật nội bộ.
    """

    # -------------------------------------------------------------------------
    # 1. Nhóm Ngành (target_segment) - BẮT BUỘC
    # Thuộc 1 trong 6 phân khúc: Nông sản, Thủy sản, Cao su, Dệt may, Phân bón, Cây trồng.
    # -------------------------------------------------------------------------
    target_segment: str

    # -------------------------------------------------------------------------
    # 2. Tên Doanh Nghiệp / Cơ Sở (company_name) - BẮT BUỘC
    # Tên pháp nhân, HTX, hộ kinh doanh hoặc tên cơ sở rõ ràng; đã bỏ khoảng trắng thừa.
    # -------------------------------------------------------------------------
    company_name: str

    # -------------------------------------------------------------------------
    # 3. Người Đại Diện / Chủ Cơ Sở (contact_person) - TÙY CHỌN
    # Họ tên người đại diện pháp luật hoặc chủ cơ sở nếu nguồn công khai có cung cấp.
    # -------------------------------------------------------------------------
    contact_person: str | None = None

    # -------------------------------------------------------------------------
    # 4. Số Điện Thoại Chính (phone_primary) - BẮT BUỘC (100% dòng bàn giao)
    # Ưu tiên số di động để Sales dùng cho Zalo/Telesales. Nếu không có di động
    # thì dùng số bàn hợp lệ.
    # -------------------------------------------------------------------------
    phone_primary: str = ""

    # -------------------------------------------------------------------------
    # 5. Loại SĐT Chính (phone_primary_type) - BẮT BUỘC
    # Chỉ nhận giá trị 'MOBILE' hoặc 'LANDLINE'. Tuyệt đối KHÔNG dùng 'HOTLINE' ở cột này.
    # -------------------------------------------------------------------------
    phone_primary_type: str = ""

    # -------------------------------------------------------------------------
    # 6. Số Điện Thoại Phụ (phone_secondary) - TÙY CHỌN
    # Số bàn, hotline 1800/1900 hoặc số di động thứ hai hợp lệ.
    # -------------------------------------------------------------------------
    phone_secondary: str | None = None

    # -------------------------------------------------------------------------
    # 7. Loại SĐT Phụ (phone_secondary_type) - TÙY CHỌN
    # Nhận một trong các giá trị: 'LANDLINE', 'HOTLINE', 'MOBILE' hoặc None nếu không có số phụ.
    # -------------------------------------------------------------------------
    phone_secondary_type: str | None = None

    # -------------------------------------------------------------------------
    # 8. Mã Số Thuế (tax_code) - TÙY CHỌN
    # MST 10 chữ số hoặc MST chi nhánh (10-3). Để trống nếu cơ sở không có MST.
    # Tuyệt đối không lưu CCCD/Định danh cá nhân 12 số của hộ kinh doanh.
    # -------------------------------------------------------------------------
    tax_code: str | None = None

    # -------------------------------------------------------------------------
    # 9. Tỉnh / Thành Phố (province) - BẮT BUỘC
    # Tỉnh/thành phố của địa chỉ thực tế nơi xưởng/kho/vườn ươm hoạt động.
    # -------------------------------------------------------------------------
    province: str = ""

    # -------------------------------------------------------------------------
    # 10. Địa Chỉ Chi Tiết (address) - BẮT BUỘC
    # Địa chỉ chi tiết xưởng, kho, vựa, vườn ươm hoặc cơ sở sản xuất hoạt động thực tế.
    # -------------------------------------------------------------------------
    address: str = ""

    # -------------------------------------------------------------------------
    # 11. Trạng Thái Dữ Liệu (data_status) - BẮT BUỘC
    # Giá trị mặc định duy nhất: 'Công khai hợp lệ' (BA §6.1).
    # -------------------------------------------------------------------------
    data_status: str = DataStatus.PUBLIC_VALID.value

    # =========================================================================
    # DANH SÁCH 11 CỘT HIỂN THỊ TIẾNG VIỆT THEO THỨ TỰ BẮT BUỘC (BA §6)
    # =========================================================================
    COLUMN_HEADERS: tuple[str, ...] = (
        "Nhóm Ngành",
        "Tên Doanh Nghiệp / Cơ Sở",
        "Người Đại Diện / Chủ Cơ Sở",
        "Số Điện Thoại Chính",
        "Loại SĐT Chính",
        "Số Điện Thoại Phụ",
        "Loại SĐT Phụ",
        "Mã Số Thuế",
        "Tỉnh / Thành Phố",
        "Địa Chỉ Chi Tiết",
        "Trạng Thái Dữ Liệu",
    )

    # =========================================================================
    # CÁC LOGIC VERIFY CHI TIẾT (TỔNG HỢP KIỂM TRA TỪNG TRƯỜNG)
    # =========================================================================

    def validate_target_segment(self) -> list[ValidationError]:
        """
        Verify cột 1: Nhóm Ngành.
        - Bắt buộc phải là 1 trong 6 phân khúc được định nghĩa trong BA §4.
        """
        errors: list[ValidationError] = []
        valid_segments = {s.value for s in Segment}
        if not self.target_segment or self.target_segment not in valid_segments:
            errors.append(
                ValidationError(
                    field_name="target_segment",
                    reason=RejectReason.WRONG_SEGMENT,
                    message=f"Nhóm ngành '{self.target_segment}' không hợp lệ. Phải thuộc 1 trong 6 ngành: {list(valid_segments)}",
                )
            )
        return errors

    def validate_company_name(self) -> list[ValidationError]:
        """
        Verify cột 2: Tên Doanh Nghiệp / Cơ Sở.
        - Không được để trống.
        - Không được là giá trị giữ chỗ (như 'Đang cập nhật', 'None', '-').
        - Độ dài tối thiểu phải từ 3 ký tự trở lên.
        """
        errors: list[ValidationError] = []
        name = clean_whitespace(self.company_name)
        if not name or is_placeholder(name) or len(name) < 3:
            errors.append(
                ValidationError(
                    field_name="company_name",
                    reason=RejectReason.MISSING_NAME,
                    message=f"Tên doanh nghiệp/cơ sở không hợp lệ hoặc bị trống: '{self.company_name}'",
                )
            )
        return errors

    def validate_phones(self) -> list[ValidationError]:
        """
        Verify cột 4, 5, 6, 7: Số điện thoại chính, phụ và loại tương ứng (BA §7).
        - 100% dòng bắt buộc phải có Số Điện Thoại Chính (phone_primary).
        - Loại SĐT Chính chỉ được phép là 'MOBILE' hoặc 'LANDLINE'.
        - Cột chính KHÔNG ĐƯỢC PHÉP là 'HOTLINE' (1800/1900).
        - Số chính phải đúng cú pháp: Mobile 10 số (03/05/07/08/09), Landline 11 số (02x).
        - Số phụ (nếu có): phải hợp lệ (Mobile, Landline, Hotline) và không được trùng với số chính.
        - Loại SĐT phụ phải khớp với số phụ.
        - Không được là số rác (toàn số 0, dãy tuần tự tăng giảm).
        """
        errors: list[ValidationError] = []

        # 1. Kiểm tra SĐT chính
        p_num = clean_whitespace(self.phone_primary)
        p_type = clean_whitespace(self.phone_primary_type).upper()

        if not p_num:
            errors.append(
                ValidationError(
                    field_name="phone_primary",
                    reason=RejectReason.NO_VALID_PHONE,
                    message="Bắt buộc phải có Số Điện Thoại Chính hợp lệ.",
                )
            )
            return errors

        # Phân loại SĐT chính theo định dạng thực tế
        detected_p_type = phone_validator.classify_phone(p_num)
        if not detected_p_type:
            errors.append(
                ValidationError(
                    field_name="phone_primary",
                    reason=RejectReason.INVALID_PHONE,
                    message=f"Số điện thoại chính '{p_num}' không đúng định dạng chuẩn hoặc là số rác.",
                )
            )
        elif detected_p_type.value not in {t.value for t in PRIMARY_PHONE_TYPES}:
            # BA cấm HOTLINE ở cột chính
            errors.append(
                ValidationError(
                    field_name="phone_primary_type",
                    reason=RejectReason.HOTLINE_ONLY,
                    message=f"SĐT chính không được là HOTLINE ({p_num}). Chỉ chấp nhận MOBILE hoặc LANDLINE.",
                )
            )
        elif detected_p_type.value != p_type:
            errors.append(
                ValidationError(
                    field_name="phone_primary_type",
                    reason=RejectReason.INVALID_FIELD,
                    message=f"Loại SĐT chính khai báo '{p_type}' không khớp với số thực tế ({detected_p_type.value}).",
                )
            )

        # 2. Kiểm tra SĐT phụ (nếu có)
        s_num = clean_whitespace(self.phone_secondary) if self.phone_secondary else None
        s_type = clean_whitespace(self.phone_secondary_type).upper() if self.phone_secondary_type else None

        if s_num:
            # SĐT phụ không được trùng với SĐT chính
            if s_num == p_num:
                errors.append(
                    ValidationError(
                        field_name="phone_secondary",
                        reason=RejectReason.DUPLICATE_PHONE,
                        message=f"SĐT phụ trùng lặp với SĐT chính ({s_num}).",
                    )
                )

            detected_s_type = phone_validator.classify_phone(s_num)
            if not detected_s_type:
                errors.append(
                    ValidationError(
                        field_name="phone_secondary",
                        reason=RejectReason.INVALID_PHONE,
                        message=f"Số điện thoại phụ '{s_num}' không hợp lệ hoặc là số rác.",
                    )
                )
            elif not s_type or detected_s_type.value != s_type:
                errors.append(
                    ValidationError(
                        field_name="phone_secondary_type",
                        reason=RejectReason.INVALID_FIELD,
                        message=f"Loại SĐT phụ khai báo '{s_type}' không khớp với số phụ thực tế ({detected_s_type.value if detected_s_type else 'None'}).",
                    )
                )
        elif s_type:
            errors.append(
                ValidationError(
                    field_name="phone_secondary_type",
                    reason=RejectReason.INVALID_FIELD,
                    message=f"Khai báo loại SĐT phụ '{s_type}' nhưng không có số điện thoại phụ.",
                )
            )

        return errors

    def validate_tax_code(self) -> list[ValidationError]:
        """
        Verify cột 8: Mã Số Thuế (Tùy chọn nhưng nếu có phải chuẩn).
        - MST doanh nghiệp: 10 chữ số.
        - MST chi nhánh: 13 chữ số (chuẩn hóa hiển thị dạng 10-3).
        - Tuyệt đối cấm số CCCD 12 số của hộ kinh doanh cá thể (BA §5.3).
        """
        errors: list[ValidationError] = []
        if not self.tax_code or is_placeholder(self.tax_code):
            return errors

        clean_tax = clean_whitespace(self.tax_code)
        parsed = parse_and_validate_tax_code(clean_tax)
        if not parsed:
            errors.append(
                ValidationError(
                    field_name="tax_code",
                    reason=RejectReason.INVALID_TAX_CODE,
                    message=f"Mã số thuế '{self.tax_code}' không hợp lệ hoặc vi phạm quy định CCCD 12 số.",
                )
            )
        return errors

    def validate_province(self) -> list[ValidationError]:
        """
        Verify cột 9: Tỉnh / Thành Phố.
        - Bắt buộc phải có.
        - Phải thuộc danh mục Tỉnh/Thành phố chuẩn của Việt Nam.
        """
        errors: list[ValidationError] = []
        prov = clean_whitespace(self.province)
        if not prov or is_placeholder(prov):
            errors.append(
                ValidationError(
                    field_name="province",
                    reason=RejectReason.MISSING_PROVINCE,
                    message="Bắt buộc phải có Tỉnh / Thành Phố.",
                )
            )
        elif prov not in CANONICAL_PROVINCES:
            errors.append(
                ValidationError(
                    field_name="province",
                    reason=RejectReason.MISSING_PROVINCE,
                    message=f"Tên tỉnh/thành phố '{prov}' chưa được chuẩn hóa theo quy ước chính thức.",
                )
            )
        return errors

    def validate_address(self) -> list[ValidationError]:
        """
        Verify cột 10: Địa Chỉ Chi Tiết (BA §3.2).
        - Bắt buộc phải có.
        - Phải có dấu hiệu địa chỉ cơ sở cụ thể (xã/phường/ấp/đường/lô/KCN...),
          không chấp nhận chỉ ghi mỗi tên Tỉnh hoặc 'Việt Nam'.
        """
        errors: list[ValidationError] = []
        addr = clean_whitespace(self.address)
        if not addr or is_placeholder(addr):
            errors.append(
                ValidationError(
                    field_name="address",
                    reason=RejectReason.MISSING_ADDRESS,
                    message="Bắt buộc phải có Địa Chỉ Chi Tiết của cơ sở.",
                )
            )
        elif not is_specific_address(addr):
            errors.append(
                ValidationError(
                    field_name="address",
                    reason=RejectReason.ADDRESS_NOT_SPECIFIC,
                    message=f"Địa chỉ '{addr}' quá chung chung, thiếu thông tin cấp xã/phường/đường/KCN cụ thể.",
                )
            )
        return errors

    def validate_data_status(self) -> list[ValidationError]:
        """
        Verify cột 11: Trạng Thái Dữ Liệu (BA §6.1).
        - Giá trị duy nhất bắt buộc là 'Công khai hợp lệ'.
        """
        errors: list[ValidationError] = []
        if self.data_status != DataStatus.PUBLIC_VALID.value:
            errors.append(
                ValidationError(
                    field_name="data_status",
                    reason=RejectReason.INVALID_FIELD,
                    message=f"Trạng thái dữ liệu phải là '{DataStatus.PUBLIC_VALID.value}', hiện tại là '{self.data_status}'.",
                )
            )
        return errors

    # =========================================================================
    # HÀM VALIDATE TỔNG THỂ
    # =========================================================================

    def validate(self) -> list[ValidationError]:
        """
        Thực hiện toàn bộ các logic kiểm tra trên bản ghi.
        Trả về danh sách tất cả các lỗi vi phạm (nếu có).
        Bản ghi hoàn toàn hợp lệ khi danh sách trả về rỗng.
        """
        all_errors: list[ValidationError] = []
        all_errors.extend(self.validate_target_segment())
        all_errors.extend(self.validate_company_name())
        all_errors.extend(self.validate_phones())
        all_errors.extend(self.validate_tax_code())
        all_errors.extend(self.validate_province())
        all_errors.extend(self.validate_address())
        all_errors.extend(self.validate_data_status())
        return all_errors

    @property
    def is_valid(self) -> bool:
        """True nếu bản ghi vượt qua 100% các tiêu chí nghiệm thu."""
        return len(self.validate()) == 0

    # =========================================================================
    # CÁC TIỆN ÍCH DÙNG CHO DEDUPLICATION & PHÂN TÍCH
    # =========================================================================

    @property
    def has_mobile(self) -> bool:
        """Kiểm tra bản ghi có ít nhất 1 số di động ở cột chính hoặc cột phụ (BA §7.3)."""
        return (
            self.phone_primary_type == PhoneType.MOBILE.value
            or (self.phone_secondary_type == PhoneType.MOBILE.value if self.phone_secondary_type else False)
        )

    @property
    def root_tax_code(self) -> str | None:
        """Lấy 10 chữ số gốc của MST (dùng để dedupe doanh nghiệp và các chi nhánh)."""
        if not self.tax_code:
            return None
        parsed = parse_and_validate_tax_code(self.tax_code)
        return parsed.root_code if parsed else None

    def all_phones(self) -> list[str]:
        """Trả về toàn bộ số điện thoại có trong bản ghi (chính + phụ)."""
        res: list[str] = []
        if self.phone_primary:
            res.append(self.phone_primary)
        if self.phone_secondary:
            res.append(self.phone_secondary)
        return res

    def richness_score(self) -> int:
        """
        Tính điểm độ 'giàu thông tin' của bản ghi để ưu tiên giữ lại khi trùng lặp (BA §8.1).
        
        Thang điểm ưu tiên:
          + 50 điểm: Có SĐT chính là di động (cực kỳ quan trọng cho Sales Zalo)
          + 20 điểm: Có người đại diện/chủ cơ sở rõ ràng
          + 20 điểm: Có Mã số thuế hợp lệ
          + 15 điểm: Có thêm SĐT phụ
          + 10 điểm: Địa chỉ chi tiết, rõ ràng (càng dài & đầy đủ càng cao)
        """
        score = 0
        if self.phone_primary_type == PhoneType.MOBILE.value:
            score += 50
        elif self.phone_secondary_type == PhoneType.MOBILE.value:
            score += 25

        if self.contact_person and not is_placeholder(self.contact_person):
            score += 20

        if self.tax_code and not is_placeholder(self.tax_code):
            score += 20

        if self.phone_secondary:
            score += 15

        if self.address:
            score += min(len(self.address) // 5, 15)

        return score

    # =========================================================================
    # XUẤT RA DÒNG DỮ LIỆU ĐỂ GHI EXCEL / CSV
    # =========================================================================

    def to_row(self) -> tuple[Any, ...]:
        """
        Xuất ra tuple 11 phần tử theo đúng thứ tự cột hiển thị của BA §6:
        (Nhóm Ngành, Tên Cty, Người Đại Diện, SĐT Chính, Loại SĐT Chính,
         SĐT Phụ, Loại SĐT Phụ, MST, Tỉnh/Thành, Địa Chỉ, Trạng Thái)
        """
        return (
            self.target_segment,
            self.company_name,
            self.contact_person or "",
            self.phone_primary,
            self.phone_primary_type,
            self.phone_secondary or "",
            self.phone_secondary_type or "",
            self.tax_code or "",
            self.province,
            self.address,
            self.data_status,
        )

    def to_dict(self) -> dict[str, Any]:
        """Chuyển đổi thành từ điển có key là tên cột hiển thị tiếng Việt."""
        return dict(zip(self.COLUMN_HEADERS, self.to_row()))
