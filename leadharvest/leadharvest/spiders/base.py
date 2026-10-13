"""
Lớp Spider cơ sở (BaseLeadSpider) cho dự án LeadHarvest.
"""

from __future__ import annotations

import re
import scrapy
from leadharvest.models.raw_lead import RawLead


class BaseLeadSpider(scrapy.Spider):
    """
    Spider cha cho tất cả các spider thu thập B2B leads.
    Đảm bảo mọi spider trả về đối tượng RawLead chuẩn thống nhất.
    """

    default_segment: str | None = None
    source_name: str = "GENERIC"
    save_file: str | None = None
    save_folder: str | None = None

    # Các mẫu regex nhận diện trường đại học, trường cao đẳng, học viện hoặc ngân hàng, tín dụng
    EXCLUDED_ORG_PATTERNS: tuple[str, ...] = (
        r"\btrường\s+(?:đại\s*học|cao\s*đẳng|trung\s*cấp|đh|cđ)\b",
        r"\bđại\s*học\b",
        r"\btrường\s+đh\b",
        r"\btrường\s+cao\s*đẳng\b",
        r"\bcao\s*đẳng\b",
        r"\btrường\s+cđ\b",
        r"\bhọc\s*viện\b",
        r"\btrường\s+trung\s*cấp\b",
        r"\buniversity\b",
        r"\bcollege\b",
        r"\bacademy\b",
        r"\bngân\s*hàng\b",
        r"\bngan\s*hang\b",
        r"\b\w*bank\b",
        r"\bquỹ\s+tín\s*dụng\b",
    )

    @classmethod
    def is_excluded_organization(cls, name: str | None) -> bool:
        """
        Kiểm tra xem tên đơn vị có phải là trường đại học, cao đẳng, học viện
        hoặc ngân hàng, quỹ tín dụng hay không (không phải đối tượng doanh nghiệp B2B mục tiêu).
        """
        if not name:
            return False
        lower = f" {name.strip().lower()} "
        return any(bool(re.search(pat, lower)) for pat in cls.EXCLUDED_ORG_PATTERNS)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.save_file = (
            kwargs.get("save_file")
            or kwargs.get("filename")
            or kwargs.get("file_name")
            or kwargs.get("output_file")
            or getattr(self, "save_file", None)
        )
        self.save_folder = (
            kwargs.get("save_folder")
            or kwargs.get("save_dir")
            or kwargs.get("output_dir")
            or kwargs.get("output_folder")
            or getattr(self, "save_folder", None)
        )

    def make_raw_lead(self, **kwargs) -> RawLead:
        """Helper tạo RawLead tự động điền source_name và target_segment mặc định."""
        if "source_name" not in kwargs:
            kwargs["source_name"] = self.source_name
        if "target_segment" not in kwargs and self.default_segment:
            kwargs["target_segment"] = self.default_segment
        return RawLead(**kwargs)


