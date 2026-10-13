"""
Unit tests cho VietnamTextileSpider (Hiệp hội Dệt may Việt Nam - VITAS).

Kiểm tra:
- Khởi tạo spider & cấu hình mặc định (phân khúc Dệt may, source_name VITAS).
- Phân tích danh sách hội viên trên trang listing (thẻ a[href*="DanhBa.aspx"]).
- Phân tích chi tiết hội viên với các định dạng khác nhau:
  + ID 51: Công ty TNHH MTV 28.1 (Mẫu người dùng cung cấp - định dạng từng div riêng)
  + ID 517: Công ty Cổ phần Đầu tư Q&T (Định dạng br, có tiếng Anh, Giám đốc, Hoạt động chính)
  + ID 513: CÔNG TY TNHH TRƯỜNG PHÁT TOÀN CẦU (Có website, Chủ tịch, Tỉnh Thanh Hóa)
- Chuẩn hóa RawLead thành LeadOutput hợp lệ đưa vào tab Dệt may.
"""

from __future__ import annotations

import pytest
from scrapy.http import HtmlResponse, Request

from leadharvest.models.enums import Segment
from leadharvest.models.raw_lead import RawLead
from leadharvest.processing.normalizer import normalize_raw_lead
from leadharvest.spiders.vietnamtextile import VietnamTextileSpider


def test_vietnamtextile_spider_init():
    """Kiểm tra cấu hình khởi tạo của VietnamTextileSpider."""
    spider = VietnamTextileSpider()
    assert spider.name == "vietnamtextile"
    assert spider.source_name == "VITAS"
    assert spider.default_segment == Segment.DET_MAY.value
    assert spider.allowed_domains == ["vietnamtextile.org.vn"]
    assert len(spider.start_urls) == 1
    assert "hoi-vien-vitas" in spider.start_urls[0]


def test_clean_text_and_company_name():
    """Kiểm tra làm sạch ký tự ẩn, số thứ tự và khoảng trắng thừa."""
    raw = "\ufeff  12. CÔNG TY TNHH TORAY INTERNATIONAL VIỆT NAM\u200b  * "
    cleaned = VietnamTextileSpider._clean_company_name(raw)
    assert cleaned == "CÔNG TY TNHH TORAY INTERNATIONAL VIỆT NAM"


def test_split_and_clean_phones():
    """Kiểm tra tách số điện thoại ghép."""
    spider = VietnamTextileSpider()
    # Trường hợp số bàn ghép số đuôi
    phones1 = spider._split_and_clean_phones("(84-8) 38940914/38944750")
    assert "(84-8) 38940914" in phones1
    assert "(84-8) 38944750" in phones1

    # Trường hợp 2 số độc lập
    phones2 = spider._split_and_clean_phones("0912345678 / 0987654321")
    assert len(phones2) == 2
    assert "0912345678" in phones2
    assert "0987654321" in phones2


def test_parse_listing_page():
    """Kiểm tra trích xuất danh sách hội viên và link phân trang từ HTML listing."""
    spider = VietnamTextileSpider()
    html_content = """
    <html>
    <body>
        <div class="pl_display_list">
            <a href="/DanhBa.aspx?i=517"><img src="logo1.jpg" /></a>
            <a href="/DanhBa.aspx?i=517">Công ty Cổ phần Đầu tư Q&amp;T</a>

            <a href="/DanhBa.aspx?i=51"><img src="logo2.jpg" /></a>
            <a href="/DanhBa.aspx?i=51">Công ty TNHH MTV 28.1</a>
        </div>
        <div class="pagination">
            <a href="/hoi-vien-vitas_p1_1-1_2-1_3-676_9-2_11-20_12-2_13-402.html#a_list_target">2</a>
            <a href="/hoi-vien-vitas_p1_1-1_2-1_3-676_9-2_11-20_12-3_13-402.html#a_list_target">3</a>
        </div>
    </body>
    </html>
    """
    request = Request(url="http://www.vietnamtextile.org.vn/hoi-vien-vitas_p1_1-1_2-1_3-676.html")
    response = HtmlResponse(
        url="http://www.vietnamtextile.org.vn/hoi-vien-vitas_p1_1-1_2-1_3-676.html",
        body=html_content.encode("utf-8"),
        encoding="utf-8",
        request=request,
    )

    results = list(spider.parse(response))
    # 2 requests chi tiết + 2 requests phân trang (trang 2 và trang 3)
    detail_reqs = [r for r in results if "DanhBa.aspx" in r.url]
    page_reqs = [r for r in results if "_12-" in r.url]

    assert len(detail_reqs) == 2
    assert any("i=517" in r.url and r.meta["company_name"] == "Công ty Cổ phần Đầu tư Q&T" for r in detail_reqs)
    assert any("i=51" in r.url and r.meta["company_name"] == "Công ty TNHH MTV 28.1" for r in detail_reqs)

    assert len(page_reqs) == 2
    assert any("12-2" in r.url for r in page_reqs)
    assert any("12-3" in r.url for r in page_reqs)


