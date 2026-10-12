"""
Unit tests cho VasepSpider bao gồm tính năng crawl_all (cào tất cả các trang).
"""

from __future__ import annotations

import pytest
from scrapy.http import HtmlResponse, Request

from leadharvest.spiders.vasep import VasepSpider


def test_vasep_spider_init_default():
    """Kiểm tra khởi tạo mặc định: cào từ trang 1 đến 10, crawl_all=False."""
    spider = VasepSpider()
    assert spider.crawl_all is False
    assert spider.start_page == 1
    assert spider.end_page == 10
    assert len(spider.start_urls) == 10
    assert spider.start_urls[0] == "https://vasep.com.vn/hoi-vien?page=1"
    assert spider.start_urls[-1] == "https://vasep.com.vn/hoi-vien?page=10"


def test_vasep_spider_init_custom_range():
    """Kiểm tra khởi tạo với khoảng trang tùy chỉnh."""
    spider = VasepSpider(start_page="2", end_page="5")
    assert spider.crawl_all is False
    assert spider.start_page == 2
    assert spider.end_page == 5
    assert len(spider.start_urls) == 4
    assert spider.start_urls[0] == "https://vasep.com.vn/hoi-vien?page=2"
    assert spider.start_urls[-1] == "https://vasep.com.vn/hoi-vien?page=5"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"crawl_all": True},
        {"crawl_all": "true"},
        {"crawl_all": "1"},
        {"all": "true"},
        {"all_pages": "true"},
        {"end_page": "all"},
        {"end_page": "max"},
    ],
)
def test_vasep_spider_init_crawl_all_options(kwargs):
    """Kiểm tra các biến thể tham số bật option crawl_all."""
    spider = VasepSpider(**kwargs)
    assert spider.crawl_all is True
    assert spider.start_page == 1
    assert len(spider.start_urls) == 1
    assert spider.start_urls[0] == "https://vasep.com.vn/hoi-vien?page=1"


def test_vasep_spider_parse_without_crawl_all():
    """Khi crawl_all=False, spider parse trang danh sách nhưng không yield request sang trang kế tiếp."""
    spider = VasepSpider(start_page=1, end_page=2)
    html_content = """
    <html>
        <body>
            <div class="xitem">
                <a href="/hoi-vien/thong-tin/cong-ty-a-1.html">
                    <span class="xtitle">CÔNG TY TNHH A</span>
                </a>
            </div>
            <div class="pagination text-center">
                <a href="https://vasep.com.vn/hoi-vien?page=1" class="active">1</a>
                <a href="https://vasep.com.vn/hoi-vien?page=2">2</a>
                <a id="dnn_ctr4087_Main_ctl00_vbPaging_btnNext" href="https://vasep.com.vn/hoi-vien?page=6">Trang sau</a>
            </div>
        </body>
    </html>
    """
    request = Request(url="https://vasep.com.vn/hoi-vien?page=1")
    response = HtmlResponse(
        url="https://vasep.com.vn/hoi-vien?page=1",
        body=html_content.encode("utf-8"),
        encoding="utf-8",
        request=request,
    )

    results = list(spider.parse(response))
    # Chỉ có 1 request chi tiết công ty A, không có request phân trang
    assert len(results) == 1
    assert results[0].url == "https://vasep.com.vn/hoi-vien/thong-tin/cong-ty-a-1.html"
    assert results[0].callback == spider.parse_detail


def test_vasep_spider_parse_with_crawl_all_yields_next_page():
    """Khi crawl_all=True, spider yield request chi tiết VÀ request chuyển sang trang tiếp theo."""
    spider = VasepSpider(crawl_all=True)
    html_content = """
    <html>
        <body>
            <div class="xitem">
                <a href="/hoi-vien/thong-tin/cong-ty-a-1.html">
                    <span class="xtitle">CÔNG TY TNHH A</span>
                </a>
            </div>
            <div class="xitem">
                <a href="/hoi-vien/thong-tin/cong-ty-b-2.html">
                    <span class="xtitle">CÔNG TY CỔ PHẦN B</span>
                </a>
            </div>
            <div class="pagination text-center">
                <a href="https://vasep.com.vn/hoi-vien?page=1" class="active">1</a>
                <a href="https://vasep.com.vn/hoi-vien?page=2">2</a>
                <a id="dnn_ctr4087_Main_ctl00_vbPaging_btnNext" href="https://vasep.com.vn/hoi-vien?page=6">Trang sau</a>
            </div>
        </body>
    </html>
    """
    request = Request(url="https://vasep.com.vn/hoi-vien?page=1")
    response = HtmlResponse(
        url="https://vasep.com.vn/hoi-vien?page=1",
        body=html_content.encode("utf-8"),
        encoding="utf-8",
        request=request,
    )

    results = list(spider.parse(response))
    # 2 detail requests + 1 next page request (page=2)
    assert len(results) == 3
    detail_urls = [r.url for r in results if r.callback == spider.parse_detail]
    next_page_reqs = [r for r in results if r.callback == spider.parse]

    assert len(detail_urls) == 2
    assert "https://vasep.com.vn/hoi-vien/thong-tin/cong-ty-a-1.html" in detail_urls
    assert "https://vasep.com.vn/hoi-vien/thong-tin/cong-ty-b-2.html" in detail_urls

    assert len(next_page_reqs) == 1
    assert next_page_reqs[0].url == "https://vasep.com.vn/hoi-vien?page=2"
    assert next_page_reqs[0].meta.get("page") == 2


