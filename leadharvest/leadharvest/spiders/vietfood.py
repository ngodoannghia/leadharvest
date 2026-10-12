"""
Spider thu thập hội viên Hiệp hội Lương thực Việt Nam - VFA (vietfood.org.vn).

Nguồn dữ liệu ngành Lúa gạo / Lương thực / Nông sản theo BA §2.1 & §4.
Tự động gán phân khúc mặc định: 'Nông sản' (Segment.NONG_SAN).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Generator
import scrapy
from scrapy.http import Response

from leadharvest.models.enums import Segment
from leadharvest.spiders.base import BaseLeadSpider
from leadharvest.validators.province import (
    detect_province_from_address,
    normalize_province_name,
)


class VietfoodSpider(BaseLeadSpider):
    """
    Spider cào dữ liệu danh sách và chi tiết hội viên Hiệp hội Lương thực Việt Nam (VFA).
    
    URL danh sách: https://vietfood.org.vn/hoi-vien/danh-sach-hoi-vien/
    URL chi tiết: https://vietfood.org.vn/<slug-hoi-vien>/
    
    Dữ liệu xuất ra dưới dạng RawLead chuẩn của LeadHarvest.
    """

    name = "vietfood"
    allowed_domains = ["vietfood.org.vn"]
    source_name = "VIETFOOD"
    default_segment = Segment.NONG_SAN.value

    start_urls = ["https://vietfood.org.vn/hoi-vien/danh-sach-hoi-vien/"]

    custom_settings = {
        "ROBOTSTXT_OBEY": False,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 4,
        "DOWNLOAD_DELAY": 0.5,
    }

    # Các tag SEO không phải tên tỉnh/thành cần bỏ qua khi trích xuất tỉnh
    NON_PROVINCE_TAGS = {
        "hội viên",
        "danh sách hội viên",
        "hội viên nổi bật",
        "miền nam",
        "miền bắc",
        "miền trung",
        "vietfood",
        "vfa",
    }

    def __init__(
        self,
        limit: int | str | None = None,
        save_file: str | None = None,
        save_folder: str | None = None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, save_file=save_file, save_folder=save_folder, **kwargs)
        self.limit = int(limit) if limit and str(limit).isdigit() else None
        self._crawled_count = 0
        self._seen_urls: set[str] = set()

    def parse(self, response: Response) -> Generator[scrapy.Request, None, None]:
        """
        Duyệt trang danh sách hội viên:
        Trích xuất các liên kết từ thẻ: ol.display-posts-listing li.listing-item a.title
        """
        items = response.css(
            "ol.display-posts-listing li.listing-item a.title, ol.display-posts-listing li.listing-item a"
        )
        self.logger.info(
            f"[VIETFOOD] Đã tải trang danh sách {response.url}: Tìm thấy {len(items)} hội viên."
        )

        for item in items:
            if self.limit and self._crawled_count >= self.limit:
                self.logger.info(
                    f"[VIETFOOD] Đã đạt giới hạn limit={self.limit} bản ghi. Dừng lấy thêm."
                )
                break

            name_raw = item.css("::text").get("")
            name_clean = self._clean_company_name(name_raw)

            detail_rel = item.attrib.get("href", "").strip()
            link_detail = response.urljoin(detail_rel) if detail_rel else ""

            if not link_detail or link_detail in self._seen_urls:
                continue

            self._seen_urls.add(link_detail)
            self._crawled_count += 1

            yield scrapy.Request(
                url=link_detail,
                callback=self.parse_detail,
                meta={
                    "company_name": name_clean,
                    "link_detail": link_detail,
                },
            )

        # Hỗ trợ phân trang nếu website có liên kết sang trang tiếp theo
        next_page = response.css("link[rel='next']::attr(href)").get()
        if not next_page:
            next_page = response.xpath(
                "//a[contains(@class, 'next') or contains(text(), 'Trang sau')]/@href"
            ).get()

        if next_page and (not self.limit or self._crawled_count < self.limit):
            next_url = response.urljoin(next_page.strip())
            if next_url not in self._seen_urls:
                self.logger.info(f"[VIETFOOD] Chuyển tiếp sang trang tiếp theo: {next_url}")
                yield scrapy.Request(url=next_url, callback=self.parse)

    def parse_detail(self, response: Response) -> Generator:
        """
        Trích xuất thông tin chi tiết từng hội viên từ trang chi tiết:
        - Tên doanh nghiệp (tiếng Việt & tiếng Anh)
        - Địa chỉ chi tiết
        - Tỉnh / Thành phố (từ thẻ meta SEO tag và chuỗi địa chỉ)
        - Số điện thoại (Tel/Phone/Hotline)
        - Email liên hệ
        - Website
        - Fax (nếu có)
        - Mã số thuế / Người đại diện (nếu có)
        - Ảnh logo doanh nghiệp
        """
        meta = response.meta
        link_detail = meta.get("link_detail", response.url)

        # 1. Trích xuất tên doanh nghiệp
        company_name = meta.get("company_name")
        if not company_name:
            # Fallback 1: Trích xuất từ heading h1/h3 trong nội dung bài viết
            headings = response.css(".elementor-widget-heading .elementor-heading-title::text").getall()
            for h in headings:
                h_clean = self._clean_company_name(h)
                # Bỏ qua tiêu đề hiệp hội
                if h_clean and "HIỆP HỘI LƯƠNG THỰC" not in h_clean.upper():
                    company_name = h_clean
                    break

        if not company_name:
            # Fallback 2: Trích xuất từ thẻ meta og:title
            og_title = response.css("meta[property='og:title']::attr(content)").get("")
            if og_title:
                company_name = self._clean_company_name(
                    og_title.split("-")[0] if "-" in og_title else og_title
                )

        company_name = (company_name or "").strip()

        # 2. Trích xuất tỉnh / thành phố từ meta article:tag của WordPress
        tags = response.css("meta[property='article:tag']::attr(content)").getall()
        province_candidate: str | None = None
        for tag in tags:
            tag_clean = tag.strip()
            if tag_clean.lower() not in self.NON_PROVINCE_TAGS:
                # Thử chuẩn hóa tên tỉnh qua từ điển 34/63 tỉnh thành
                norm = normalize_province_name(tag_clean)
                if norm:
                    province_candidate = norm
                    break
                elif not province_candidate:
                    province_candidate = tag_clean

        # 3. Trích xuất nội dung từ khối text editor chứa thông tin liên hệ
        target_editor = None
        for te in response.css(".elementor-widget-text-editor .elementor-text-editor"):
            full_txt = te.xpath("string(.)").get("")
            if any(
                kw in full_txt
                for kw in ["Địa chỉ", "Tel", "Điện thoại", "Phone", "Email", "Website", "Fax", "MST"]
            ):
                target_editor = te
                break

        address: str | None = None
        raw_phones: list[str] = []
        emails: list[str] = []
        website: str | None = None
        fax: str | None = None
        tax_code: str | None = None
        contact_person: str | None = None
        english_name: str | None = None

        if target_editor:
            # Lấy tất cả các dòng text, chuẩn hóa unicode NFKC và xóa ký tự ẩn &nbsp;
            raw_lines = target_editor.xpath(".//text()").getall()
            cleaned_lines = []
            for line in raw_lines:
                norm_line = unicodedata.normalize("NFKC", line).replace("\xa0", " ").strip()
                if norm_line:
                    cleaned_lines.append(norm_line)

            for line in cleaned_lines:
                # --- Địa chỉ ---
                m_addr = re.search(
                    r"^(?:Địa chỉ|Address|Trụ sở chính|Trụ sở)\s*:\s*(.+)$",
                    line,
                    re.IGNORECASE,
                )
                if m_addr:
                    address = m_addr.group(1).strip().rstrip(".,;")
                    continue

                # --- Số điện thoại (Tel / Điện thoại / Phone / Hotline / Đ/T) ---
                m_tel = re.search(
                    r"^(?:Tel|Điện thoại|Phone|Hotline|Đ/T)\s*:\s*(.+)$",
                    line,
                    re.IGNORECASE,
                )
                if m_tel:
                    tel_text = m_tel.group(1).strip()
                    # Tách các số phân cách bởi '/', ';', ',', hoặc khoảng trắng nối
                    parts = re.split(r"[/;,–-]\s*(?=[+0-9])", tel_text)
                    for p in parts:
                        p_clean = p.strip()
                        if p_clean and re.search(r"\d{3,}", p_clean):
                            raw_phones.append(p_clean)
                    continue

                # --- Fax ---
                m_fax = re.search(r"^(?:Fax)\s*:\s*(.+)$", line, re.IGNORECASE)
                if m_fax:
                    fax = m_fax.group(1).strip().rstrip(".,;")
                    continue

                # --- Email ---
                m_email = re.search(
                    r"^(?:Email|Thư điện tử|E-mail)\s*:\s*(.+)$",
                    line,
                    re.IGNORECASE,
                )
                if m_email:
                    email_str = m_email.group(1).strip()
                    found_emails = re.findall(
                        r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", email_str
                    )
                    emails.extend(found_emails)
                    continue
                elif "@" in line:
                    found_emails = re.findall(
                        r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", line
                    )
                    emails.extend(found_emails)

                # --- Website ---
                m_web = re.search(r"^(?:Website|Web)\s*:\s*(.+)$", line, re.IGNORECASE)
                if m_web:
                    website = m_web.group(1).strip().rstrip(".,;")
                    continue

                # --- Mã số thuế (MST) ---
                m_mst = re.search(r"^(?:Mã số thuế|MST|Tax code)\s*:\s*(.+)$", line, re.IGNORECASE)
                if m_mst:
                    tax_code = m_mst.group(1).strip().rstrip(".,;")
                    continue

                # --- Người đại diện / Chủ cơ sở ---
                m_rep = re.search(
                    r"^(?:Người đại diện|Đại diện pháp luật|Chủ cơ sở|Giám đốc|Tổng Giám đốc|Chủ tịch)\s*:\s*(.+)$",
                    line,
                    re.IGNORECASE,
                )
                if m_rep:
                    contact_person = m_rep.group(1).strip().rstrip(".,;")
                    continue

                # --- Tên tiếng Anh / Tên quốc tế ---
                # Dòng đầu tiên nếu không chứa các từ khóa liên hệ
                if not english_name and not any(
                    kw in line.lower()
                    for kw in ["địa chỉ", "address", "tel", "fax", "email", "website", "http", "phone", "mst"]
                ):
                    english_name = line

            # Kiểm tra thêm các thẻ liên kết <a> trong khối text editor để lấy website hoặc mailto
            if not website:
                for a_href in target_editor.css("a::attr(href)").getall():
                    a_href = a_href.strip()
                    if a_href.startswith("http") and "vietfood.org.vn" not in a_href:
                        website = a_href
                        break
                    elif a_href.startswith("mailto:"):
                        m = re.search(r"mailto:([^\?&]+)", a_href)
                        if m:
                            emails.append(m.group(1).strip())

        # Khử trùng lặp email và loại bỏ rỗng
        clean_emails = list(dict.fromkeys([e.strip() for e in emails if e.strip()]))

        # 4. Xác định tỉnh/thành phố cuối cùng
        # Ưu tiên tag SEO, nếu chưa có thì dò từ chuỗi địa chỉ
        province = province_candidate
        if address:
            detected_prov = detect_province_from_address(address)
            if detected_prov:
                province = detected_prov
            elif not province:
                province = normalize_province_name(address)

        # 5. Logo hình ảnh công ty
        logo_url = response.css(".elementor-image img::attr(src)").get()
        extra_data = {}
        if logo_url:
            extra_data["logo_url"] = response.urljoin(logo_url.strip())
        if english_name:
            extra_data["english_name"] = english_name

        # 6. Tạo mô tả
        description_parts = []
        if english_name:
            description_parts.append(english_name)
        description_parts.append("Hội viên Hiệp hội Lương thực Việt Nam (VFA)")
        description = ". ".join(description_parts)

        # 7. Trả về RawLead qua helper make_raw_lead
        raw_phone_str = " / ".join(raw_phones) if raw_phones else None
        yield self.make_raw_lead(
            company_name=company_name,
            target_segment=self.default_segment,
            contact_person=contact_person,
            raw_phone=raw_phone_str,
            emails=clean_emails,
            website=website,
            fax=fax,
            tax_code=tax_code,
            province=province,
            address=address,
            description=description,
            source_url=link_detail,
            extra_data=extra_data,
        )

    @staticmethod
    def _clean_company_name(name: str) -> str:
        """
        Làm sạch tên công ty:
        - Xóa dấu '*' ở cuối (dấu đánh dấu hội viên liên kết của Vietfood).
        - Chuẩn hóa khoảng trắng thừa.
        """
        if not name:
            return ""
        # Xóa dấu * hoặc dấu khoảng trắng ở đuôi
        cleaned = re.sub(r"[\*\s]+$", "", name.strip())
        # Xóa khoảng trắng lặp lại
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.strip()
