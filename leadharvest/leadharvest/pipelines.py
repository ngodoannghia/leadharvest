"""
Scrapy Pipelines cho LeadHarvest.

Lưu dữ liệu thô vào `data/raw/<spider_name>.jsonl` và quản lý checkpoint URL
để tiếp tục chạy mà không bị trùng bản ghi khi bị gián đoạn (BA §13.3, §13.4).
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, is_dataclass
from leadharvest.models.enums import PhoneType
from leadharvest.models.raw_lead import RawLead
from leadharvest.validators.phone import extract_phones


class RawLeadStoragePipeline:
    """
    Lưu dữ liệu thô dạng JSON Lines vào thư mục `data/raw/` (hoặc thư mục tùy chọn qua -a save_folder=...).
    Cung cấp cơ chế checkpoint theo URL đã cào và thống kê số lượng mobile thu thập được.
    """

    def __init__(self, default_output_dir: str = "data/raw"):
        self.files = {}
        self.seen_urls = set()
        self.default_output_dir = default_output_dir
        self.stats = {}

    @classmethod
    def from_crawler(cls, crawler):
        output_dir = crawler.settings.get("RAW_DATA_DIR", "data/raw")
        return cls(default_output_dir=output_dir)

    def _resolve_file_path(self, spider) -> str:
        save_file = (
            getattr(spider, "save_file", None)
            or getattr(spider, "filename", None)
            or getattr(spider, "file_name", None)
            or getattr(spider, "output_file", None)
        )
        save_folder = (
            getattr(spider, "save_folder", None)
            or getattr(spider, "save_dir", None)
            or getattr(spider, "output_dir", None)
            or getattr(spider, "output_folder", None)
            or self.default_output_dir
        )

        if save_file:
            save_file = str(save_file).strip()
            # Tự động thêm đuôi .jsonl nếu chưa có đuôi mở rộng
            if not save_file.endswith(".jsonl") and not os.path.splitext(save_file)[1]:
                save_file += ".jsonl"

            # Nếu chỉ truyền tên file (không có đường dẫn thư mục), kết hợp với save_folder (mặc định data/raw)
            if not os.path.dirname(save_file):
                return os.path.join(save_folder, save_file)
            return save_file

        return os.path.join(save_folder, f"{spider.name}.jsonl")

    def open_spider(self, spider):
        file_path = self._resolve_file_path(spider)
        output_dir = os.path.dirname(file_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        self.stats[spider] = {
            "total": 0,
            "mobile": 0,
            "landline": 0,
            "hotline": 0,
            "no_phone": 0,
        }

        # Đọc checkpoint từ file cũ nếu đã tồn tại
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            data = json.loads(line)
                            url = data.get("source_url")
                            if url:
                                self.seen_urls.add(url)
                        except json.JSONDecodeError:
                            continue

        self.files[spider] = open(file_path, "a", encoding="utf-8")
        spider.logger.info(
            f"Đã mở file checkpoint raw: {file_path}. Đã có {len(self.seen_urls)} URLs đã cào."
        )

    def close_spider(self, spider):
        f = self.files.pop(spider, None)
        if f:
            f.close()

        st = self.stats.pop(spider, None)
        if st:
            total = st["total"]
            skipped = st.get("skipped_checkpoint", 0)
            if total > 0:
                mob = st["mobile"]
                land = st["landline"]
                hot = st["hotline"]
                no_p = st["no_phone"]
                mob_pct = (mob / total * 100.0) if total > 0 else 0.0

                summary_box = (
                    f"\n" + "=" * 65 + "\n"
                    f"THỐNG KÊ THU THẬP DỮ LIỆU THÔ (SPIDER: {spider.name.upper()}):\n"
                    f"- Tổng số bản ghi mới ghi nhận   : {total:,}\n"
                    f"- Số bản ghi có di động (Mobile)  : {mob:,} ({mob_pct:.1f}%)\n"
                    f"- Số bản ghi có số bàn (Landline) : {land:,}\n"
                    f"- Số bản ghi có Hotline           : {hot:,}\n"
                    f"- Số bản ghi không có SĐT         : {no_p:,}\n"
                )
                if skipped > 0:
                    summary_box += f"- Số bản ghi bỏ qua (đã có từ trước): {skipped:,}\n"
                summary_box += "=" * 65
                spider.logger.info(summary_box)
                print(summary_box)
            elif skipped > 0:
                msg = f"\n[INFO] Đã hoàn thành spider {spider.name}. Toàn bộ {skipped:,} bản ghi đã có trong checkpoint (không có bản ghi mới)."
                spider.logger.info(msg)
                print(msg)

    def process_item(self, item, spider):
        url = getattr(item, "source_url", "")
        if url and url in self.seen_urls:
            # Bản ghi đã có trong checkpoint từ lần chạy trước -> bỏ qua
            st = self.stats.get(spider)
            if st is not None:
                st["skipped_checkpoint"] = st.get("skipped_checkpoint", 0) + 1
            return item

        f = self.files.get(spider)
        if f:
            data = asdict(item) if is_dataclass(item) else dict(item)
            f.write(json.dumps(data, ensure_ascii=False) + "\n")
            f.flush()
            if url:
                self.seen_urls.add(url)

        # Thống kê loại số điện thoại
        if hasattr(item, "raw_phone"):
            phones_raw = item.raw_phone
        elif isinstance(item, dict):
            phones_raw = item.get("raw_phone") or item.get("raw_phones")
        else:
            phones_raw = None

        st = self.stats.get(spider)
        if st is not None:
            st["total"] += 1
            extracted = extract_phones(phones_raw)
            has_mobile = any(p.type is PhoneType.MOBILE for p in extracted)
            has_landline = any(p.type is PhoneType.LANDLINE for p in extracted)
            has_hotline = any(p.type is PhoneType.HOTLINE for p in extracted)

            if has_mobile:
                st["mobile"] += 1
            if has_landline:
                st["landline"] += 1
            if has_hotline:
                st["hotline"] += 1
            if not extracted:
                st["no_phone"] += 1

        return item
