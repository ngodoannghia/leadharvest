"""
Spider thu thập hội viên VASEP (Hiệp hội Chế biến và Xuất khẩu Thủy sản Việt Nam).

Nguồn P0 bắt buộc theo BA §5.1 cho phân khúc Thủy sản.
"""

from __future__ import annotations

import re
import scrapy
from leadharvest.models.enums import Segment
from leadharvest.spiders.base import BaseLeadSpider


class VasepSpider(BaseLeadSpider):
    """
    Spider cào dữ liệu danh sách và chi tiết hội viên VASEP.
    Trả về đối tượng RawLead.
    """

    name = "vasep"
    allowed_domains = ["vasep.com.vn"]
    source_name = "VASEP"
    default_segment = Segment.THUY_SAN.value

    custom_settings = {
        "ROBOTSTXT_OBEY": False,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 4,
        "DOWNLOAD_DELAY": 0.5,
    }

    @staticmethod
    def _is_truthy(val: any) -> bool:
        if isinstance(val, bool):
            return val
        if val is None:
            return False
        return str(val).strip().lower() in ("true", "1", "yes", "y", "t", "all")

    def __init__(
        self,
        start_page: int | str = 1,
        end_page: int | str | None = 10,
        crawl_all: bool | str | None = False,
        save_file: str | None = None,
        save_folder: str | None = None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, save_file=save_file, save_folder=save_folder, **kwargs)
        self.save_file = (
            save_file
            or kwargs.get("filename")
            or kwargs.get("file_name")
            or kwargs.get("output_file")
            or getattr(self, "save_file", None)
        )
        self.save_folder = (
            save_folder
            or kwargs.get("save_dir")
            or kwargs.get("output_dir")
            or kwargs.get("output_folder")
            or getattr(self, "save_folder", None)
        )
        self.base_url = "https://vasep.com.vn/hoi-vien"

        # Nhận diện tham số crawl_all (hỗ trợ các alias: crawl_all, all_pages, all)
        raw_crawl_all = crawl_all
        if not self._is_truthy(raw_crawl_all):
            raw_crawl_all = kwargs.get("all_pages", kwargs.get("all", False))

        # Hỗ trợ truyền end_page='all', end_page='max', end_page=0 hoặc end_page=-1
        if end_page is not None and str(end_page).strip().lower() in ("all", "max", "-1", "0"):
            self.crawl_all = True
            end_page = None
        else:
            self.crawl_all = self._is_truthy(raw_crawl_all)

        self.start_page = int(start_page) if str(start_page).isdigit() else 1
        self.end_page = (
            int(end_page)
            if (end_page is not None and str(end_page).isdigit())
            else (None if self.crawl_all else 10)
        )

        if self.crawl_all:
            self.start_urls = [f"{self.base_url}?page={self.start_page}"]
            self.logger.info(
                f"[VASEP] Khởi chạy chế độ CRAWL TẤT CẢ CÁC TRANG (bắt đầu từ trang {self.start_page})."
            )
        else:
            final_end_page = self.end_page if self.end_page is not None else 10
            self.start_urls = [
                f"{self.base_url}?page={p}"
                for p in range(self.start_page, final_end_page + 1)
            ]
            self.logger.info(
                f"[VASEP] Khởi chạy cào từ trang {self.start_page} đến trang {final_end_page}."
            )

    def parse(self, response):
        """Duyệt qua từng thẻ hội viên trên trang danh sách."""
        page_match = re.search(r"page=(\d+)", response.url)
        current_page = (
            int(page_match.group(1))
            if page_match
            else response.meta.get("page", self.start_page)
        )

        items = response.css(".xitem")
        self.logger.info(
            f"Đã tải {response.url} (Trang {current_page}): Tìm thấy {len(items)} hội viên."
        )

        if not items:
            self.logger.info(
                f"Không còn hội viên nào tại {response.url}. Dừng cào phân trang."
            )
            return

        for item_node in items:
            name_raw = item_node.css(".xtitle::text").get()
            name_company_list = name_raw.strip() if name_raw else ""

            detail_rel = item_node.css("a::attr(href)").get()
            link_detail = response.urljoin(detail_rel.strip()) if detail_rel else ""

            if not link_detail:
                continue

            yield scrapy.Request(
                url=link_detail,
                callback=self.parse_detail,
                meta={
                    "name_company_list": name_company_list,
                    "link_detail": link_detail,
                },
            )

        # Xử lý tự động chuyển trang khi bật option crawl_all
        if self.crawl_all:
            paging_hrefs = response.css(".pagination a::attr(href)").getall()
            paging_numbers = [
                int(m.group(1))
                for h in paging_hrefs
                for m in [re.search(r"page=(\d+)", h)]
                if m
            ]
            has_next_btn = bool(
                response.css("#dnn_ctr4087_Main_ctl00_vbPaging_btnNext")
                or response.xpath("//a[contains(@id, 'btnNext') or contains(., 'Trang sau')]")
            )
            max_seen_page = max(paging_numbers) if paging_numbers else current_page

            # Nếu trang hiện tại đã chạm max_seen_page và không còn nút Next -> đã đến trang cuối
            if current_page >= max_seen_page and not has_next_btn:
                self.logger.info(
                    f"[VASEP] Đã đến trang cuối cùng ({current_page}). Hoàn tất duyệt toàn bộ danh sách hội viên!"
                )
            else:
                next_page = current_page + 1
                next_url = f"{self.base_url}?page={next_page}"
                self.logger.info(
                    f"[VASEP] Đang chuyển tiếp sang trang {next_page}: {next_url}"
                )
                yield scrapy.Request(
                    url=next_url,
                    callback=self.parse,
                    meta={"page": next_page},
                )

    def parse_detail(self, response):
        """Trích xuất chi tiết doanh nghiệp từ bảng thông tin hội viên."""
        meta = response.meta
        link_detail = meta.get("link_detail", response.url)

        row_dict = {}
        rows = response.css(".table-responsive table.table-condensed tr, .table-responsive table tr")
        for row in rows:
            cols = [t.strip() for t in row.xpath(".//td//text() | .//th//text()").getall() if t.strip()]
            if len(cols) >= 2:
                key = cols[0].lower().strip(": ")
                val = " ".join(cols[1:]).strip()
                row_dict[key] = val
            elif len(cols) == 1 and ":" in cols[0]:
                parts = cols[0].split(":", 1)
                row_dict[parts[0].lower().strip()] = parts[1].strip()

        company_name = (row_dict.get("tên doanh nghiệp") or meta.get("name_company_list", "")).strip()
        if not company_name:
            return

        # Loại bỏ các đơn vị là trường đại học, cao đẳng, học viện hoặc ngân hàng
        if self.is_excluded_organization(company_name):
            self.logger.info(
                f"[VASEP] Bỏ qua đơn vị trường học / ngân hàng / viện đào tạo: '{company_name}' ({response.url})"
            )
            return

        raw_address = row_dict.get("địa chỉ") or ""

        province = (
            row_dict.get("tỉnh thành phố")
            or row_dict.get("tỉnh/thành phố")
            or row_dict.get("tỉnh thành")
            or None
        )
        tax_code = row_dict.get("mã số thuế") or row_dict.get("mst") or None
        contact_person = (
            row_dict.get("người đại diện")
            or row_dict.get("người đại diện pháp luật")
            or row_dict.get("chủ cơ sở")
            or None
        )
        raw_phone = row_dict.get("điện thoại") or None
        fax = row_dict.get("fax") or None
        website = row_dict.get("website") or None
        product = row_dict.get("sản phẩm") or ""
        field_activity = row_dict.get("lĩnh vực hoạt động") or ""

        # Trích xuất danh sách emails
        raw_email = row_dict.get("email") or row_dict.get("emails") or ""
        extracted_emails = re.findall(
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", str(raw_email)
        )
        emails = list(dict.fromkeys(extracted_emails))

        # Tách địa chỉ xưởng và địa chỉ VPDD (BA §2.2: ưu tiên địa chỉ xưởng/nhà máy thực tế)
        factory_address = raw_address
        if "Địa chỉ VPDD:" in raw_address:
            parts = raw_address.split("Địa chỉ VPDD:", 1)
            # Ưu tiên phần địa chỉ trước VPDD (thường là địa chỉ nhà máy tại KCN)
            candidate = parts[0].strip(" ;,–-")
            if len(candidate) > 10:
                factory_address = candidate

        description = f"{field_activity}. {product}".strip(" .")

        yield self.make_raw_lead(
            company_name=company_name.strip(),
            target_segment=self.default_segment,
            contact_person=contact_person.strip() if contact_person else None,
            raw_phone=raw_phone,
            emails=emails,
            website=website.strip() if website else None,
            fax=fax.strip() if fax else None,
            tax_code=tax_code.strip() if tax_code else None,
            province=province.strip() if province else None,
            address=factory_address.strip() if factory_address else None,
            description=description if description else None,
            source_url=link_detail,
        )
