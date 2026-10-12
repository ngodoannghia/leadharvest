"""
Chuẩn hóa dữ liệu từ RawLead sang LeadOutput (BA §6, §7).

Quy trình:
  1. Kiểm tra trạng thái hoạt động: Loại bỏ doanh nghiệp giải thể / ngừng hoạt động.
  2. Chuẩn hóa tên cơ sở: Loại bỏ khoảng trắng thừa, kiểm tra tính hợp lệ.
  3. Phân loại ngành (Segment): Quét từ khóa tích cực và từ khóa loại trừ.
  4. Chuẩn hóa địa chỉ & Tỉnh/Thành: Nhận diện tỉnh từ địa chỉ nếu cột tỉnh thiếu.
  5. Trích xuất và gán Số điện thoại chính / phụ theo quy tắc ưu tiên di động (BA §7.2).
  6. Chuẩn hóa Mã số thuế và Người đại diện.
  7. Khởi tạo đối tượng `LeadOutput` và chạy hàm `validate()`.
"""

from __future__ import annotations

from dataclasses import dataclass
from leadharvest.models.enums import DataStatus, PhoneType, RejectReason, Segment
from leadharvest.models.lead_output import LeadOutput
from leadharvest.models.raw_lead import RawLead
from leadharvest.validators.phone import assign_primary_secondary, extract_phones
from leadharvest.validators.province import (
    detect_province_from_address,
    normalize_province_name,
)
from leadharvest.validators.segment import (
    classify_text_to_segment,
    is_record_inactive,
)
from leadharvest.validators.tax_code import parse_and_validate_tax_code
from leadharvest.validators.text import (
    clean_whitespace,
    is_placeholder,
    is_specific_address,
    normalize_company_name,
    normalize_person_name,
)


@dataclass(frozen=True, slots=True)
class NormalizationResult:
    """Kết quả chuẩn hóa 1 bản ghi thô."""

    lead: LeadOutput | None
    reject_reason: RejectReason | None
    reject_message: str | None


def normalize_raw_lead(raw: RawLead) -> NormalizationResult:
    """
    Chuyển đổi một bản ghi thô `RawLead` thành `LeadOutput` hoàn chỉnh.
    Nếu dữ liệu không đạt yêu cầu, trả về lý do loại bỏ (RejectReason).
    """
    # 1. Kiểm tra trạng thái giải thể / ngừng hoạt động (BA §2.3)
    text_corpus = f"{raw.company_name} {raw.description or ''} {raw.address or ''}"
    if is_record_inactive(text_corpus):
        return NormalizationResult(
            lead=None,
            reject_reason=RejectReason.INACTIVE,
            reject_message="Cơ sở được ghi nhận đã giải thể hoặc ngừng hoạt động.",
        )

    # 2. Chuẩn hóa tên doanh nghiệp / cơ sở (BA §6 cột 2)
    company_name = normalize_company_name(raw.company_name)
    if not company_name or is_placeholder(company_name) or len(company_name) < 3:
        return NormalizationResult(
            lead=None,
            reject_reason=RejectReason.MISSING_NAME,
            reject_message="Tên cơ sở bị thiếu hoặc không hợp lệ.",
        )

    # 3. Phân loại ngành hàng (BA §4)
    # Xác định default segment từ raw lead nếu có
    default_seg: Segment | None = None
    if raw.target_segment:
        for s in Segment:
            if s.value.lower() == raw.target_segment.strip().lower() or s.name.lower() == raw.target_segment.strip().lower():
                default_seg = s
                break

    classified_segment, segment_errors = classify_text_to_segment(
        name=company_name,
        description=raw.description or "",
        default_segment=default_seg,
    )
    if not classified_segment:
        return NormalizationResult(
            lead=None,
            reject_reason=RejectReason.EXCLUDED_KEYWORD if any("loại trừ" in e for e in segment_errors) else RejectReason.WRONG_SEGMENT,
            reject_message="; ".join(segment_errors),
        )

    # 4. Chuẩn hóa Tỉnh / Thành phố và Địa chỉ (BA §2.2, §6 cột 9-10)
    address = clean_whitespace(raw.address)
    if not address or is_placeholder(address):
        return NormalizationResult(
            lead=None,
            reject_reason=RejectReason.MISSING_ADDRESS,
            reject_message="Không có địa chỉ cơ sở.",
        )

    if not is_specific_address(address):
        return NormalizationResult(
            lead=None,
            reject_reason=RejectReason.ADDRESS_NOT_SPECIFIC,
            reject_message=f"Địa chỉ quá chung chung: '{address}'",
        )

    province = normalize_province_name(raw.province)
    if not province:
        province = detect_province_from_address(address)

    if not province:
        return NormalizationResult(
            lead=None,
            reject_reason=RejectReason.MISSING_PROVINCE,
            reject_message="Không xác định được Tỉnh / Thành phố của cơ sở.",
        )

    # 5. Chuẩn hóa và gán Số điện thoại chính / phụ (BA §7)
    raw_phones = raw.get_all_raw_phones()
    phones = extract_phones(raw_phones)
    if not phones:
        return NormalizationResult(
            lead=None,
            reject_reason=RejectReason.NO_VALID_PHONE,
            reject_message="Không có bất kỳ số điện thoại hợp lệ nào.",
        )

    p_phone, s_phone = assign_primary_secondary(phones)
    if not p_phone:
        # Trường hợp chỉ có hotline 1800/1900 nhưng BA cấm hotline ở cột chính
        return NormalizationResult(
            lead=None,
            reject_reason=RejectReason.HOTLINE_ONLY,
            reject_message="Bản ghi chỉ có số Hotline (1800/1900), không có số di động hoặc số bàn làm SĐT chính.",
        )

    # 6. Chuẩn hóa Mã số thuế và Người đại diện
    tax_info = parse_and_validate_tax_code(raw.tax_code)
    cleaned_tax = tax_info.cleaned if tax_info else None

    cleaned_contact = normalize_person_name(raw.contact_person) if raw.contact_person else None
    if cleaned_contact and is_placeholder(cleaned_contact):
        cleaned_contact = None

    # 7. Khởi tạo LeadOutput
    lead = LeadOutput(
        target_segment=classified_segment.value,
        company_name=company_name,
        contact_person=cleaned_contact,
        phone_primary=p_phone.number,
        phone_primary_type=p_phone.type.value,
        phone_secondary=s_phone.number if s_phone else None,
        phone_secondary_type=s_phone.type.value if s_phone else None,
        tax_code=cleaned_tax,
        province=province,
        address=address,
        data_status=DataStatus.PUBLIC_VALID.value,
    )

    # 8. Thực thi validation tổng thể cuối cùng
    errors = lead.validate()
    if errors:
        first_err = errors[0]
        return NormalizationResult(
            lead=None,
            reject_reason=first_err.reason,
            reject_message=first_err.message,
        )

    return NormalizationResult(
        lead=lead,
        reject_reason=None,
        reject_message=None,
    )
