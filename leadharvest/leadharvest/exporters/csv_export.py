"""
Xuất dữ liệu bàn giao sang 6 file CSV độc lập theo phân khúc (BA §6, §10.1).

Yêu cầu:
  - Mỗi phân khúc một file CSV riêng biệt: `nong_san.csv`, `thuy_san.csv`, v.v.
  - Sử dụng encoding `utf-8-sig` (UTF-8 kèm BOM) để Microsoft Excel mở trực tiếp
    hiển thị đúng 100% tiếng Việt có dấu mà không bị lỗi font (mojibake).
  - Đúng 11 cột hiển thị theo thứ tự BA §6.
"""

from __future__ import annotations

import csv
import os
from leadharvest.models.enums import SEGMENT_ORDER
from leadharvest.models.lead_output import LeadOutput


def export_to_csv_files(
    leads: list[LeadOutput],
    output_dir: str,
) -> dict[str, str]:
    """
    Xuất danh sách LeadOutput thành 6 file CSV theo phân khúc.
    Trả về dict: {segment_name: file_path}.
    """
    os.makedirs(output_dir, exist_ok=True)
    generated_files: dict[str, str] = {}

    leads_by_seg: dict[str, list[LeadOutput]] = {s.value: [] for s in SEGMENT_ORDER}
    for lead in leads:
        if lead.target_segment in leads_by_seg:
            leads_by_seg[lead.target_segment].append(lead)

    for seg in SEGMENT_ORDER:
        file_name = f"{seg.slug}.csv"
        file_path = os.path.join(output_dir, file_name)
        seg_leads = leads_by_seg[seg.value]

        with open(file_path, mode="w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            # Ghi dòng tiêu đề
            writer.writerow(LeadOutput.COLUMN_HEADERS)
            # Ghi các dòng dữ liệu
            for lead in seg_leads:
                writer.writerow(lead.to_row())

        generated_files[seg.value] = file_path

    return generated_files
