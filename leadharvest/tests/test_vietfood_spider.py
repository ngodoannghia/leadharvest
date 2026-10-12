"""
Unit tests cho VietfoodSpider (Hiệp hội Lương thực Việt Nam - VFA).

Kiểm tra:
- Khởi tạo spider & cấu hình mặc định (phân khúc Nông sản, source_name VIETFOOD).
- Phân tích danh sách hội viên trên trang listing (ol.display-posts-listing).
- Phân tích chi tiết hội viên (trang thực tế: Hà Bắc, Vinafood 1, Tân Cảng...).
- Chuẩn hóa RawLead thành LeadOutput hợp lệ theo BA §6.
"""

from __future__ import annotations

import os
from pathlib import Path
import pytest
from scrapy.http import HtmlResponse, Request

from leadharvest.models.enums import Segment
from leadharvest.models.raw_lead import RawLead
from leadharvest.processing.normalizer import normalize_raw_lead
from leadharvest.spiders.vietfood import VietfoodSpider

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_vietfood_spider_init():
    """Kiểm tra cấu hình khởi tạo của VietfoodSpider."""
    spider = VietfoodSpider()
    assert spider.name == "vietfood"
    assert spider.source_name == "VIETFOOD"
    assert spider.default_segment == Segment.NONG_SAN.value
    assert spider.allowed_domains == ["vietfood.org.vn"]
    assert len(spider.start_urls) == 1
    assert "https://vietfood.org.vn/hoi-vien/danh-sach-hoi-vien/" in spider.start_urls[0]


def test_clean_company_name():
    """Kiểm tra hàm xóa dấu '*' hội viên liên kết và khoảng trắng thừa."""
    assert VietfoodSpider._clean_company_name("CTY CỔ PHẦN LƯƠNG THỰC HÀ BẮC") == "CTY CỔ PHẦN LƯƠNG THỰC HÀ BẮC"
    assert VietfoodSpider._clean_company_name("NGÂN HÀNG QUÂN ĐỘI*") == "NGÂN HÀNG QUÂN ĐỘI"
    assert VietfoodSpider._clean_company_name("CÔNG TY TNHH AARNA AGRO VIỆT NAM* ") == "CÔNG TY TNHH AARNA AGRO VIỆT NAM"
    assert VietfoodSpider._clean_company_name("   CÔNG TY   TNHH   CỎ MAY*   ") == "CÔNG TY TNHH CỎ MAY"


def test_parse_listing_page():
    """Kiểm tra trích xuất link và tên hội viên từ trang danh sách."""
    spider = VietfoodSpider()
    html_content = """
    <html>
    <body>
        <ol class="display-posts-listing grid">
            <li class="listing-item">
                <a class="title" href="https://vietfood.org.vn/cty-co-phan-luong-thuc-ha-bac/">CTY CỔ PHẦN LƯƠNG THỰC HÀ BẮC</a>
            </li>
            <li class="listing-item">
                <a class="title" href="https://vietfood.org.vn/tong-cty-luong-thuc-mien-bac/">TỔNG CTY LƯƠNG THỰC MIỀN BẮC</a>
            </li>
            <li class="listing-item">
                <a class="title" href="https://vietfood.org.vn/ngan-hang-tmcp-sai-gon-ha-noi/">NGÂN HÀNG THƯƠNG MẠI CỔ PHẦN SÀI GÒN – HÀ NỘI*</a>
            </li>
        </ol>
    </body>
    </html>
    """
    request = Request(url="https://vietfood.org.vn/hoi-vien/danh-sach-hoi-vien/")
    response = HtmlResponse(
        url="https://vietfood.org.vn/hoi-vien/danh-sach-hoi-vien/",
        body=html_content.encode("utf-8"),
        encoding="utf-8",
        request=request,
    )

    requests = list(spider.parse(response))
    assert len(requests) == 3

    req1 = requests[0]
    assert req1.url == "https://vietfood.org.vn/cty-co-phan-luong-thuc-ha-bac/"
    assert req1.meta["company_name"] == "CTY CỔ PHẦN LƯƠNG THỰC HÀ BẮC"

    req3 = requests[2]
    assert req3.url == "https://vietfood.org.vn/ngan-hang-tmcp-sai-gon-ha-noi/"
    # Dấu * phải được làm sạch
    assert req3.meta["company_name"] == "NGÂN HÀNG THƯƠNG MẠI CỔ PHẦN SÀI GÒN – HÀ NỘI"


def test_parse_listing_with_limit():
    """Kiểm tra tham số limit chỉ lấy số lượng hội viên chỉ định."""
    spider = VietfoodSpider(limit=2)
    html_content = """
    <html>
    <body>
        <ol class="display-posts-listing grid">
            <li class="listing-item"><a class="title" href="https://vietfood.org.vn/item-1/">Cty 1</a></li>
            <li class="listing-item"><a class="title" href="https://vietfood.org.vn/item-2/">Cty 2</a></li>
            <li class="listing-item"><a class="title" href="https://vietfood.org.vn/item-3/">Cty 3</a></li>
        </ol>
    </body>
    </html>
    """
    request = Request(url="https://vietfood.org.vn/hoi-vien/danh-sach-hoi-vien/")
    response = HtmlResponse(
        url="https://vietfood.org.vn/hoi-vien/danh-sach-hoi-vien/",
        body=html_content.encode("utf-8"),
        encoding="utf-8",
        request=request,
    )

    requests = list(spider.parse(response))
    assert len(requests) == 2


