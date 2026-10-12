"""
Schema dữ liệu thô nội bộ (RawLead) thu thập từ Spider.

Lưu ý nghiệp vụ (BA §6.2, §5.3):
  - Các trường kỹ thuật và thông tin nguồn (`source_name`, `source_url`, `crawled_at`, `raw_html`)
    CHỈ dùng nội bộ để truy vết, debug và thống kê QA Report.
  - TUYỆT ĐỐI KHÔNG xuất các trường này ra file bàn giao chính thức cho khách hàng.
  - Thông tin SĐT thô lưu thống nhất dưới dạng 1 chuỗi string `raw_phone`.
    Nếu nguồn có nhiều số, các số được nối bằng dấu ' / '.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class RawLead:
    """Bản ghi dữ liệu thô ban đầu do các Spider cào về."""

    # 1. Thông tin định danh cơ bản do nguồn cung cấp
    company_name: str
    target_segment: str | None = None
    contact_person: str | None = None

    # 2. Thông tin liên lạc thô (chỉ giữ 1 trường string duy nhất cho SĐT)
    raw_phone: str | None = None
    emails: list[str] = field(default_factory=list)
    website: str | None = None
    fax: str | None = None

    # 3. Địa chỉ & Pháp lý
    tax_code: str | None = None
    province: str | None = None
    address: str | None = None
    description: str | None = None

    # 4. Trường nội bộ bắt buộc đối soát (BA §5.3, §6.2)
    source_name: str = ""
    source_url: str = ""
    crawled_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    extra_data: dict[str, Any] = field(default_factory=dict)

    def __init__(
        self,
        company_name: str,
        target_segment: str | None = None,
        contact_person: str | None = None,
        raw_phone: str | None = None,
        emails: list[str] | None = None,
        website: str | None = None,
        fax: str | None = None,
        tax_code: str | None = None,
        province: str | None = None,
        address: str | None = None,
        description: str | None = None,
        source_name: str = "",
        source_url: str = "",
        crawled_at: str | None = None,
        extra_data: dict[str, Any] | None = None,
        raw_phones: list[str] | None = None,
    ):
        self.company_name = company_name
        self.target_segment = target_segment
        self.contact_person = contact_person

        # Chuẩn hóa về 1 chuỗi string duy nhất: nếu truyền raw_phones (dạng list cũ), nối bằng ' / '
        if raw_phones:
            cleaned_phones = [str(p).strip() for p in raw_phones if str(p).strip()]
            if cleaned_phones:
                if raw_phone:
                    parts = [raw_phone.strip()]
                    for cp in cleaned_phones:
                        if cp not in parts:
                            parts.append(cp)
                    raw_phone = " / ".join(parts)
                else:
                    raw_phone = " / ".join(cleaned_phones)

        self.raw_phone = raw_phone.strip() if raw_phone else None
        self.emails = emails or []
        self.website = website
        self.fax = fax
        self.tax_code = tax_code
        self.province = province
        self.address = address
        self.description = description
        self.source_name = source_name
        self.source_url = source_url
        self.crawled_at = crawled_at or datetime.now(timezone.utc).isoformat()
        self.extra_data = extra_data or {}

    def get_all_raw_phones(self) -> list[str]:
        """Tách chuỗi raw_phone thành danh sách các chuỗi số thô."""
        if not self.raw_phone:
            return []
        from leadharvest.validators.phone import split_raw_phone_text
        return split_raw_phone_text(self.raw_phone)

    @property
    def raw_phones(self) -> list[str]:
        """Hỗ trợ tương thích ngược cho các nơi truy cập thuộc tính .raw_phones."""
        return self.get_all_raw_phones()
