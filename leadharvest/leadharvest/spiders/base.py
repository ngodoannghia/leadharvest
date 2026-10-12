"""
Lớp Spider cơ sở (BaseLeadSpider) cho dự án LeadHarvest.
"""

from __future__ import annotations

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