def test_parse_detail_ha_bac():
    """Kiểm tra bóc tách trang chi tiết CTY CỔ PHẦN LƯƠNG THỰC HÀ BẮC."""
    spider = VietfoodSpider()
    fixture_path = FIXTURES_DIR / "vietfood_habac_detail.html"
    assert fixture_path.exists(), f"Không tìm thấy fixture {fixture_path}"

    with open(fixture_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    target_url = "https://vietfood.org.vn/cty-co-phan-luong-thuc-ha-bac/"
    request = Request(
        url=target_url,
        meta={
            "company_name": "CTY CỔ PHẦN LƯƠNG THỰC HÀ BẮC",
            "link_detail": target_url,
        },
    )
    response = HtmlResponse(
        url=target_url,
        body=html_content.encode("utf-8"),
        encoding="utf-8",
        request=request,
    )

    leads = list(spider.parse_detail(response))
    assert len(leads) == 1
    lead: RawLead = leads[0]

    assert lead.company_name == "CTY CỔ PHẦN LƯƠNG THỰC HÀ BẮC"
    assert lead.target_segment == Segment.NONG_SAN.value
    assert lead.source_name == "VIETFOOD"
    assert lead.source_url == target_url
    assert "Bắc Ninh" in lead.address
    assert lead.province == "Bắc Ninh"
    assert "+84.204 3854335" in (lead.raw_phone or "")
    assert "luongthuchabachbf@gmail.com" in lead.emails
    assert "HA BAC FOOD JOINT STOCK COMPANY" in lead.description

    # Test chuẩn hóa sang LeadOutput
    norm_result = normalize_raw_lead(lead)
    assert norm_result.lead is not None
    assert norm_result.lead.is_valid
    assert norm_result.lead.phone_primary == "02043854335"
    assert norm_result.lead.phone_primary_type == "LANDLINE"
    assert norm_result.lead.province == "Bắc Ninh"
    assert norm_result.lead.target_segment == Segment.NONG_SAN.value


def test_parse_detail_vinafood1():
    """Kiểm tra bóc tách trang chi tiết TỔNG CTY LƯƠNG THỰC MIỀN BẮC (nhiều SĐT, fax, website)."""
    spider = VietfoodSpider()
    fixture_path = FIXTURES_DIR / "vietfood_vinafood1_detail.html"
    assert fixture_path.exists(), f"Không tìm thấy fixture {fixture_path}"

    with open(fixture_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    target_url = "https://vietfood.org.vn/tong-cty-luong-thuc-mien-bac/"
    request = Request(
        url=target_url,
        meta={
            "company_name": "TỔNG CTY LƯƠNG THỰC MIỀN BẮC",
            "link_detail": target_url,
        },
    )
    response = HtmlResponse(
        url=target_url,
        body=html_content.encode("utf-8"),
        encoding="utf-8",
        request=request,
    )

    leads = list(spider.parse_detail(response))
    assert len(leads) == 1
    lead: RawLead = leads[0]

    assert lead.company_name == "TỔNG CTY LƯƠNG THỰC MIỀN BẮC"
    assert lead.province == "Hà Nội"
    assert "6 Ngô Quyền" in lead.address
    assert "+84.24 39351572" in (lead.raw_phone or "")
    assert "+84 28 3911 8817" in (lead.raw_phone or "")
    assert "+84.24 3910 6331" in (lead.fax or "")
    assert "rice-hcm@vinafood1.vn" in lead.emails
    assert "vinafood1.com.vn" in (lead.website or "")

    # Test chuẩn hóa sang LeadOutput
    norm_result = normalize_raw_lead(lead)
    assert norm_result.lead is not None
    assert norm_result.lead.is_valid
    assert norm_result.lead.phone_primary == "02439351572"
    assert norm_result.lead.phone_secondary == "02839118817"
    assert norm_result.lead.province == "Hà Nội"


def test_parse_detail_fallback_title():
    """Kiểm tra khi meta không truyền company_name thì spider tự trích xuất từ heading h3/og:title."""
    spider = VietfoodSpider()
    html_content = """
    <html>
    <head>
        <meta property="article:tag" content="Cần Thơ">
        <meta property="og:title" content="CÔNG TY CỔ PHẦN NÔNG SẢN CẦN THƠ - Hiệp hội Lương thực Việt Nam">
    </head>
    <body>
        <div class="elementor-widget-heading">
            <h3 class="elementor-heading-title">CÔNG TY CỔ PHẦN NÔNG SẢN CẦN THƠ</h3>
        </div>
        <div class="elementor-widget-text-editor">
            <div class="elementor-text-editor">
                <p>
                Can Tho Agricultural Products JSC<br>
                Địa chỉ: KCN Trà Nóc, quận Bình Thủy, TP. Cần Thơ<br>
                Tel: 0292.3841234<br>
                Email: nongsan@cantho.vn
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    request = Request(url="https://vietfood.org.vn/cong-ty-co-phan-nong-san-can-tho/")
    response = HtmlResponse(
        url="https://vietfood.org.vn/cong-ty-co-phan-nong-san-can-tho/",
        body=html_content.encode("utf-8"),
        encoding="utf-8",
        request=request,
    )

    leads = list(spider.parse_detail(response))
    assert len(leads) == 1
    assert leads[0].company_name == "CÔNG TY CỔ PHẦN NÔNG SẢN CẦN THƠ"
    assert leads[0].province == "Cần Thơ"
    assert leads[0].raw_phone == "0292.3841234"
    assert leads[0].emails == ["nongsan@cantho.vn"]
