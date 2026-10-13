"""
Spider thu thập hội viên Hiệp hội Dệt may Việt Nam - VITAS (vietnamtextile.org.vn).

Nguồn dữ liệu ngành Dệt may theo BA §2.1 & tài liệu BA_baoBiHongHai.md.
Tự động gán phân khúc mặc định: 'Dệt may' (Segment.DET_MAY).
"""

from __future__ import annotations

import html
import re
import unicodedata
from typing import Generator
import scrapy
from scrapy.http import Response

from leadharvest.models.enums import Segment
from leadharvest.spiders.base import BaseLeadSpider
from leadharvest.validators.province import detect_province_from_address


class VietnamTextileSpider(BaseLeadSpider):
    """
    Spider cào dữ liệu danh sách và chi tiết hội viên Hiệp hội Dệt may Việt Nam (VITAS).
    
    URL danh sách: http://www.vietnamtextile.org.vn/hoi-vien-vitas_p1_1-1_2-1_3-676.html
    URL chi tiết: http://www.vietnamtextile.org.vn/DanhBa.aspx?i={id}
    
    Dữ liệu xuất ra dưới dạng RawLead chuẩn của LeadHarvest.
    """

    name = "vietnamtextile"
    allowed_domains = ["vietnamtextile.org.vn"]
    source_name = "VITAS"
    default_segment = Segment.DET_MAY.value

    start_urls = [
        "http://www.vietnamtextile.org.vn/hoi-vien-vitas_p1_1-1_2-1_3-676.html"
    ]

    custom_settings = {
        "ROBOTSTXT_OBEY": False,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 4,
        "DOWNLOAD_DELAY": 0.5,
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
        self._seen_pages: set[str] = set()

    def parse(self, response: Response) -> Generator[scrapy.Request, None, None]:
        """
        Duyệt trang danh sách hội viên VITAS:
        - Trích xuất link chi tiết hội viên: a[href*="DanhBa.aspx"]
        - Phân trang qua link: a[href*="hoi-vien-vitas_p1_1-1_2-1_3-676"]
        """
        # Ghi nhận trang hiện tại đã duyệt
        current_page_clean = response.url.split("#")[0]
        self._seen_pages.add(current_page_clean)

        # 1. Trích xuất danh sách hội viên trên trang hiện tại
        detail_links = response.css('a[href*="DanhBa.aspx"]')
        member_items: dict[str, str] = {}

        for a in detail_links:
            href = a.attrib.get("href", "").strip().split("#")[0]
            if not href:
                continue
            full_url = response.urljoin(href)
            text = a.css("::text").get("").strip()
            text = self._clean_text(text)

            if full_url not in member_items:
                member_items[full_url] = text
            elif text and not member_items[full_url]:
                member_items[full_url] = text

        self.logger.info(
            f"[VITAS] Đã tải trang danh sách {response.url}: Tìm thấy {len(member_items)} hội viên."
        )

        for detail_url, name in member_items.items():
            if self.limit and self._crawled_count >= self.limit:
                self.logger.info(
                    f"[VITAS] Đã đạt giới hạn limit={self.limit} bản ghi. Dừng lấy thêm."
                )
                return

            if name and self.is_excluded_organization(name):
                self.logger.info(
                    f"[VITAS] Bỏ qua trường học/ngân hàng từ trang danh sách: '{name}' ({detail_url})"
                )
                continue

            if detail_url in self._seen_urls:
                continue
            self._seen_urls.add(detail_url)


            yield scrapy.Request(
                detail_url,
                callback=self.parse_detail,
                meta={"company_name": name},
            )

        # 2. Xử lý phân trang
        if self.limit and len(self._seen_urls) >= self.limit:
            return

        pagination_links = response.css('a[href*="hoi-vien-vitas"]')
        for p in pagination_links:
            href = p.attrib.get("href", "").strip()
            if not href or "_12-" not in href:
                continue
            page_url = response.urljoin(href).split("#")[0]
            if page_url not in self._seen_pages:
                self._seen_pages.add(page_url)
                self.logger.info(f"[VITAS] Chuyển tiếp trang danh sách: {page_url}")
                yield scrapy.Request(page_url, callback=self.parse)

    def parse_detail(self, response: Response):
        """
        Trích xuất thông tin chi tiết từng hội viên VITAS.
        """
        if self.limit and self._crawled_count >= self.limit:
            return

        meta_name = response.meta.get("company_name", "").strip()
        content_sel = response.css("#content_ptab_1, .pl_c, .danhba_subpage_content")
        raw_html = content_sel.get() or response.text

        # 1. Tiền xử lý HTML thành các dòng văn bản sạch sẽ
        text = self._clean_html_to_text(raw_html)
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        if not lines and not meta_name:
            self.logger.warning(f"[VITAS] Bỏ qua trang rỗng: {response.url}")
            return

        # 2. Trích xuất tên công ty
        heading_name = response.css("h1::text, .pc_title::text, .title::text").get("").strip()
        heading_name = self._clean_text(heading_name)
        company_name = heading_name or meta_name

        # Nếu dòng đầu tiên có 'Tên Công ty:' hoặc tương tự
        english_name: str | None = None
        address: str | None = None
        phone_parts: list[str] = []
        fax: str | None = None
        emails: list[str] = []
        website: str | None = None
        contact_person: str | None = None
        activities: list[str] = []
        desc_lines: list[str] = []

        # Quét email regex toàn bộ nội dung
        found_emails = re.findall(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", text
        )
        for em in found_emails:
            em_clean = em.lower().strip(".,;")
            if em_clean not in emails:
                emails.append(em_clean)

        # Quét thẻ link website ngoài
        for a_tag in response.css('#content_ptab_1 a, .pl_c a'):
            href = a_tag.attrib.get('href', '').strip()
            if href.startswith('http') and 'vietnamtextile.org.vn' not in href:
                website = href
                break

        # Duyệt từng dòng để bóc tách các trường
        for idx, line in enumerate(lines):
            # Nếu tên công ty chưa có hoặc dòng đầu tiên là tên công ty
            if idx == 0 and not company_name:
                company_name = self._extract_value_or_line(line, r"^Tên\s+Công\s*ty\s*:\s*(.+)")
                continue

            # Tên tiếng Anh thường là dòng 2 (nếu không có nhãn trường và chứa keyword quốc tế)
            if idx == 1 and not english_name and not self._is_field_label(line):
                if re.search(r"(?:Company|Corporation|JSC|Co\.|Ltd|Enterprise|Group)", line, re.IGNORECASE):
                    english_name = line
                    continue

            # Tên công ty có nhãn 'Tên Công ty:'
            if re.search(r"^Tên\s+(?:Công\s*ty|Doanh\s*nghiệp)\s*:\s*", line, re.IGNORECASE):
                val = re.sub(r"^Tên\s+(?:Công\s*ty|Doanh\s*nghiệp)\s*:\s*", "", line, flags=re.IGNORECASE).strip()
                if val:
                    company_name = val
                continue

            # Địa chỉ
            if re.search(r"^(?:Địa\s*chỉ|Address|Trụ\s*sở(?:\s*chính)?)\s*:\s*", line, re.IGNORECASE):
                addr_val = re.sub(r"^(?:Địa\s*chỉ|Address|Trụ\s*sở(?:\s*chính)?)\s*:\s*", "", line, flags=re.IGNORECASE).strip()
                contact_split = re.split(
                    r"\s*(?=(?:Tel|Điện\s*thoại|SĐT|Phone|Hotline|Đ[Tt]|Mobile|Fax|Email)\s*:\s*)",
                    addr_val,
                    flags=re.IGNORECASE,
                )
                address = contact_split[0].strip().rstrip(",;") if contact_split else addr_val
                continue

            # Điện thoại, Mobile & Fax
            if re.search(r"(?:Điện\s*thoại|SĐT|Tel|Phone|Hotline|Đ[Tt]|Mobile)\s*:\s*", line, re.IGNORECASE):
                phone_line = line
                # Nếu có chứa Fax trên cùng dòng: Điện thoại: ... - Fax: ...
                if re.search(r"-?\s*Fax\s*:\s*", phone_line, re.IGNORECASE):
                    parts = re.split(r"-?\s*Fax\s*:\s*", phone_line, flags=re.IGNORECASE)
                    phone_part = parts[0]
                    if len(parts) > 1 and not fax:
                        fax_val = parts[1].strip()
                        fax = re.sub(r"[^\d\s\(\)\+\-\.]", "", fax_val).strip()
                    phone_line = phone_part

                extracted_phone = re.sub(
                    r"^.*?(?:Điện\s*thoại|SĐT|Tel|Phone|Hotline|Đ[Tt]|Mobile)\s*:\s*", "", phone_line, flags=re.IGNORECASE
                ).strip()
                if extracted_phone:
                    phone_parts.extend(self._split_and_clean_phones(extracted_phone))
                continue



            # Dòng chỉ có Fax
            if re.search(r"^Fax\s*:\s*", line, re.IGNORECASE):
                fax_val = re.sub(r"^Fax\s*:\s*", "", line, flags=re.IGNORECASE).strip()
                if fax_val and not fax:
                    fax = re.sub(r"[^\d\s\(\)\+\-\.]", "", fax_val).strip()
                continue

            # Website
            if re.search(r"^(?:Website|Web)\s*:\s*", line, re.IGNORECASE):
                web_val = re.sub(r"^(?:Website|Web)\s*:\s*", "", line, flags=re.IGNORECASE).strip()
                if web_val and not website:
                    if not web_val.startswith("http"):
                        web_val = "https://" + web_val
                    website = web_val
                continue

            # Người đại diện / Lãnh đạo
            m_contact = re.search(
                r"^(?:Giám\s*đốc|Tổng\s*giám\s*đốc|Tổng\s*Giám\s*đốc|Chủ\s*tịch|Người\s*đại\s*diện|Đại\s*diện\s*(?:Công\s*ty|pháp\s*luật)?)\s*:\s*(.*)",
                line,
                re.IGNORECASE,
            )
            if m_contact:
                val = m_contact.group(1).strip()
                # Nếu giá trị trên cùng dòng chỉ là danh xưng ("Ông", "Bà") hoặc rỗng, lấy dòng tiếp theo
                if val.lower() in ("ông", "bà", "ông/bà", "") and idx + 1 < len(lines):
                    next_l = lines[idx + 1].strip()
                    if not self._is_field_label(next_l) and len(next_l) < 50:
                        val = next_l
                if val:
                    contact_person = val
                continue


            # Hoạt động chính / Sản phẩm chính
            if re.search(r"^(?:Hoạt\s*động\s*chính|Ngành\s*nghề|Sản\s*phẩm\s*chính)\s*:\s*", line, re.IGNORECASE):
                act_val = re.sub(
                    r"^(?:Hoạt\s*động\s*chính|Ngành\s*nghề|Sản\s*phẩm\s*chính)\s*:\s*",
                    "",
                    line,
                    flags=re.IGNORECASE,
                ).strip()
                if act_val:
                    activities.append(act_val)
                continue

            # Các dòng mô tả giới thiệu khác
            if not self._is_field_label(line) and len(line) > 20:
                desc_lines.append(line)

        company_name = self._clean_company_name(company_name or meta_name)
        if not company_name:
            self.logger.warning(f"[VITAS] Không tìm thấy tên công ty tại: {response.url}")
            return

        # Loại bỏ các đơn vị là trường đại học, cao đẳng, học viện hoặc ngân hàng
        if self.is_excluded_organization(company_name):
            self.logger.info(
                f"[VITAS] Bỏ qua đơn vị trường học / ngân hàng / viện đào tạo: '{company_name}' ({response.url})"
            )
            return


        # Chuẩn hóa SĐT dạng string duy nhất ghép bằng ' / '
        raw_phone_str: str | None = None
        unique_phones: list[str] = []
        for p in phone_parts:
            p_clean = p.strip()
            if p_clean and p_clean not in unique_phones:
                unique_phones.append(p_clean)
        if unique_phones:
            raw_phone_str = " / ".join(unique_phones)

        # Xác định tỉnh / thành phố từ địa chỉ
        province: str | None = None
        if address:
            province = detect_province_from_address(address)

        # Lấy toàn bộ nội dung chi tiết hội viên làm description
        description = text.strip() if text else None


        # Trích xuất extra_data
        extra_data: dict[str, str] = {}
        if english_name:
            extra_data["english_name"] = english_name

        # Lấy member id từ URL: DanhBa.aspx?i=51
        id_match = re.search(r"[?&]i=(\d+)", response.url)
        if id_match:
            extra_data["member_id"] = id_match.group(1)

        lead = self.make_raw_lead(
            company_name=company_name,
            target_segment=self.default_segment,
            contact_person=contact_person,
            raw_phone=raw_phone_str,
            emails=emails,
            website=website,
            fax=fax,
            province=province,
            address=address,
            description=description,
            source_url=response.url,
            extra_data=extra_data,
        )

        self._crawled_count += 1
        self.logger.info(
            f"[VITAS #{self._crawled_count}] {company_name} | {province or 'Chưa rõ tỉnh'} | {raw_phone_str or 'Không SĐT'}"
        )
        yield lead

    # --------------------------------------------------------------------------
    # Helpers làm sạch & phân tích text
    # --------------------------------------------------------------------------

    @staticmethod
    def _clean_html_to_text(html_content: str) -> str:
        """Chuyển HTML thành văn bản đa dòng sạch sẽ, giữ nguyên phân cách logic."""
        if not html_content:
            return ""
        # Thay thẻ ngắt dòng và đóng khối thành newline (hỗ trợ mọi thẻ <br> có style hoặc thuộc tính)
        text = re.sub(r"(?i)<br\b[^>]*>", "\n", html_content)
        text = re.sub(r"(?i)</(?:div|p|tr|li|h[1-6])>", "\n", text)
        # Xóa các thẻ HTML còn lại
        text = re.sub(r"<[^>]+>", " ", text)
        # Xóa các ký tự zero-width & non-breaking space
        text = re.sub(r"[\ufeff\u200b\u200c\u200d]", "", text)
        text = text.replace("\xa0", " ")
        text = unicodedata.normalize("NFKC", text)
        text = html.unescape(text)
        # Chuẩn hóa khoảng trắng mỗi dòng
        lines = [re.sub(r"\s+", " ", l).strip() for l in text.split("\n")]
        return "\n".join([l for l in lines if l])

    @staticmethod
    def _clean_text(s: str) -> str:
        """Làm sạch ký tự unicode ẩn và khoảng trắng thừa."""
        if not s:
            return ""
        s = re.sub(r"[\ufeff\u200b\u200c\u200d]", "", s)
        s = s.replace("\xa0", " ")
        s = unicodedata.normalize("NFKC", s)
        s = html.unescape(s)
        return re.sub(r"\s+", " ", s).strip()

    @staticmethod
    def _clean_company_name(name: str) -> str:
        """Loại bỏ ký tự lạ, dấu sao, khoảng trắng thừa trong tên công ty."""
        if not name:
            return ""
        cleaned = VietnamTextileSpider._clean_text(name)
        cleaned = re.sub(r"^[\d\.\-\s]+", "", cleaned)  # Bỏ số thứ tự đầu dòng
        cleaned = cleaned.strip(" *-\t\n\r.")
        return cleaned

    @staticmethod
    def _is_field_label(line: str) -> bool:
        """Kiểm tra xem dòng có phải là nhãn trường dữ liệu hay không."""
        labels = [
            "địa chỉ:",
            "address:",
            "trụ sở:",
            "trụ sở chính:",
            "điện thoại:",
            "sđt:",
            "tel:",
            "phone:",
            "mobile:",
            "đt:",
            "hotline:",
            "fax:",
            "email:",
            "website:",
            "web:",
            "giám đốc:",
            "tổng giám đốc:",
            "chủ tịch:",
            "người đại diện:",
            "đại diện công ty:",
            "hoạt động chính:",
            "ngành nghề:",
            "sản phẩm chính:",
            "tên công ty:",
        ]

        low = line.lower()
        return any(low.startswith(lb) for lb in labels)

    @staticmethod
    def _extract_value_or_line(line: str, pattern: str) -> str:
        match = re.search(pattern, line, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return line.strip()

    @staticmethod
    def _split_and_clean_phones(raw: str) -> list[str]:
        """Tách các số điện thoại ghép bằng / hoặc ; hoặc dấu phẩy hoặc dấu gạch ngang phân cách."""
        if not raw:
            return []
        parts = re.split(r"[/,;]|\s+[-–—]\s+", raw)
        results: list[str] = []
        base_prefix = ""


        # Tìm tiền tố mã vùng nếu có trong chuỗi gốc, ví dụ: '(84-8)', '028', '(024)'
        area_code_match = re.match(r"^(\(?\+?84[\s\-\.]*\d+\)?|\(?0\d{2,3}\)?[\s\.\-]*)", raw.strip())
        area_code_prefix = area_code_match.group(1).strip() if area_code_match else ""

        for idx, part in enumerate(parts):
            p = part.strip()
            if not p:
                continue
            # Nếu phần sau là số đuôi ngắn (ví dụ: '028 39103878/79')
            if idx > 0 and len(p) <= 4 and base_prefix and len(base_prefix) > len(p):
                # Thay số đuôi vào số trước
                full_num = base_prefix[:-len(p)] + p
                results.append(full_num)
            elif idx > 0 and area_code_prefix and not re.match(r"^(\(?\+?84|\(?0\d)", p):
                # Số sau thiếu mã vùng: bổ sung mã vùng từ số trước
                sep = " " if not area_code_prefix.endswith((" ", "-", ".")) else ""
                full_num = f"{area_code_prefix}{sep}{p}"
                results.append(full_num)
                base_prefix = full_num
            else:
                base_prefix = p
                results.append(p)

        return results

