"""
crawler_v3.py — dùng DrissionPage (kết nối Chrome thật, vượt CF tốt hơn Playwright)
Cài: pip install DrissionPage
Chạy: python crawler_v3.py
"""

import re, os, sys, time, random, logging, signal, json
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock, Event
from datetime import datetime
from unidecode import unidecode
import pandas as pd
from curl_cffi import requests
from bs4 import BeautifulSoup
from DrissionPage import ChromiumPage, ChromiumOptions

import io
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("crawler_hsctvn.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

# ─── Config ──────────────────────────────────────────────────────────────────

BASE_URL   = "https://hsctvn.com"
TINH_URL   = {"ha-noi": "/p/ha-noi", "ho-chi-minh": "/p/ho-chi-minh"}
DELAY_MIN  = 1.5
DELAY_MAX  = 3.0
os.makedirs("data", exist_ok=True)
CSV_PATH   = "data/doanh_nghiep.csv"
EXCEL_PATH = "data/doanh_nghiep.xlsx"
CKPT_PATH  = "data/checkpoint.csv"

CHAY_HA_NOI = True
CHAY_HCM    = True
TARGET      = 15000
CO_ENRICH   = True

# Trang bắt đầu (1 = từ đầu, tự động bị ghi đè nếu có checkpoint) muốn theo checkpoint để =1
START_HA_NOI = 936
START_HCM    = 6

START_PAGE   = {"ha-noi": START_HA_NOI, "ho-chi-minh": START_HCM}
LISTING_PATH   = "data/listing.csv"
PAGE_CKPT_PATH = "data/page_checkpoint.json"

# ── Fast mode: dùng HTTP + cookies từ Chrome sau khi pass CF ──────────────────
# Nhanh hơn 5-10x so với điều hướng Chrome từng trang
FAST_MODE       = True   # False = dùng Chrome cho mọi trang (chậm nhưng chắc)
PARALLEL        = 4      # số request đồng thời (chỉ dùng khi FAST_MODE=True)
FAST_DELAY_MIN  = 1.0    # giây nghỉ giữa mỗi request trong fast mode
FAST_DELAY_MAX  = 2.5
# Cứ N request nghỉ dài để tránh rate-limit
BURST_EVERY     = 30     # nghỉ dài sau mỗi N request
BURST_REST_MIN  = 8.0
BURST_REST_MAX  = 15.0
RETRY_INCOMPLETE = True  # True = enrich lại record thiếu cả SDT lẫn Email
FREEZE_AFTER     = 5     # số lần thất bại liên tiếp trước khi đóng băng chờ đổi IP

# ─── Stop flag ───────────────────────────────────────────────────────────────

_STOP        = Event()
_FROZEN      = Event()
_freeze_lock = Lock()


def _handle_sigint(sig, frame):
    if not _STOP.is_set():
        print("\n" + "=" * 60)
        print("  [!] Nhan Ctrl+C — se dung sau record hien tai...")
        print("  [!] Nhan Ctrl+C lan 2 de THOAT NGAY.")
        print("=" * 60 + "\n")
        _STOP.set()
        _FROZEN.clear()  # bỏ freeze nếu đang đóng băng để thoát ngay
    else:
        print("\n[!] Buoc dung ngay!")
        sys.exit(1)

signal.signal(signal.SIGINT, _handle_sigint)


def _freeze_and_wait(reason: str = ""):
    """Đóng băng toàn bộ crawl, chờ người dùng đổi IP rồi nhấn Enter."""
    with _freeze_lock:
        if _FROZEN.is_set():
            return  # thread khác đang xử lý rồi
        _FROZEN.set()
        print("\n" + "=" * 60)
        print(f"  [FROZEN] {reason}")
        print("  Crawl da DONG BANG hoan toan.")
        print("  Hay doi IP, sau do nhan ENTER de tiep tuc...")
        print("  (Nhan Ctrl+C de dung han)")
        print("=" * 60)
        try:
            input("  >> Nhan ENTER sau khi doi IP xong: ")
        except (EOFError, KeyboardInterrupt):
            pass
        if not _STOP.is_set():
            global _http_session
            _http_session = None  # force re-init HTTP session với IP mới
            print("  Dang khoi dong lai session voi IP moi...\n")
        _FROZEN.clear()


def _wait_if_frozen():
    """Nếu đang đóng băng, block cho đến khi được giải phóng."""
    if _FROZEN.is_set():
        log.info("  [Thread] Dang cho frozen duoc giai phong...")
        while _FROZEN.is_set() and not _STOP.is_set():
            time.sleep(1)

# ─── Browser ─────────────────────────────────────────────────────────────────

_page: ChromiumPage = None


def get_browser() -> ChromiumPage:
    global _page
    if _page is not None:
        return _page

    log.info("Khoi dong Chrome ...")
    co = ChromiumOptions()
    co.set_argument("--no-sandbox")
    co.set_argument("--disable-blink-features=AutomationControlled")
    co.set_argument("--lang=vi-VN")
    # headless=False (mặc định) để user giải CF nếu cần
    _page = ChromiumPage(co)
    return _page


def close_browser():
    global _page
    try:
        if _page:
            _page.quit()
    except Exception:
        pass
    _page = None


# ─── HTTP session (fast mode) ────────────────────────────────────────────────

_http_session: requests.Session | None = None
_session_lock  = Lock()
_request_count = 0
_count_lock    = Lock()


def init_http_session() -> bool:
    """Lấy cookies + UA từ Chrome (đã pass CF), tạo requests.Session."""
    global _http_session
    br = get_browser()
    s  = requests.Session(impersonate="chrome120")

    n = 0
    try:
        for c in br.cookies():
            dom = c.get("domain", "")
            if "hsctvn" in dom:
                s.cookies.set(c["name"], c["value"], domain=dom, path=c.get("path", "/"))
                n += 1
    except Exception as e:
        log.warning(f"Khong lay duoc cookies: {e}")
        return False

    if n == 0:
        log.warning("Chua co cookie hsctvn — Chrome chua pass CF?")
        return False

    try:
        ua = br.run_js("return navigator.userAgent;")
    except Exception:
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

    s.headers.update({
        "User-Agent":              ua,
        "Accept":                  "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language":         "vi-VN,vi;q=0.9,en;q=0.8",
        "Referer":                 BASE_URL + "/",
        "Upgrade-Insecure-Requests": "1",
    })
    _http_session = s
    log.info(f"HTTP session OK: {n} cookies")
    return True


def _throttle():
    """Nghỉ ngắn giữa các request, nghỉ dài sau mỗi BURST_EVERY request."""
    global _request_count
    with _count_lock:
        _request_count += 1
        cnt = _request_count
    time.sleep(random.uniform(FAST_DELAY_MIN, FAST_DELAY_MAX))
    if cnt % BURST_EVERY == 0:
        rest = random.uniform(BURST_REST_MIN, BURST_REST_MAX)
        log.info(f"  [Throttle] Nghi {rest:.1f}s sau {cnt} request...")
        time.sleep(rest)


def fetch_html_fast(url: str) -> str | None:
    """Fetch bằng HTTP requests. Nếu CF hết hạn → refresh qua Chrome. Retry vô hạn cho đến khi thành công hoặc _STOP."""
    global _http_session
    if _http_session is None:
        with _session_lock:
            if _http_session is None and not init_http_session():
                return None

    attempt = 0

    while not _STOP.is_set():
        _wait_if_frozen()
        if _STOP.is_set():
            return None

        if attempt >= FREEZE_AFTER:
            _freeze_and_wait(
                f"HTTP that bai {attempt} lan lien tiep — IP co the bi chan hoan toan\n"
                f"  URL: {url[:80]}"
            )
            attempt = 0
            continue

        try:
            r = _http_session.get(url, timeout=15)
            attempt = 0  # reset backoff sau khi kết nối lại thành công
            if r.status_code in (403, 503) or "Just a moment" in r.text:
                print("\n" + "=" * 60)
                print("  CF cookie het han — dang refresh qua Chrome")
                print("  Neu co CAPTCHA hay giai trong Chrome")
                print("  (Nhan Ctrl+C de dung gracefully)")
                print("=" * 60 + "\n")
                with _session_lock:
                    fetch_html(url, wait_selector="ul.hsct", timeout=120)
                    init_http_session()
                attempt = 0
                continue
            if r.status_code == 200:
                _throttle()
                return r.text
            log.warning(f"Fast fetch HTTP {r.status_code} [{url[:60]}] — thu lai lan {attempt + 1}...")
        except Exception as e:
            log.warning(f"Fast fetch [{url[:60]}]: {e} — thu lai lan {attempt + 1}...")

        if not _STOP.is_set():
            wait = min(random.uniform(3, 7) * (attempt + 1), 60)
            log.info(f"  Cho {wait:.1f}s truoc khi thu lai...")
            time.sleep(wait)
        attempt += 1

    return None


# ─── Fetch ───────────────────────────────────────────────────────────────────

def fetch_html(url: str, wait_selector: str = "ul.hsdn",
               timeout: int = 120) -> str | None:
    """
    Điều hướng đến url, chờ wait_selector xuất hiện (tối đa timeout giây).
    Nếu CF hiện: in thông báo, chờ user giải, tự động tiếp tục.
    Nếu thất bại: retry vô hạn cho đến khi thành công hoặc _STOP được set.
    """
    br = get_browser()
    attempt = 0

    while not _STOP.is_set():
        _wait_if_frozen()
        if _STOP.is_set():
            return None

        attempt += 1
        if attempt > FREEZE_AFTER:
            _freeze_and_wait(
                f"Chrome that bai {attempt - 1} lan lien tiep — IP co the bi chan hoan toan\n"
                f"  URL: {url[:80]}"
            )
            attempt = 1
            continue

        try:
            br.get(url)
            attempt = 1  # reset backoff sau khi kết nối lại thành công
        except Exception as e:
            log.error(f"Loi navigate [{url}]: {e}")
            close_browser()
            br = get_browser()
            if _STOP.is_set():
                return None
            wait = min(5 * attempt, 30)
            log.info(f"  Thu lai lan {attempt} sau {wait}s (co the dang doi IP)...")
            time.sleep(wait)
            continue

        t0     = time.time()
        warned = False

        while not _STOP.is_set():
            try:
                el = br.ele(f"css:{wait_selector}", timeout=0)
            except Exception as e:
                log.error(f"Loi element: {e}")
                close_browser()
                br = get_browser()
                break

            if el:
                try:
                    html = br.html
                except Exception as e:
                    log.error(f"Loi lay HTML: {e}")
                    close_browser()
                    br = get_browser()
                    break
                time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
                return html

            elapsed = time.time() - t0
            if elapsed > timeout:
                # Phân biệt: CF/block → retry | trang load OK nhưng không có selector → trả về để parse
                title = ""
                try:
                    title = br.title
                except Exception:
                    pass
                is_cf = any(s in title for s in ("Just a moment", "Verify", "Checking", "Attention Required"))
                if is_cf:
                    log.warning(f"CF block sau {timeout}s (lan {attempt}): [{url}] — se thu lai...")
                    break  # break vòng trong → retry vòng ngoài
                else:
                    # Trang load bình thường nhưng không có selector (hết trang, trang rỗng...)
                    log.info(f"Timeout {timeout}s: [{url}] — khong co {wait_selector!r}, tra ve html de xu ly")
                    try:
                        html = br.html
                    except Exception as e:
                        log.error(f"Loi lay HTML sau timeout: {e}")
                        close_browser()
                        br = get_browser()
                        break
                    time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
                    return html

            if not warned and elapsed > 8:
                title = ""
                try:
                    title = br.title
                except Exception:
                    pass
                is_cf = any(s in title for s in ("Just a moment", "Verify", "Checking", "Attention Required"))
                print("\n" + "=" * 60)
                print(f"  Chua co du lieu sau {elapsed:.0f}s  |  title: {title!r}")
                if is_cf:
                    print("  CLOUDFLARE CHALLENGE — hay giai xac thuc trong Chrome")
                else:
                    print("  Trang chua tai xong hoac bi chan — kiem tra cua so Chrome")
                print("  Script se TU DONG TIEP TUC sau khi du lieu xuat hien")
                print("  (Nhan Ctrl+C de dung gracefully, Ctrl+C x2 de thoat ngay)")
                print("=" * 60 + "\n")
                warned = True

            time.sleep(1.5)

        if not _STOP.is_set():
            wait = min(random.uniform(5, 10) * attempt, 60)
            log.info(f"  Thu lai lan {attempt + 1} sau {wait:.1f}s... [{url[:60]}]")
            time.sleep(wait)

    return None


# ─── Parse listing ───────────────────────────────────────────────────────────

def normalize_phone(phone: str) -> str:
    if not phone:
        return ""
    d = re.sub(r"\D", "", phone)
    if d.startswith("84") and len(d) == 11:
        d = "0" + d[2:]
    return d if len(d) in (9, 10) and d.startswith("0") else ""


def normalize_address(raw: str) -> str:
    return " ".join(raw.split()).replace(" ,", ",") if raw else ""


def decode_cf_email(encoded: str) -> str:
    try:
        enc = bytes.fromhex(encoded)
        key = enc[0]
        return "".join(chr(b ^ key) for b in enc[1:]).lower().strip()
    except Exception:
        return ""


def parse_listing(html: str, tinh_label: str) -> list:
    soup    = BeautifulSoup(html, "html.parser")
    records = []
    seen    = set()

    listing = soup.find("ul", class_="hsdn")
    if not listing:
        log.warning("Khong tim thay ul.hsdn")
        return []

    for li in listing.find_all("li", recursive=False):
        h3 = li.find("h3")
        if not h3:
            continue
        a = h3.find("a", href=True)
        if not a:
            continue

        href  = a.get("href", "").strip("/")
        title = a.get("title", "")
        ten   = a.get_text(strip=True)

        mst = title.split(" - ")[0].strip() if " - " in title else ""
        if not mst or len(mst) < 10 or mst in seen:
            continue
        seen.add(mst)

        dia_chi = ""
        div_tag = li.find("div")
        if div_tag:
            raw = div_tag.get_text(separator=" ", strip=True)
            raw = re.sub(r"(?i)M[aã]\s*s[oố]\s*thu[eế]\s*:.*$", "", raw, flags=re.DOTALL)
            raw = re.sub(r"(?i)^[^\w]*[Đd][^:]*:\s*", "", raw)
            dia_chi = normalize_address(raw)

        records.append({
            "ma_so_thue"   : mst,
            "ten_cong_ty"  : ten,
            "dia_chi"      : dia_chi,
            "tinh_thanh"   : tinh_label,
            "detail_href"  : href,
            "nam_thanh_lap": "",
            "so_dien_thoai": "",
            "email"        : "",
            "nganh_nghe"   : "",
            "crawled_at"   : datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })

    return records


# ─── Parse detail ─────────────────────────────────────────────────────────────

def parse_detail(html: str) -> dict:
    soup   = BeautifulSoup(html, "html.parser")
    result = {"so_dien_thoai": "", "email": "", "nam_thanh_lap": "", "nganh_nghe": ""}

    scope = soup.find("div", class_=lambda c: c and "detail" in c) or soup

    # FIX: mở rộng icon class cho ngành nghề — hsctvn dùng nhiều biến thể
    _NGANH_ICONS = {"fa-tags", "fa-briefcase", "fa-industry", "fa-list-alt",
                    "fa-list", "fa-th-list", "fa-clipboard", "fa-building"}
    # FIX: thêm keyword nhận diện ngành nghề qua text label
    _NGANH_KEYWORDS = {"nganh nghe", "linh vuc", "linh vuc kinh doanh",
                       "nganh kinh doanh", "hoat dong chinh"}

    for ul in scope.find_all("ul", class_="hsct"):
        for li in ul.find_all("li"):
            # FIX: lấy li_str TRƯỚC khi decompose để giữ class icon nguyên vẹn
            li_str = str(li)

            for icon in li.find_all("i"):
                icon.decompose()

            text      = li.get_text(separator=" ", strip=True)
            text_norm = unidecode(text).lower()

            if "fa-phone" in li_str or "dien thoai" in text_norm:
                nums = re.findall(r"0\d{8,9}", text)
                if nums and not result["so_dien_thoai"]:
                    result["so_dien_thoai"] = normalize_phone(nums[0])

            elif "fa-envelope" in li_str or "email" in text_norm:
                cf_tag = li.find(class_="__cf_email__")
                if cf_tag and cf_tag.get("data-cfemail"):
                    result["email"] = decode_cf_email(cf_tag["data-cfemail"])
                else:
                    emails = re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", text)
                    if emails and not result["email"]:
                        result["email"] = emails[0].lower()

            elif "fa-calendar" in li_str or "ngay cap" in text_norm or "ngay thanh lap" in text_norm:
                years = re.findall(r"\b(?:19|20)\d{2}\b", text)
                if years and not result["nam_thanh_lap"]:
                    result["nam_thanh_lap"] = years[0]

            elif (
                any(icon_cls in li_str for icon_cls in _NGANH_ICONS)
                or any(kw in text_norm for kw in _NGANH_KEYWORDS)
            ):
                if not result["nganh_nghe"] and text.strip():
                    # FIX: không bắt buộc có ":" — nếu có thì lấy phần sau,
                    # nếu không có thì lấy toàn bộ text (icon đã bị xóa)
                    if ":" in text:
                        value = text.split(":", 1)[1].strip()
                    else:
                        value = text.strip()
                    if value:
                        result["nganh_nghe"] = value
                        log.debug(f"  [parse_detail] nganh_nghe = {value[:80]!r}")

    # FIX: fallback — tìm ngành nghề ở các cấu trúc HTML khác (div, span, p)
    # nếu ul.hsct không có hoặc không match được
    if not result["nganh_nghe"]:
        _fallback_selectors = [
            ("div", "nganh"),   # <div class="nganh-nghe">...</div>
            ("div", "business"),
            ("td", None),       # một số site dùng table
            ("span", None),
        ]
        _label_patterns = re.compile(
            r"ng[aà]nh\s*ngh[eề]|l[iĩ]nh\s*v[uự]c|kinh\s*doanh\s*ch[ií]nh",
            re.IGNORECASE
        )
        for tag_name, cls_hint in _fallback_selectors:
            for tag in scope.find_all(tag_name):
                cls = " ".join(tag.get("class", []))
                if cls_hint and cls_hint not in cls.lower():
                    continue
                txt = tag.get_text(separator=" ", strip=True)
                if _label_patterns.search(txt) and len(txt) < 300:
                    value = txt.split(":", 1)[1].strip() if ":" in txt else txt.strip()
                    if value and len(value) > 3:
                        result["nganh_nghe"] = value
                        log.debug(f"  [parse_detail][fallback] nganh_nghe = {value[:80]!r}")
                        break
            if result["nganh_nghe"]:
                break

    return result


# ─── Crawl ───────────────────────────────────────────────────────────────────

def _load_page_ckpt() -> dict:
    if os.path.exists(PAGE_CKPT_PATH):
        try:
            with open(PAGE_CKPT_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def _save_page_ckpt(tinh_key: str, page_num: int):
    data = _load_page_ckpt()
    data[tinh_key] = page_num
    with open(PAGE_CKPT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

def _append_listing(new_records: list):
    """Ghi thêm records mới vào LISTING_PATH, dedup theo MST."""
    df_new = pd.DataFrame(new_records)
    if os.path.exists(LISTING_PATH):
        df_old = pd.read_csv(LISTING_PATH, dtype=str).fillna("")
        df = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df = df_new
    df.drop_duplicates(subset=["ma_so_thue"], keep="last", inplace=True)
    df.to_csv(LISTING_PATH, index=False, encoding="utf-8-sig")


def get_listing_url(tinh_key: str, page_num: int) -> str:
    base = TINH_URL[tinh_key]
    return f"{BASE_URL}{base}" if page_num == 1 else f"{BASE_URL}{base}/page-{page_num}"


def crawl_listing(tinh_key: str, tinh_label: str, max_records: int = 500) -> list:
    all_records = []
    seen_mst    = set()

    # Resume: load MST + trang đã crawl từ lần trước
    if os.path.exists(LISTING_PATH):
        try:
            df_ex = pd.read_csv(LISTING_PATH, dtype=str).fillna("")
            prev  = df_ex[df_ex["tinh_thanh"] == tinh_label]
            seen_mst    = set(prev["ma_so_thue"].tolist())
            all_records = prev.to_dict("records")
            if seen_mst:
                log.info(f"  Resume listing {tinh_label}: da co {len(seen_mst)} MST tu file cu")
        except Exception as e:
            log.warning(f"  Khong load duoc listing.csv: {e}")

    manual_start = START_PAGE.get(tinh_key, 1)
    if manual_start > 1:
        # User đặt trang cụ thể → ưu tiên tuyệt đối, bỏ qua checkpoint
        page_num = manual_start
        log.info(f"  Bat dau tu trang {page_num} (do nguoi dung chi dinh)")
    else:
        # Dùng checkpoint nếu có, không thì bắt từ 1
        page_ckpt = _load_page_ckpt()
        if tinh_key in page_ckpt and len(seen_mst) > 0:
            page_num = page_ckpt[tinh_key]
            log.info(f"  Resume tu trang {page_num} (checkpoint tu lan chay truoc)")
        else:
            page_num = 1

    log.info(f"=== Crawl listing: {tinh_label} | tu trang {page_num} | muc tieu: {max_records} ===")

    while len(all_records) < max_records and not _STOP.is_set():
        url  = get_listing_url(tinh_key, page_num)
        html = fetch_html(url, wait_selector="ul.hsdn")
        if not html:
            # fetch_html chi tra None khi _STOP duoc set
            log.info(f"Dung crawl listing theo yeu cau nguoi dung.")
            break

        records   = parse_listing(html, tinh_label)

        # Trang load được nhưng parse ra rỗng — kiểm tra có phải load dở không
        if not records and "hsdn" not in html:
            # HTML không chứa class listing → trang load dở hoặc lỗi → retry
            log.warning(f"  [{tinh_label}] trang {page_num}: HTML khong co listing, co the load do — thu lai...")
            time.sleep(random.uniform(5, 10))
            continue  # không tăng page_num, không tính empty_pages

        new_count = 0
        new_batch = []
        for r in records:
            if r["ma_so_thue"] not in seen_mst and len(all_records) < max_records:
                seen_mst.add(r["ma_so_thue"])
                all_records.append(r)
                new_batch.append(r)
                new_count += 1

        log.info(
            f"  [{tinh_label}] trang {page_num:>4}: +{new_count:>2}"
            f" | tong {len(all_records):>5}/{max_records}"
        )

        if new_count > 0:
            _append_listing(new_batch)

        page_num += 1
        _save_page_ckpt(tinh_key, page_num)  # lưu trang tiếp theo cần crawl

        if page_num % 10 == 0:
            wait = random.uniform(8, 12)
            log.info(f"  Nghi {wait:.1f}s ...")
            time.sleep(wait)

    log.info(f"Xong listing {tinh_label}: {len(all_records)} records")
    return all_records


def enrich_records(records: list, batch_size: int = 50) -> list:
    # Nếu không có records trong memory, load từ file có sẵn
    if not records:
        for src in [LISTING_PATH, CKPT_PATH, CSV_PATH]:
            if os.path.exists(src):
                records = pd.read_csv(src, dtype=str).fillna("").to_dict("records")
                log.info(f"Load {len(records)} records tu {src}")
                break

    ENRICH_FIELDS = ["so_dien_thoai", "email", "nam_thanh_lap", "nganh_nghe"]
    attempted_mst = set()  # đã fetch (dù có hay không có data)
    enriched_mst  = set()  # đã fetch và có ít nhất 1 trường
    if os.path.exists(CKPT_PATH):
        df_cp    = pd.read_csv(CKPT_PATH, dtype=str).fillna("")
        ckpt_map = df_cp.set_index("ma_so_thue").to_dict("index")
        attempted_mst = set(df_cp["ma_so_thue"].tolist())
        has_data = df_cp[ENRICH_FIELDS].apply(
            lambda row: any(str(v).strip() for v in row), axis=1
        )
        enriched_mst = set(df_cp[has_data]["ma_so_thue"].tolist())

        # RETRY_INCOMPLETE: bỏ khỏi attempted những record thiếu cả SDT lẫn Email
        if RETRY_INCOMPLETE:
            incomplete = set(
                df_cp[
                    df_cp["so_dien_thoai"].str.strip().eq("") &
                    df_cp["email"].str.strip().eq("")
                ]["ma_so_thue"].tolist()
            )
            attempted_mst -= incomplete
            log.info(f"RETRY_INCOMPLETE: se thu lai {len(incomplete)} record thieu ca SDT lan Email")

        # Áp dụng data từ checkpoint vào records hiện tại
        for r in records:
            if r["ma_so_thue"] in ckpt_map:
                for k in ENRICH_FIELDS:
                    v = ckpt_map[r["ma_so_thue"]].get(k, "")
                    if v:
                        r[k] = v
        n_skip = len(attempted_mst)
        log.info(f"Checkpoint: {len(enriched_mst)} co du lieu, {n_skip - len(enriched_mst)} da thu/khong co, se bo qua ca hai")

    total   = len(records)
    pending = [r for r in records if r["ma_so_thue"] not in attempted_mst and r.get("detail_href")]
    sdt_ok  = sum(1 for r in records if r.get("so_dien_thoai"))
    log.info(f"=== Enrich {total} records | can fetch: {len(pending)} | mode={'FAST x' + str(PARALLEL) if FAST_MODE else 'SLOW'} ===")

    # Warm-up: đảm bảo Chrome đã pass CF trước khi chạy fast mode
    if FAST_MODE and pending:
        first_url = f"{BASE_URL}/{pending[0]['detail_href']}"
        log.info("Warm-up Chrome de pass CF...")
        html = fetch_html(first_url, wait_selector="ul.hsct", timeout=120)
        if html:
            for k, v in parse_detail(html).items():
                if v:
                    pending[0][k] = v
            if pending[0].get("so_dien_thoai"):
                sdt_ok += 1
        pending = pending[1:]
        init_http_session()

    save_lock = Lock()
    done_count = 0

    def _fetch_one(r: dict) -> dict:
        href = r.get("detail_href", "")
        url  = f"{BASE_URL}/{href}"
        html = fetch_html_fast(url) if FAST_MODE else fetch_html(url, wait_selector="ul.hsct", timeout=30)
        if html:
            for k, v in parse_detail(html).items():
                if v:
                    r[k] = v
        return r

    def _after_each(r: dict):
        nonlocal done_count, sdt_ok
        done_count += 1
        if r.get("so_dien_thoai"):
            sdt_ok += 1
        if done_count % 10 == 0 or done_count == len(pending):
            pct = done_count / len(pending) * 100 if pending else 100
            log.info(f"  Enrich {done_count}/{len(pending)} ({pct:.0f}%) | SDT: {sdt_ok}")
        if done_count % batch_size == 0 or done_count == len(pending):
            with save_lock:
                pd.DataFrame(records).to_csv(CKPT_PATH, index=False, encoding="utf-8-sig")

    if FAST_MODE and PARALLEL > 1:
        with ThreadPoolExecutor(max_workers=PARALLEL) as ex:
            futures = {ex.submit(_fetch_one, r): r for r in pending}
            for fut in as_completed(futures):
                if _STOP.is_set():
                    ex.shutdown(wait=False, cancel_futures=True)
                    break
                _after_each(fut.result())
    else:
        for r in pending:
            if _STOP.is_set():
                break
            _after_each(_fetch_one(r))

    if _STOP.is_set():
        log.info("Enrich dung theo yeu cau nguoi dung. Luu checkpoint...")

    return records


COLS = [
    "ma_so_thue", "ten_cong_ty", "nam_thanh_lap",
    "so_dien_thoai", "email", "dia_chi", "nganh_nghe",
    "tinh_thanh", "crawled_at",
]


def save_and_merge(records: list) -> pd.DataFrame:
    df_moi = pd.DataFrame(records)
    for c in COLS:
        if c not in df_moi.columns:
            df_moi[c] = ""

    if os.path.exists(CSV_PATH):
        df_cu = pd.read_csv(CSV_PATH, dtype=str).fillna("")
        df    = pd.concat([df_cu, df_moi[COLS]], ignore_index=True)
        print(f"Merge: {len(df_cu):,} (cu) + {len(df_moi):,} (moi) = {len(df):,}")
    else:
        df = df_moi[COLS].copy()
        print(f"File moi: {len(df):,} records")

    before = len(df)
    df = df.drop_duplicates(subset=["ma_so_thue"], keep="last").reset_index(drop=True)
    print(f"Dedup: {before:,} -> {len(df):,} (bo {before - len(df):,} trung)")

    df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
    with pd.ExcelWriter(EXCEL_PATH, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Doanh Nghiep")
        ws = writer.sheets["Doanh Nghiep"]
        for col, w in zip("ABCDEFGHI", [15, 45, 8, 13, 30, 55, 30, 10, 18]):
            ws.column_dimensions[col].width = w

    print(f"\nDa luu:\n  {CSV_PATH}\n  {EXCEL_PATH}")

    total = len(df)
    print(f"\nChat luong {total:,} records:")
    for col, label in [
        ("ma_so_thue",    "MST       "),
        ("ten_cong_ty",   "Ten CT    "),
        ("dia_chi",       "Dia chi   "),
        ("nam_thanh_lap", "Nam TL    "),
        ("so_dien_thoai", "SDT       "),
        ("email",         "Email     "),
        ("nganh_nghe",    "Nganh nghe"),
    ]:
        n = df[col].str.strip().str.len().gt(0).sum()
        print(f"  {label}: {n:>6,} ({n/total*100:.0f}%)")

    return df



# ─── Debug helper ─────────────────────────────────────────────────────────────

def debug_html(html: str):
    """
    Paste HTML của 1 trang detail vào đây để xem parser đang nhìn thấy gì.
    Dùng khi ngành nghề không parse được:
        from crawler_v2 import debug_html
        debug_html(open("sample_detail.html").read())
    """
    soup  = BeautifulSoup(html, "html.parser")
    scope = soup.find("div", class_=lambda c: c and "detail" in c) or soup

    print(f"=== scope tag: {scope.name} class={scope.get('class')} ===")
    uls = scope.find_all("ul", class_="hsct")
    print(f"=== Số ul.hsct tìm thấy: {len(uls)} ===\n")

    for i, ul in enumerate(uls):
        print(f"--- ul[{i}] ---")
        for j, li in enumerate(ul.find_all("li")):
            li_str = str(li)
            icons  = [tag.get("class") for tag in li.find_all("i")]
            for tag in li.find_all("i"):
                tag.decompose()
            text = li.get_text(separator=" ", strip=True)
            print(f"  li[{j}]  icons={icons}")
            print(f"         text={text[:120]!r}")
            print(f"         has_colon={'yes' if ':' in text else 'NO ← bug nếu là ngành nghề'}")
            print()

    print("=== Kết quả parse_detail ===")
    import json
    print(json.dumps(parse_detail(html), ensure_ascii=False, indent=2))


# ─── Entry point ─────────────────────────────────────────────────────────────

try:
    tat_ca = []

    if CHAY_HA_NOI:
        tat_ca.extend(crawl_listing("ha-noi",      "Ha Noi", max_records=TARGET))
    if CHAY_HCM:
        tat_ca.extend(crawl_listing("ho-chi-minh", "TP.HCM", max_records=TARGET))

    if CO_ENRICH:
        # Enrich dùng file listing (bao gồm cả records từ các lần chạy trước)
        tat_ca = enrich_records(tat_ca, batch_size=50)

    if tat_ca:
        save_and_merge(tat_ca)
    else:
        log.warning("Khong co record nao.")

finally:
    close_browser()
    # Dù script chạy xong hay bị crash — luôn xuất xlsx từ checkpoint
    if os.path.exists(CKPT_PATH):
        try:
            records_saved = pd.read_csv(CKPT_PATH, dtype=str).fillna("").to_dict("records")
            if records_saved:
                log.info(f"[Finally] Xuat xlsx tu checkpoint ({len(records_saved)} records)...")
                save_and_merge(records_saved)
        except Exception as e:
            log.error(f"[Finally] Khong xuat duoc xlsx: {e}")