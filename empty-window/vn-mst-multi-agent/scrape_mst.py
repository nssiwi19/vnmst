import asyncio
import aiohttp
import xml.etree.ElementTree as ET
import re
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')

SITEMAP_INDEX_URL = "https://hsctvn.com/sitemap/sitemap.xml"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

async def fetch_xml(session, url):
    """Tải nội dung file XML"""
    try:
        async with session.get(url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=30)) as response:
            if response.status == 200:
                return await response.text()
            else:
                logging.error(f"Lỗi {response.status} khi tải: {url}")
                return None
    except Exception as e:
        logging.error(f"Lỗi mạng khi tải {url}: {e}")
        return None

async def parse_sitemap():
    logging.info(f"Đang tải Sitemap Index: {SITEMAP_INDEX_URL}")
    mst_set = set() # Dùng Set để tự động lọc trùng MST
    
    async with aiohttp.ClientSession() as session:
        # 1. Tải sitemap gốc
        index_xml = await fetch_xml(session, SITEMAP_INDEX_URL)
        if not index_xml: return
        
        # Parse XML (Bỏ qua namespace để dễ tìm thẻ)
        index_xml = re.sub(r'\sxmlns="[^"]+"', '', index_xml, count=1)
        root = ET.fromstring(index_xml)
        
        # 2. Tìm tất cả các file sitemap con (sitemap-1.xml, sitemap-2.xml...)
        sub_sitemaps = [loc.text for loc in root.findall('.//loc') if loc.text.endswith('.xml')]
        logging.info(f"Tìm thấy {len(sub_sitemaps)} file sitemap con.")
        
        if not sub_sitemaps:
            # Nếu sitemap.xml chứa luôn link .htm thì đưa nó vào list luôn
            sub_sitemaps = [SITEMAP_INDEX_URL]
            
        # 3. Duyệt qua từng sitemap con để lấy MST
        for sitemap_url in sub_sitemaps:
            logging.info(f"Đang quét dữ liệu từ: {sitemap_url}")
            xml_content = await fetch_xml(session, sitemap_url)
            
            if xml_content:
                # Tìm tất cả các link .htm trong sitemap
                urls = re.findall(r'<loc>(.*?)</loc>', xml_content)
                for url in urls:
                    # Dùng Regex lấy đoạn số cuối cùng trước .htm (độ dài 10 hoặc 13 số)
                    # Phù hợp với format: .../ten-cong-ty-0101248141.htm
                    match = re.search(r'-([0-9]{10,13})\.htm', url)
                    if match:
                        mst_set.add(match.group(1))
            
            # Nếu đã đủ 120k (100k chuẩn + 20k dự phòng) thì dừng sớm cho nhẹ máy
            if len(mst_set) > 120000:
                logging.info("Đã đạt mốc 120,000 Mã số thuế. Dừng quét!")
                break
                
    # 4. Lưu ra file txt
    output_path = 'seed_mst.txt'
    with open(output_path, 'w', encoding='utf-8') as f:
        for mst in mst_set:
            f.write(f"{mst}\n")
            
    logging.info(f"✅ HOÀN TẤT! Đã lưu {len(mst_set)} Mã số thuế vào file {output_path}")

if __name__ == "__main__":
    asyncio.run(parse_sitemap())
