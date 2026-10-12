"""
Schema dữ liệu thô nội bộ (RawLead) thu thập từ Spider.

Lưu ý nghiệp vụ (BA §6.2, §5.3):
  - Các trường kỹ thuật và thông tin nguồn (`source_name`, `source_url`, `crawled_at`, `raw_html`)
    CHỈ dùng nội bộ để truy vết, debug và thống kê QA Report.
  - TUYỆT ĐỐI KHÔNG xuất các trường này ra file bàn giao chính thức cho khách hàng.
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
    
    # 2. Thông tin liên lạc thô
    raw_phone: str | None = None
    raw_phones: list[str] = field(default_factory=list)
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

    def get_all_raw_phones(self) -> list[str]:
        """Gom tất cả các nguồn số điện thoại thô thành một danh sách."""
        phones: list[str] = []
        if self.raw_phone:
            phones.append(self.raw_phone)
        phones.extend(self.raw_phones)
        return phones