def test_vasep_spider_parse_with_crawl_all_stops_at_last_page():
    """Khi crawl_all=True và đang ở trang cuối cùng (không có nút next và page >= max_seen), dừng phân trang."""
    spider = VasepSpider(crawl_all=True)
    html_content = """
    <html>
        <body>
            <div class="xitem">
                <a href="/hoi-vien/thong-tin/cong-ty-cuoi-16.html">
                    <span class="xtitle">CÔNG TY CUỐI CÙNG</span>
                </a>
            </div>
            <div class="pagination text-center">
                <a href="https://vasep.com.vn/hoi-vien?page=11">Trang trước</a>
                <a href="https://vasep.com.vn/hoi-vien?page=16" class="active">16</a>
            </div>
        </body>
    </html>
    """
    request = Request(url="https://vasep.com.vn/hoi-vien?page=16")
    response = HtmlResponse(
        url="https://vasep.com.vn/hoi-vien?page=16",
        body=html_content.encode("utf-8"),
        encoding="utf-8",
        request=request,
    )

    results = list(spider.parse(response))
    # Chỉ yield 1 detail request, KHÔNG yield request sang page 17
    assert len(results) == 1
    assert results[0].url == "https://vasep.com.vn/hoi-vien/thong-tin/cong-ty-cuoi-16.html"
    assert results[0].callback == spider.parse_detail


def test_vasep_spider_parse_empty_page_stops():
    """Khi gặp trang không có thẻ .xitem nào, dừng ngay lập tức."""
    spider = VasepSpider(crawl_all=True)
    html_content = """
    <html>
        <body>
            <div class="container">
                <p>Không có dữ liệu</p>
            </div>
        </body>
    </html>
    """
    request = Request(url="https://vasep.com.vn/hoi-vien?page=17")
    response = HtmlResponse(
        url="https://vasep.com.vn/hoi-vien?page=17",
        body=html_content.encode("utf-8"),
        encoding="utf-8",
        request=request,
    )

    results = list(spider.parse(response))
    assert len(results) == 0


def test_vasep_spider_save_folder_param():
    """Kiểm tra khởi tạo spider với save_folder."""
    spider = VasepSpider(save_folder="data/my_custom_folder")
    assert spider.save_folder == "data/my_custom_folder"

    # Alias save_dir
    spider2 = VasepSpider(save_dir="data/another_folder")
    assert spider2.save_folder == "data/another_folder"


def test_raw_lead_storage_pipeline_custom_save_folder(tmp_path):
    """Kiểm tra RawLeadStoragePipeline ghi file vào đúng thư mục save_folder được chỉ định."""
    from leadharvest.pipelines import RawLeadStoragePipeline
    from leadharvest.models.raw_lead import RawLead

    custom_dir = str(tmp_path / "custom_raw")
    spider = VasepSpider(save_folder=custom_dir)

    pipeline = RawLeadStoragePipeline()
    pipeline.open_spider(spider)

    lead = spider.make_raw_lead(
        company_name="TEST COMPANY",
        raw_phone="0912345678",
        source_url="https://vasep.com.vn/hoi-vien/thong-tin/test.html",
    )
    pipeline.process_item(lead, spider)
    pipeline.close_spider(spider)

    expected_file = tmp_path / "custom_raw" / "vasep.jsonl"
    assert expected_file.exists()
    content = expected_file.read_text(encoding="utf-8")
    assert "TEST COMPANY" in content
    assert "https://vasep.com.vn/hoi-vien/thong-tin/test.html" in content


def test_vasep_spider_save_file_param():
    """Kiểm tra khởi tạo spider với save_file / filename."""
    spider = VasepSpider(save_file="vasep_dot1.jsonl")
    assert spider.save_file == "vasep_dot1.jsonl"

    spider2 = VasepSpider(filename="vasep_custom")
    assert spider2.save_file == "vasep_custom"


def test_raw_lead_storage_pipeline_custom_save_file(tmp_path):
    """Kiểm tra RawLeadStoragePipeline ghi file vào đúng save_file được chỉ định."""
    from leadharvest.pipelines import RawLeadStoragePipeline

    # Trường hợp 1: Đường dẫn đầy đủ
    full_path_file = str(tmp_path / "custom_batch" / "output.jsonl")
    spider1 = VasepSpider(save_file=full_path_file)
    pipeline1 = RawLeadStoragePipeline()
    pipeline1.open_spider(spider1)

    lead1 = spider1.make_raw_lead(
        company_name="COMPANY 1",
        raw_phone="0911111111",
        source_url="https://vasep.com.vn/hoi-vien/thong-tin/1.html",
    )
    pipeline1.process_item(lead1, spider1)
    pipeline1.close_spider(spider1)

    assert (tmp_path / "custom_batch" / "output.jsonl").exists()

    # Trường hợp 2: Chỉ truyền tên file không có đuôi mở rộng
    spider2 = VasepSpider(save_file="custom_batch_2", save_folder=str(tmp_path))
    pipeline2 = RawLeadStoragePipeline()
    pipeline2.open_spider(spider2)

    lead2 = spider2.make_raw_lead(
        company_name="COMPANY 2",
        raw_phone="0922222222",
        source_url="https://vasep.com.vn/hoi-vien/thong-tin/2.html",
    )
    pipeline2.process_item(lead2, spider2)
    pipeline2.close_spider(spider2)

    expected_file2 = tmp_path / "custom_batch_2.jsonl"
    assert expected_file2.exists()
    assert "COMPANY 2" in expected_file2.read_text(encoding="utf-8")


