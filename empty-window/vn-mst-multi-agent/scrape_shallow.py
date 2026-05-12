import asyncio
import aiohttp
import re
import logging
import random

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')

# Cấu hình Headers giả lập trình duyệt xịn (Bypass cơ bản)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
    'Referer': 'https://www.google.com/',
    'Sec-Ch-Ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
    'Sec-Ch-Ua-Mobile': '?0',
    'Sec-Ch-Ua-Platform': '"Windows"',
    'Upgrade-Insecure-Requests': '1'
}

# Giới hạn luồng để không bị block 429
MAX_CONCURRENT = 10 
TOTAL_MST_NEEDED = 100000

async def fetch_page(session, semaphore, url, mst_set):
    """Truy cập trang danh mục và dùng Regex nhặt MST từ các thẻ <a>"""
    async with semaphore:
        try:
            # Độ trễ ngẫu nhiên mô phỏng người thật lật trang
            await asyncio.sleep(random.uniform(0.5, 2.0))
            
            async with session.get(url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status == 200:
                    html = await response.text()
                    
                    # Kỹ thuật bóc tách bằng Regex siêu tốc
                    # Tìm tất cả các đoạn URL có dạng: -0101248141.htm
                    matches = re.findall(r'-([0-9]{10,13})\.htm', html)
                    
                    new_count = 0
                    for mst in matches:
                        if mst not in mst_set:
                            mst_set.add(mst)
                            new_count += 1
                            
                    logging.info(f"Trang {url.split('/')[-1]} -> Lấy thêm được {new_count} MST. Tổng: {len(mst_set)}")
                    
                elif response.status == 403:
                    logging.warning(f"Lỗi 403 tại {url}. Cần dùng Proxy nếu bị liên tục.")
                elif response.status == 429:
                    logging.warning(f"Lỗi 429 (Quá nhanh) tại {url}. Đang tạm nghỉ...")
                    await asyncio.sleep(5)
                else:
                    logging.error(f"Lỗi {response.status} tại {url}")
                    
        except Exception as e:
            logging.error(f"Lỗi kết nối tại {url}: {e}")

async def main():
    mst_set = set()
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    
    # Giả định quét từ page 1 đến page 3000 tại Hà Nội
    # Bạn có thể thêm vòng lặp cho tp-ho-chi-minh
    urls_to_scrape = [f"https://hosocongty.vn/tp-ha-noi/page-{i}" for i in range(1, 4000)]
    
    # TCPConnector thiết lập để tối ưu hóa việc tái sử dụng kết nối
    connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT, enable_cleanup_closed=True)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = []
        for url in urls_to_scrape:
            if len(mst_set) >= TOTAL_MST_NEEDED:
                break
                
            task = asyncio.create_task(fetch_page(session, semaphore, url, mst_set))
            tasks.append(task)
            
        # Chạy đồng thời các tác vụ
        await asyncio.gather(*tasks)
        
    # Ghi ra file nhiên liệu
    with open('seed_mst.txt', 'w', encoding='utf-8') as f:
        for mst in mst_set:
            f.write(f"{mst}\n")
            
    logging.info(f"🏁 ĐÃ HOÀN TẤT BƯỚC 1: Thu thập thành công {len(mst_set)} Mã số thuế!")

if __name__ == "__main__":
    asyncio.run(main())
