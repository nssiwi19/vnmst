import asyncio
import aiohttp
import json
import logging
import random

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')

# Cấu hình
TOTAL_PAGES = 5000  # 5000 trang * 20 cty = 100,000 records
MAX_CONCURRENT = 10 # 10 luồng đồng thời để không làm sập server của họ

async def fetch_api_page(session, semaphore, page, mst_set):
    """Gọi thẳng vào API ẩn để lấy dữ liệu JSON"""
    url = f"https://thongtindoanhnghiep.co/api/company?l=ha-noi&p={page}"
    
    # Header mô phỏng luồng gọi AJAX (Rất quan trọng để đánh lừa API)
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://thongtindoanhnghiep.co/ha-noi',
        'X-Requested-With': 'XMLHttpRequest' # Khẳng định đây là request từ code JS nội bộ
    }
    
    async with semaphore:
        try:
            # Nghỉ ngẫu nhiên một chút
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Tùy thuộc cấu trúc JSON, thường list doanh nghiệp nằm trong key 'LtsItem' hoặc tương tự
                    # Lưu ý: In thử page 1 ra xem key chính xác là gì nếu code này không nhặt được
                    items = data.get('LtsItem', [])
                    
                    new_count = 0
                    for item in items:
                        # Lấy MST từ data trả về (thường là key 'SolrID' hoặc 'MaSoThue')
                        mst = str(item.get('SolrID', '')).strip()
                        if mst and len(mst) >= 10:
                            mst_set.add(mst)
                            new_count += 1
                            
                    logging.info(f"✅ Trang {page} -> Lấy được {new_count} MST. Tổng kho: {len(mst_set)}")
                    
                elif response.status == 429:
                    logging.warning(f"⚠️ Rate limit tại trang {page}. Đang làm mát...")
                    await asyncio.sleep(5)
                else:
                    logging.error(f"❌ Lỗi {response.status} tại trang {page}")
                    
        except Exception as e:
            logging.error(f"❌ Lỗi mạng tại trang {page}: {e}")

async def main():
    mst_set = set()
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        for page in range(1, TOTAL_PAGES + 1):
            task = asyncio.create_task(fetch_api_page(session, semaphore, page, mst_set))
            tasks.append(task)
            
        await asyncio.gather(*tasks)
        
    # Ghi ra file làm input cho hệ thống
    with open('seed_mst.txt', 'w', encoding='utf-8') as f:
        for mst in mst_set:
            f.write(f"{mst}\n")
            
    logging.info("-" * 40)
    logging.info(f"🎉 HOÀN TẤT CHIẾN DỊCH: Đã thu hoạch {len(mst_set)} Mã số thuế sạch từ API JSON.")
    logging.info("Bây giờ hãy đưa file seed_mst.txt này vào Pipeline Esgoo.")
    logging.info("-" * 40)

if __name__ == "__main__":
    asyncio.run(main())
