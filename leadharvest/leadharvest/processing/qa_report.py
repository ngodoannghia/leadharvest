"""
Báo cáo chất lượng dữ liệu QA Report (BA §9).

Tính toán và tạo báo cáo `qa_report.json` hoặc dữ liệu tab `Thong_Ke` theo đầy đủ
các tiêu chí bắt buộc trong BA §9 và kiểm tra ngưỡng nghiệm thu (BA §10.1).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from leadharvest.models.enums import (
    MIN_MOBILE_RATIO,
    PhoneType,
    RejectCategory,
    RejectReason,
    Segment,
    SEGMENT_MIN_QUOTA,
    TOTAL_MIN_QUOTA,
)
from leadharvest.models.lead_output import LeadOutput


@dataclass
class QAReport:
    """Cấu trúc dữ liệu báo cáo chất lượng theo BA §9."""

    # 1. Thống kê sản lượng đầu vào và phân loại loại trừ
    total_raw_records: int
    rejected_duplicates: int
    rejected_missing_info: int
    rejected_wrong_segment: int
    rejected_inactive: int
    total_rejected: int

    # 2. Sản lượng bàn giao
    total_delivered_records: int
    segment_counts: dict[str, int]

    # 3. Thống kê điện thoại
    total_with_mobile: int
    total_with_landline: int
    total_with_hotline: int
    mobile_ratio_pct: float
    valid_phone_ratio_pct: float

    # 4. Đánh giá tiêu chí nghiệm thu (BA §10.1)
    is_total_quota_passed: bool
    is_segment_quota_passed: bool
    is_mobile_ratio_passed: bool
    is_valid_phone_passed: bool
    is_overall_passed: bool

    # 5. Chi tiết lý do loại bỏ
    rejection_details: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        """Xuất báo cáo sang định dạng dict / JSON."""
        return asdict(self)

    def to_json(self, indent: int = 4) -> str:
        """Xuất chuỗi JSON tiếng Việt đẹp mắt."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


def generate_qa_report(
    total_raw: int,
    delivered_leads: list[LeadOutput],
    all_rejected: list[tuple[Any, RejectReason, str]],
) -> QAReport:
    """
    Tổng hợp toàn bộ số liệu và sinh đối tượng QAReport hoàn chỉnh.
    """
    total_delivered = len(delivered_leads)

    # Đếm theo nhóm lý do loại bỏ (RejectCategory)
    cat_counts: dict[RejectCategory, int] = {cat: 0 for cat in RejectCategory}
    rejection_details: dict[str, int] = {}

    for _, reason, _ in all_rejected:
        cat_counts[reason.category] = cat_counts.get(reason.category, 0) + 1
        rejection_details[reason.value] = rejection_details.get(reason.value, 0) + 1

    # Thống kê theo 6 tab ngành
    segment_counts: dict[str, int] = {s.value: 0 for s in Segment}
    for lead in delivered_leads:
        segment_counts[lead.target_segment] = segment_counts.get(lead.target_segment, 0) + 1

    # Thống kê loại số điện thoại
    with_mobile = sum(1 for lead in delivered_leads if lead.has_mobile)
    with_landline = sum(
        1
        for lead in delivered_leads
        if lead.phone_primary_type == PhoneType.LANDLINE.value or lead.phone_secondary_type == PhoneType.LANDLINE.value
    )
    with_hotline = sum(
        1 for lead in delivered_leads if lead.phone_secondary_type == PhoneType.HOTLINE.value
    )

    mobile_ratio = (with_mobile / total_delivered * 100.0) if total_delivered > 0 else 0.0
    valid_phone_ratio = 100.0 if total_delivered > 0 else 0.0

    # Đánh giá tiêu chí nghiệm thu (BA §10.1)
    is_total_passed = total_delivered >= TOTAL_MIN_QUOTA
    is_seg_passed = all(
        segment_counts.get(s.value, 0) >= SEGMENT_MIN_QUOTA[s] for s in Segment
    )
    is_mob_passed = (mobile_ratio / 100.0) >= MIN_MOBILE_RATIO
    is_phone_passed = valid_phone_ratio == 100.0

    is_overall = is_total_passed and is_seg_passed and is_mob_passed and is_phone_passed

    return QAReport(
        total_raw_records=total_raw,
        rejected_duplicates=cat_counts[RejectCategory.DUPLICATE],
        rejected_missing_info=cat_counts[RejectCategory.MISSING_INFO],
        rejected_wrong_segment=cat_counts[RejectCategory.WRONG_SEGMENT],
        rejected_inactive=cat_counts[RejectCategory.INACTIVE],
        total_rejected=len(all_rejected),
        total_delivered_records=total_delivered,
        segment_counts=segment_counts,
        total_with_mobile=with_mobile,
        total_with_landline=with_landline,
        total_with_hotline=with_hotline,
        mobile_ratio_pct=round(mobile_ratio, 2),
        valid_phone_ratio_pct=round(valid_phone_ratio, 2),
        is_total_quota_passed=is_total_passed,
        is_segment_quota_passed=is_seg_passed,
        is_mobile_ratio_passed=is_mob_passed,
        is_valid_phone_passed=is_phone_passed,
        is_overall_passed=is_overall,
        rejection_details=rejection_details,
    )