def test_parse_detail_sample_51():
    """Kiểm tra bóc tách chi tiết URL sample mẫu i=51 (Công ty TNHH MTV 28.1)."""
    spider = VietnamTextileSpider()
    html_content = """
    <html>
    <head><title>Công ty TNHH MTV 28.1</title></head>
    <body>
        <div id="content_ptab_1" class="pl_c">
            <div style="padding-top:10px;">
                <h1>Công ty TNHH MTV 28.1</h1>
                <div class="wrap-about">
                    <div>Địa chỉ: 03 Nguyễn Oanh, Phường 10, Quận Gò Vấp, TP. HCM</div>
                    <div>Điện thoại: (84-8) 38940914/38944750\xa0 - Fax: (84-8) 38941668</div>
                    <div>Email: tuananh@agtex28-1.com</div>
                    <div>Công ty TNHH MTV 28.1 là công ty con với 100% vốn của Tổng công ty, chuyên sản xuất các sản phẩm veston nam và nữ chất lượng cao. Hiện tại có 2 xưởng may với hơn 1000 công nhân.</div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    url = "http://www.vietnamtextile.org.vn/DanhBa.aspx?i=51"
    request = Request(url=url, meta={"company_name": "Công ty TNHH MTV 28.1"})
    response = HtmlResponse(url=url, body=html_content.encode("utf-8"), encoding="utf-8", request=request)

    leads = list(spider.parse_detail(response))
    assert len(leads) == 1
    lead: RawLead = leads[0]

    assert lead.company_name == "Công ty TNHH MTV 28.1"
    assert lead.target_segment == Segment.DET_MAY.value
    assert lead.province == "Hồ Chí Minh"
    assert "03 Nguyễn Oanh" in lead.address
    assert "(84-8) 38940914" in lead.raw_phone
    assert "(84-8) 38944750" in lead.raw_phone
    assert lead.fax == "(84-8) 38941668"
    assert "tuananh@agtex28-1.com" in lead.emails
    assert lead.extra_data.get("member_id") == "51"
    assert lead.description is not None
    assert "chuyên sản xuất các sản phẩm veston nam và nữ chất lượng cao" in lead.description
    assert "Địa chỉ: 03 Nguyễn Oanh" in lead.description


def test_parse_detail_sample_517():
    """Kiểm tra bóc tách chi tiết URL sample i=517 (Công ty Cổ phần Đầu tư Q&T)."""
    spider = VietnamTextileSpider()
    html_content = """
    <html>
    <body>
        <div id="content_ptab_1" class="pl_c">
            <div style="padding-top:10px;">
                <strong>Công ty Cổ phần Đầu tư Q&amp;T﻿<br>Q&amp;T Investment Joint Stock Company﻿﻿﻿﻿﻿﻿</strong><br><br>
                <strong>Địa chỉ:</strong> Lô 379 No5- LK 20, Khu dịch vụ Văn La, Phường Kiến Hưng, Thành phố Hà Nội, Việt Nam﻿﻿﻿<br>
                <strong>Email: </strong>hdkt2007@gmail.com﻿﻿﻿﻿﻿﻿<br>
                <strong>SĐT: </strong>0243 355 2731﻿﻿﻿﻿﻿﻿<br>
                <strong>Hoạt động chính:</strong> lĩnh vực điện tử viễn thông, truyền thanh, Cụm công nghiệp﻿<br>
                <strong>Giám đốc: </strong>Nguyễn Ngọc Quý﻿<br><br>
                <strong>Q&amp;T</strong> là Công ty hoạt động về lĩnh vực điện tử viễn thông, truyền thanh, Cụm công nghiệp.﻿<br>
            </div>
        </div>
    </body>
    </html>
    """
    url = "http://www.vietnamtextile.org.vn/DanhBa.aspx?i=517"
    request = Request(url=url, meta={"company_name": "Công ty Cổ phần Đầu tư Q&T"})
    response = HtmlResponse(url=url, body=html_content.encode("utf-8"), encoding="utf-8", request=request)

    leads = list(spider.parse_detail(response))
    assert len(leads) == 1
    lead: RawLead = leads[0]

    assert lead.company_name == "Công ty Cổ phần Đầu tư Q&T"
    assert lead.province == "Hà Nội"
    assert "Lô 379 No5- LK 20" in lead.address
    assert "hdkt2007@gmail.com" in lead.emails
    assert "0243 355 2731" in lead.raw_phone
    assert lead.contact_person == "Nguyễn Ngọc Quý"
    assert "lĩnh vực điện tử viễn thông" in lead.description
    assert lead.extra_data.get("english_name") == "Q&T Investment Joint Stock Company"


def test_parse_detail_sample_513():
    """Kiểm tra bóc tách chi tiết URL i=513 (Công ty TNHH Trường Phát Toàn Cầu)."""
    spider = VietnamTextileSpider()
    html_content = """
    <html>
    <body>
        <div id="content_ptab_1" class="pl_c">
            <h1>CÔNG TY TNHH TRƯỜNG PHÁT TOÀN CẦU</h1>
            <strong>TRUONG PHAT GLOBAL COMPANY LIMITED</strong><br>
            <strong>Địa chỉ:</strong> Số 668 Thôn Xuân Thành, Xã Nông Cống, Tỉnh Thanh Hóa<br>
            <strong>Email:</strong> jacksonnguyen@tpgarments.com<br>
            <strong>SĐT:</strong> 0921333299<br>
            <strong>Website:</strong> www.tpgarments.com<br>
            <strong>Hoạt động chính:</strong> sản xuất hàng may mặc: áo, quần, váy, tất<br>
            <strong>Chủ tịch:</strong> Nguyễn Thanh Hải<br>
        </div>
    </body>
    </html>
    """
    url = "http://www.vietnamtextile.org.vn/DanhBa.aspx?i=513"
    request = Request(url=url, meta={"company_name": "CÔNG TY TNHH TRƯỜNG PHÁT TOÀN CẦU"})
    response = HtmlResponse(url=url, body=html_content.encode("utf-8"), encoding="utf-8", request=request)

    leads = list(spider.parse_detail(response))
    assert len(leads) == 1
    lead: RawLead = leads[0]

    assert lead.company_name == "CÔNG TY TNHH TRƯỜNG PHÁT TOÀN CẦU"
    assert lead.province == "Thanh Hóa"
    assert "Thôn Xuân Thành" in lead.address
    assert lead.raw_phone == "0921333299"
    assert "jacksonnguyen@tpgarments.com" in lead.emails
    assert lead.website == "https://www.tpgarments.com"
    assert lead.contact_person == "Nguyễn Thanh Hải"


def test_parse_detail_sample_124_excluded_university():
    """Kiểm tra spider tự động BỎ QUA trường đại học (Trường ĐH Nguyễn Tất Thành - ID 124)."""
    spider = VietnamTextileSpider()
    html_content = """
    <html>
    <body>
        <div id="content_ptab_1" class="pl_c">
            <p><strong>Trường Đại học Nguyễn Tất Thành<br></strong><br>
            <b>Trụ sở chính</b>: 300A Nguyễn Tất Thành, Phường 13, Quận 4, TP.HCM<br>
            Đt: 84-8-62619423<br>
            Fax: 84-8-39404759<br>
            Email: info@ntt.edu.vn<br>
            Web: www.ntt.edu.vn</p>
        </div>
    </body>
    </html>
    """
    url = "http://www.vietnamtextile.org.vn/DanhBa.aspx?i=124"
    request = Request(url=url, meta={"company_name": "Trường ĐH Nguyễn Tất Thành"})
    response = HtmlResponse(url=url, body=html_content.encode("utf-8"), encoding="utf-8", request=request)

    leads = list(spider.parse_detail(response))
    # Phải bị loại bỏ hoàn toàn (không yield RawLead nào)
    assert len(leads) == 0


def test_is_excluded_organization():
    """Kiểm tra nhận diện và loại bỏ trường đại học, cao đẳng, học viện, ngân hàng."""
    spider = VietnamTextileSpider()
    # Các đơn vị trường học / đào tạo
    assert spider.is_excluded_organization("Trường ĐH Nguyễn Tất Thành") is True
    assert spider.is_excluded_organization("Trường Đại học Bách Khoa Hà Nội") is True
    assert spider.is_excluded_organization("Đại học Sư phạm Kỹ thuật Hưng Yên") is True
    assert spider.is_excluded_organization("Trường Cao đẳng Công nghệ Dệt May") is True
    assert spider.is_excluded_organization("Học viện Nông nghiệp Việt Nam") is True
    assert spider.is_excluded_organization("Hanoi Textile University") is True

    # Các đơn vị ngân hàng / tín dụng
    assert spider.is_excluded_organization("Ngân hàng TMCP Quân đội") is True
    assert spider.is_excluded_organization("Ngân hàng Thương mại Cổ phần Sài Gòn – Hà Nội") is True
    assert spider.is_excluded_organization("Ngân hàng Nông nghiệp và Phát triển Nông thôn") is True
    assert spider.is_excluded_organization("Vietcombank") is True
    assert spider.is_excluded_organization("Quỹ tín dụng nhân dân") is True

    # Các doanh nghiệp sản xuất kinh doanh B2B thông thường (KHÔNG bị loại)
    assert spider.is_excluded_organization("Công ty Cổ phần Đầu tư Q&T") is False
    assert spider.is_excluded_organization("Công ty TNHH MTV 28.1") is False
    assert spider.is_excluded_organization("Công ty Cổ phần May Kinh Bắc") is False
    assert spider.is_excluded_organization("Công ty TNHH May Xuất khẩu Việt Tiến") is False


def test_parse_detail_sample_95_tan_xuan():
    """Kiểm tra bóc tách chi tiết địa chỉ 37 Tân Xuân, Tel, Fax, Mobile gạch ngang và thẻ br có style (ID 95)."""
    spider = VietnamTextileSpider()
    html_content = """
    <html>
    <body>
        <div id="content_ptab_1" class="pl_c">
            <div style="font-family: Arial; text-align: center;">
                <b style="font-family: Tahoma;"><span style="font-size: x-large;">CÔNG TY TNHH TM DV LÂM ANH</span></b>
                <br style="font-family: Tahoma;">
            </div>
            <div>
                <span style="font-size: medium;">Địa chỉ: 37 Tân Xuân,Phường 8, Q.Tân Bình, HCM </span>
                <br style="font-size: medium;">
                <span style="font-size: medium;">Tel: (08)39 717 816 </span>
                <br style="font-size: medium;">
                <span style="font-size: medium;">Fax: (08)39 717 816 </span>
                <br style="font-size: medium;">
                <span style="font-size: medium;">Mobile: 0903 805 632 - 0942 669 669 </span>
                <br>
            </div>
            <div>
                CÔNG TY TNHH SX TM DV LÂM ANH hoạt động trong ngành dệt may trên 20 năm.
                <br>
                Đại diện Công ty: Bà
                <br>
                NGUYỄN QUẾ HƯƠNG
                <br>
                Giám đốc kiêm Chủ Tịch Hội Đồng Thành Viên.
            </div>
        </div>
    </body>
    </html>
    """
    url = "http://www.vietnamtextile.org.vn/DanhBa.aspx?i=95"
    request = Request(url=url, meta={"company_name": "CÔNG TY TNHH TM DV LÂM ANH"})
    response = HtmlResponse(url=url, body=html_content.encode("utf-8"), encoding="utf-8", request=request)

    leads = list(spider.parse_detail(response))
    assert len(leads) == 1
    lead: RawLead = leads[0]

    assert lead.company_name == "CÔNG TY TNHH TM DV LÂM ANH"
    assert lead.province == "Hồ Chí Minh"
    assert "37 Tân Xuân" in lead.address
    assert "Tel:" not in lead.address  # Địa chỉ không bị dính Tel/Fax/Mobile
    assert "(08)39 717 816" in lead.raw_phone
    assert "0903 805 632" in lead.raw_phone
    assert "0942 669 669" in lead.raw_phone
    assert lead.fax == "(08)39 717 816"
    assert lead.contact_person == "NGUYỄN QUẾ HƯƠNG"
    assert lead.description is not None
    assert "hoạt động trong ngành dệt may trên 20 năm" in lead.description
    assert "NGUYỄN QUẾ HƯƠNG" in lead.description
    assert "Giám đốc kiêm Chủ Tịch Hội Đồng Thành Viên" in lead.description





def test_vietnamtextile_normalizer_integration():
    """Kiểm tra tích hợp Normalizer đưa lead VITAS vào phân khúc Dệt may chuẩn BA."""
    raw = RawLead(
        company_name="CÔNG TY TNHH MAY XUẤT KHẨU VIỆT TIẾN",
        target_segment=Segment.DET_MAY.value,
        contact_person="Vũ Đức Giang",
        raw_phone="028 38640800 / 0903123456",
        emails=["viettien@viettien.com.vn"],
        website="https://viettien.com.vn",
        address="07 Lê Minh Xuân, Phường 7, Quận Tân Bình, TP. Hồ Chí Minh",
        source_name="VITAS",
        source_url="http://www.vietnamtextile.org.vn/DanhBa.aspx?i=1",
    )

    res = normalize_raw_lead(raw)
    assert res.lead is not None
    lead_out = res.lead
    assert lead_out.target_segment == Segment.DET_MAY.value
    assert lead_out.company_name == "CÔNG TY TNHH MAY XUẤT KHẨU VIỆT TIẾN"
    assert lead_out.contact_person == "Vũ Đức Giang"
    assert lead_out.province == "Hồ Chí Minh"
    assert lead_out.phone_primary is not None
    assert lead_out.has_mobile is True  # Có số 0903123456
    assert lead_out.richness_score() >= 80


