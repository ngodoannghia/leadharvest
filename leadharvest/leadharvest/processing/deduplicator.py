"""
Khử trùng lặp đa nguồn & đa phân khúc (Cross-Tab Deduplication) (BA §8).

Quy tắc nghiệp vụ:
  1. Theo Mã số thuế (BA §8.1):
     - Cùng MST 10 số gốc và cùng Tỉnh/Thành: Gộp làm 1 bản ghi (chọn bản ghi có richness_score cao nhất).
     - Cùng MST nhưng khác Tỉnh/Thành và có SĐT riêng: Cho phép tối đa 2 chi nhánh đại diện.
  2. Theo Số điện thoại (BA §8.2, §8.3):
     - Tuyệt đối không để 2 dòng trong toàn bộ file (dù cùng hay khác tab) dùng chung bất kỳ SĐT nào
       (áp dụng cho cả phone_primary và phone_secondary).
  3. Thứ tự ưu tiên (BA §8.1):
     - Ưu tiên bản ghi có điểm thông tin (richness_score) cao nhất: Có di động > Có người liên hệ > Địa chỉ chi tiết.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from leadharvest.models.enums import RejectReason
from leadharvest.models.lead_output import LeadOutput


@dataclass(frozen=True, slots=True)
class DeduplicationResult:
    """Kết quả khử trùng lặp."""

    accepted_leads: list[LeadOutput]
    duplicate_leads: list[tuple[LeadOutput, RejectReason, str]]


def deduplicate_leads(leads: Iterable[LeadOutput]) -> DeduplicationResult:
    """
    Khử trùng lặp toàn bộ danh sách LeadOutput theo quy tắc BA §8.

    Quy trình:
      1. Sắp xếp danh sách theo điểm chất lượng `richness_score()` giảm dần
         (đảm bảo bản ghi giàu thông tin nhất luôn được duyệt và giữ lại trước).
      2. Duyệt từng bản ghi:
         - Kiểm tra SĐT có trùng với bất kỳ bản ghi nào đã nhận trước đó không (cả chính lẫn phụ).
         - Kiểm tra MST gốc:
           + Cùng MST và cùng tỉnh -> Trùng lặp (DUPLICATE_TAX_CODE).
           + Cùng MST khác tỉnh -> Cho phép tối đa 2 cơ sở (TAX_CODE_BRANCH_LIMIT nếu > 2).
         - Nếu đạt tất cả điều kiện -> Thêm vào accepted_leads.
    """
    # 1. Sắp xếp ưu tiên bản ghi có chất lượng cao nhất
    sorted_leads = sorted(leads, key=lambda x: x.richness_score(), reverse=True)

    accepted_leads: list[LeadOutput] = []
    duplicate_leads: list[tuple[LeadOutput, RejectReason, str]] = []

    # Bộ theo dõi các SĐT đã được sử dụng trên toàn hệ thống (cross-tab)
    seen_phones: set[str] = set()

    # Bộ theo dõi các chi nhánh theo MST gốc 10 số: root_tax_code -> list[LeadOutput]
    tax_code_branches: dict[str, list[LeadOutput]] = {}

    for lead in sorted_leads:
        lead_phones = lead.all_phones()

        # Kiểm tra trùng Số điện thoại trên toàn bộ các tab
        duplicated_phone: str | None = None
        for p in lead_phones:
            if p in seen_phones:
                duplicated_phone = p
                break

        if duplicated_phone:
            duplicate_leads.append(
                (
                    lead,
                    RejectReason.DUPLICATE_PHONE,
                    f"Trùng lặp số điện thoại '{duplicated_phone}' với bản ghi đã được lưu trước đó.",
                )
            )
            continue

        # Kiểm tra quy tắc Mã số thuế (nếu bản ghi có MST)
        root_tax = lead.root_tax_code
        if root_tax:
            existing_branches = tax_code_branches.get(root_tax, [])

            # Kiểm tra cùng tỉnh
            same_province_branch = next(
                (b for b in existing_branches if b.province.strip().lower() == lead.province.strip().lower()),
                None,
            )
            if same_province_branch:
                duplicate_leads.append(
                    (
                        lead,
                        RejectReason.DUPLICATE_TAX_CODE,
                        f"Trùng Mã số thuế gốc '{root_tax}' tại cùng tỉnh '{lead.province}' với cơ sở '{same_province_branch.company_name}'.",
                    )
                )
                continue

            # Kiểm tra giới hạn tối đa 2 chi nhánh khác tỉnh (BA §8.1)
            if len(existing_branches) >= 2:
                duplicate_leads.append(
                    (
                        lead,
                        RejectReason.TAX_CODE_BRANCH_LIMIT,
                        f"Mã số thuế '{root_tax}' đã đạt tối đa 2 chi nhánh đại diện được phép bàn giao.",
                    )
                )
                continue

        # Đạt toàn bộ điều kiện khử trùng -> Ghi nhận bản ghi
        for p in lead_phones:
            seen_phones.add(p)

        if root_tax:
            tax_code_branches.setdefault(root_tax, []).append(lead)

        accepted_leads.append(lead)

    return DeduplicationResult(
        accepted_leads=accepted_leads,
        duplicate_leads=duplicate_leads,
    )
