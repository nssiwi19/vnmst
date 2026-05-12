#!/usr/bin/env python3
"""
Thu thap du lieu doanh nghiep Viet Nam theo MST voi pipeline async.

Cap nhat:
- Fallback da nguon theo thu tu uu tien (adapter pattern)
- Manual review queue cho MST fail/toi thieu du lieu
- Quality report theo tung nguon

Luu y tuan thu:
- Chi crawl khi ban co quyen truy cap hop phap.
- Ton trong terms, robots va rate limit.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import re
import ssl
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any

import aiohttp

VIETQR_BASE_URL = "https://api.vietqr.io"
MASOTHUE_SEARCH_URL = "https://masothue.com/Search/?q={mst}"
DKKD_LOOKUP_URL = "https://dangkykinhdoanh.gov.vn/bocaodientu/App_Services/NghiepVu/TienIch/TraCuu.asmx/LayDanhSachDoanhNghiepTheoTenNgan"
ESGOO_URL_TEMPLATE = "https://esgoo.net/api-mst/{mst}.htm"
XINVOICE_URL_TEMPLATE = "https://api.xinvoice.vn/gdt-api/tax-payer-records/{mst}"
TTDN_URL_TEMPLATE = "https://thongtindoanhnghiep.co/api/company/{mst}"
OFFICIAL3_SOURCE_ORDER = [
    "dkkd",
    "gdt",
    "vietqr",
    "esgoo",
    "thongtindoanhnghiep",
    "xinvoice",
    "masothue",
]
DEFAULT_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/123.0 Safari/537.36",
]
HN_HCM_KEYWORDS = (
    "HA NOI",
    "HANOI",
    "HÀ NỘI",
    "HO CHI MINH",
    "HỒ CHÍ MINH",
    "TP HỒ CHÍ MINH",
    "TP. HỒ CHÍ MINH",
    "THỦ ĐỨC",
)
SUPPORTED_SOURCES = {
    "vietqr",
    "esgoo",
    "xinvoice",
    "thongtindoanhnghiep",
    "gdt",
    "third_party",
    "masothue",
    "dkkd",
}


@dataclass
class JobConfig:
    workers: int
    max_retries: int
    backoff: float
    pause_ms: int
    only_hn_hcm: bool
    source_order: list[str]
    vietqr_base_url: str
    gdt_url_template: str
    third_party_url_template: str
    masothue_url_template: str
    dkkd_lookup_url: str
    esgoo_url_template: str
    xinvoice_url_template: str
    ttdn_url_template: str
    xinvoice_client_id: str
    xinvoice_api_key: str
    connector_ssl: ssl.SSLContext | bool
    source_retries: int
    source_retry_backoff_ms: int
    rescue_rounds: int


def normalize_mst(text: str) -> str | None:
    digits = re.sub(r"\D", "", text.strip())
    if len(digits) == 10:
        return digits
    if len(digits) == 13:
        return f"{digits[:10]}-{digits[10:]}"
    return digits or None


def normalize_phone(text: str | None) -> str | None:
    if not text:
        return None
    digits = re.sub(r"\D", "", text)
    if not digits:
        return None
    if digits.startswith("84"):
        return f"+{digits}"
    if digits.startswith("0"):
        return f"+84{digits[1:]}"
    return f"+{digits}"


def normalize_email(text: str | None) -> str | None:
    if not text:
        return None
    m = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    return m.group(0).lower() if m else None


def normalize_address(text: str | None) -> str | None:
    if not text:
        return None
    cleaned = re.sub(r"\s+", " ", text).strip(" ,")
    return cleaned or None


def looks_like_hn_hcm(address: str | None) -> bool:
    if not address:
        return False
    upper = address.upper()
    return any(keyword in upper for keyword in HN_HCM_KEYWORDS)


def parse_name_for_sector(company_name: str | None) -> str | None:
    blob = (company_name or "").lower()
    if re.search(r"ngân hàng|bank|tín dụng", blob):
        return "Tài chính - ngân hàng"
    if re.search(r"viễn thông|telecom|công nghệ|it|cntt", blob):
        return "Viễn thông - công nghệ"
    if re.search(r"sữa|dairy|food|thực phẩm", blob):
        return "Thực phẩm - FMCG"
    if re.search(r"bất động sản|real estate|hạ tầng", blob):
        return "Bất động sản - hạ tầng"
    return None


def pick_first(data: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        value = data.get(key)
        if value not in (None, "", []):
            return value
    return None


def map_record(
    source_name: str,
    api_code: str,
    api_desc: str | None,
    mst: str | None,
    company_name: str | None,
    address: str | None,
    phone: str | None = None,
    email: str | None = None,
    international_name: str | None = None,
    short_name: str | None = None,
    established_year: int | None = None,
    industry: str | None = None,
) -> dict[str, Any]:
    normalized_name = company_name.strip() if isinstance(company_name, str) else company_name
    normalized_address = normalize_address(address)
    return {
        "mst": normalize_mst(str(mst)) if mst else None,
        "ten_cong_ty": normalized_name,
        "nam_thanh_lap": established_year,
        "sdt": normalize_phone(phone),
        "email": normalize_email(email),
        "dia_chi": normalized_address,
        "nganh_nghe_kinh_doanh": industry or parse_name_for_sector(normalized_name),
        "ten_quoc_te": international_name,
        "ten_ngan": short_name,
        "nguon_chinh": source_name,
        "api_code": str(api_code),
        "api_desc": api_desc,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


async def fetch_json(
    session: aiohttp.ClientSession,
    url: str,
    user_agent: str,
    proxy: str | None,
    method: str = "GET",
    json_body: dict[str, Any] | None = None,
    content_type: str | None = None,
    extra_headers: dict[str, str] | None = None,
    request_ssl: ssl.SSLContext | bool = True,
    timeout_s: int = 25,
) -> tuple[int, dict[str, Any]]:
    headers = {"Accept": "application/json", "User-Agent": user_agent}
    if content_type:
        headers["Content-Type"] = content_type
    if extra_headers:
        headers.update(extra_headers)
    timeout = aiohttp.ClientTimeout(total=timeout_s)
    try:
        if method.upper() == "POST":
            payload = json.dumps(json_body or {}, ensure_ascii=False)
            response_ctx = session.post(
                url,
                data=payload.encode("utf-8"),
                headers=headers,
                proxy=proxy,
                timeout=timeout,
                ssl=request_ssl,
            )
        else:
            response_ctx = session.get(url, headers=headers, proxy=proxy, timeout=timeout, ssl=request_ssl)

        async with response_ctx as response:
            text = await response.text()
            try:
                body = json.loads(text)
                if not isinstance(body, dict):
                    body = {"code": "invalid_payload", "desc": "Unexpected payload", "data": None}
            except json.JSONDecodeError:
                body = {"code": "parse_error", "desc": text[:500], "data": None}
            if "code" not in body:
                body["code"] = str(response.status)
            if "desc" not in body and not response.ok:
                body["desc"] = response.reason
            return response.status, body
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
        return 0, {"code": "connection_error", "desc": str(exc), "data": None}


async def fetch_from_vietqr(
    session: aiohttp.ClientSession,
    mst: str,
    cfg: JobConfig,
    user_agent: str,
    proxy: str | None,
) -> tuple[dict[str, Any] | None, str]:
    url = f"{cfg.vietqr_base_url.rstrip('/')}/v2/business/{mst}"
    _, body = await fetch_json(session, url, user_agent, proxy, request_ssl=cfg.connector_ssl)
    data = body.get("data") if isinstance(body.get("data"), dict) else None
    if str(body.get("code")) == "00" and data:
        row = map_record(
            source_name="vietqr",
            api_code=str(body.get("code")),
            api_desc=body.get("desc"),
            mst=data.get("id"),
            company_name=data.get("name"),
            address=data.get("address"),
            international_name=data.get("internationalName"),
            short_name=data.get("shortName"),
        )
        return row, "success"
    return None, str(body.get("desc") or body.get("code") or "vietqr_no_data")


async def fetch_from_template_source(
    source_name: str,
    url_template: str,
    session: aiohttp.ClientSession,
    mst: str,
    user_agent: str,
    proxy: str | None,
    request_ssl: ssl.SSLContext | bool,
) -> tuple[dict[str, Any] | None, str]:
    if not url_template:
        return None, "template_not_configured"
    url = url_template.format(mst=mst)
    _, body = await fetch_json(session, url, user_agent, proxy, request_ssl=request_ssl)

    raw_data: dict[str, Any]
    if isinstance(body.get("data"), dict):
        raw_data = body["data"]
    elif isinstance(body, dict):
        raw_data = body
    else:
        return None, "invalid_payload"

    m = pick_first(raw_data, ["mst", "tax_code", "taxCode", "id", "ma_so_thue"])
    n = pick_first(raw_data, ["name", "company_name", "ten_cong_ty", "ten"])
    a = pick_first(raw_data, ["address", "dia_chi", "address_full"])
    p = pick_first(raw_data, ["phone", "sdt", "mobile"])
    e = pick_first(raw_data, ["email", "mail"])
    y = pick_first(raw_data, ["founded_year", "established_year", "nam_thanh_lap"])
    i = pick_first(raw_data, ["industry", "nganh_nghe_kinh_doanh", "business_line"])

    established_year: int | None = None
    if isinstance(y, int):
        established_year = y
    elif isinstance(y, str) and y.isdigit():
        established_year = int(y)

    row = map_record(
        source_name=source_name,
        api_code=str(body.get("code", "00")),
        api_desc=body.get("desc"),
        mst=str(m) if m else None,
        company_name=str(n) if n else None,
        address=str(a) if a else None,
        phone=str(p) if p else None,
        email=str(e) if e else None,
        established_year=established_year,
        industry=str(i) if i else None,
    )
    if row.get("mst") and row.get("ten_cong_ty"):
        return row, "success"
    return None, "template_source_missing_required_fields"


def strip_html_to_text(html: str) -> str:
    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", html)
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_with_patterns(text: str, patterns: list[str]) -> str | None:
    for pattern in patterns:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if m and m.group(1).strip():
            return m.group(1).strip(" :,-")
    return None


async def fetch_from_masothue(
    session: aiohttp.ClientSession,
    mst: str,
    cfg: JobConfig,
    user_agent: str,
    proxy: str | None,
) -> tuple[dict[str, Any] | None, str]:
    url = cfg.masothue_url_template.format(mst=mst)
    headers = {"User-Agent": user_agent, "Accept": "text/html,*/*;q=0.8"}
    timeout = aiohttp.ClientTimeout(total=25)
    try:
        async with session.get(url, headers=headers, proxy=proxy, timeout=timeout, ssl=cfg.connector_ssl) as response:
            html = await response.text(errors="ignore")
            if response.status != 200:
                return None, f"http_{response.status}"
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
        return None, str(exc)

    text = strip_html_to_text(html)

    parsed_mst = normalize_mst(mst) or normalize_mst(text)
    company_name = extract_with_patterns(
        text,
        [
            r"Tên công ty\s*:?\s*(.+?)\s*(?:Tên quốc tế|Tên giao dịch|Mã số thuế|Địa chỉ|$)",
            r"Tên doanh nghiệp\s*:?\s*(.+?)\s*(?:Mã số thuế|Địa chỉ|$)",
        ],
    )
    address = extract_with_patterns(
        text,
        [
            r"Địa chỉ\s*:?\s*(.+?)\s*(?:Điện thoại|Người đại diện|Ngày hoạt động|$)",
            r"Địa chỉ trụ sở\s*:?\s*(.+?)\s*(?:Điện thoại|Người đại diện|$)",
        ],
    )
    phone = extract_with_patterns(text, [r"Điện thoại\s*:?\s*([0-9\.\-\s\(\)\+]{8,20})"])
    email = extract_with_patterns(text, [r"Email\s*:?\s*([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})"])
    industry = extract_with_patterns(
        text,
        [
            r"Ngành nghề kinh doanh\s*:?\s*(.+?)\s*(?:Cập nhật mã số thuế lần cuối|$)",
            r"Ngành nghề chính\s*:?\s*(.+?)\s*(?:Cập nhật|$)",
        ],
    )

    row = map_record(
        source_name="masothue",
        api_code="00" if parsed_mst and company_name else "04",
        api_desc="success" if parsed_mst and company_name else "masothue_missing_fields",
        mst=parsed_mst,
        company_name=company_name,
        address=address,
        phone=phone,
        email=email,
        industry=industry,
    )
    if row.get("mst") and row.get("ten_cong_ty"):
        return row, "success"
    return None, "masothue_missing_required_fields"


async def fetch_from_dkkd(
    session: aiohttp.ClientSession,
    mst: str,
    cfg: JobConfig,
    user_agent: str,
    proxy: str | None,
) -> tuple[dict[str, Any] | None, str]:
    request_kwargs = {
        "session": session,
        "url": cfg.dkkd_lookup_url,
        "user_agent": user_agent,
        "proxy": proxy,
        "method": "POST",
        "json_body": {"searchString": mst},
        "content_type": "application/json; charset=UTF-8",
    }
    status, body = await fetch_json(**request_kwargs, request_ssl=cfg.connector_ssl)
    # Emergency fallback for hosts with broken TLS chain in local environment.
    if status == 0 and "CERTIFICATE_VERIFY_FAILED" in str(body.get("desc", "")):
        status, body = await fetch_json(**request_kwargs, request_ssl=False)
    if status == 0:
        return None, str(body.get("desc") or "connection_error")

    payload: Any = body.get("d", body.get("data", body))
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            payload = {}
    if isinstance(payload, list):
        payload = payload[0] if payload else {}
    if not isinstance(payload, dict):
        payload = {}

    parsed_mst = pick_first(payload, ["MaSoDoanhNghiep", "MaSoThue", "ma_so_thue", "mst"])
    company_name = pick_first(payload, ["TenDoanhNghiep", "ten_doanh_nghiep", "ten_cong_ty", "name"])
    address = pick_first(payload, ["DiaChiTruSoChinh", "dia_chi", "address"])
    industry = pick_first(payload, ["NganhNgheKinhDoanh", "nganh_nghe_kinh_doanh", "industry"])
    phone = pick_first(payload, ["DienThoai", "dien_thoai", "sdt", "phone"])
    email = pick_first(payload, ["Email", "email", "mail"])

    row = map_record(
        source_name="dkkd",
        api_code="00" if parsed_mst and company_name else "04",
        api_desc="success" if parsed_mst and company_name else "dkkd_missing_fields",
        mst=str(parsed_mst) if parsed_mst else mst,
        company_name=str(company_name) if company_name else None,
        address=str(address) if address else None,
        phone=str(phone) if phone else None,
        email=str(email) if email else None,
        industry=str(industry) if industry else None,
    )
    if row.get("mst") and row.get("ten_cong_ty"):
        return row, "success"
    return None, "dkkd_missing_required_fields"


async def fetch_from_esgoo(
    session: aiohttp.ClientSession,
    mst: str,
    cfg: JobConfig,
    user_agent: str,
    proxy: str | None,
) -> tuple[dict[str, Any] | None, str]:
    url = cfg.esgoo_url_template.format(mst=mst)
    _, body = await fetch_json(session, url, user_agent, proxy, request_ssl=cfg.connector_ssl)
    data = body.get("data") if isinstance(body.get("data"), dict) else {}

    parsed_mst = pick_first(data, ["mst", "ma_so_thue", "taxCode", "tax_code"]) or mst
    company_name = pick_first(data, ["ten", "name", "company_name"])
    address = pick_first(data, ["dc", "dia_chi", "address"])
    industry = pick_first(data, ["nganhnghe", "nganh_nghe_kinh_doanh", "industry"])
    representative = pick_first(data, ["daidien", "nguoi_dai_dien"])
    established = pick_first(data, ["capphep", "ngay_cap_phep"])

    if isinstance(industry, list):
        industry = "; ".join(str(x) for x in industry[:5])

    row = map_record(
        source_name="esgoo",
        api_code=str(body.get("code", "00")),
        api_desc=body.get("desc") or body.get("message"),
        mst=str(parsed_mst) if parsed_mst else mst,
        company_name=str(company_name) if company_name else None,
        address=str(address) if address else None,
        industry=str(industry) if industry else None,
    )
    if representative:
        row["nguoi_dai_dien"] = str(representative)
    if established:
        row["ngay_cap_phep"] = str(established)

    if row.get("mst") and row.get("ten_cong_ty"):
        return row, "success"
    return None, "esgoo_missing_required_fields"


async def fetch_from_xinvoice(
    session: aiohttp.ClientSession,
    mst: str,
    cfg: JobConfig,
    user_agent: str,
    proxy: str | None,
) -> tuple[dict[str, Any] | None, str]:
    if not cfg.xinvoice_client_id or not cfg.xinvoice_api_key:
        return None, "xinvoice_missing_credentials"

    url = cfg.xinvoice_url_template.format(mst=mst)
    _, body = await fetch_json(
        session=session,
        url=url,
        user_agent=user_agent,
        proxy=proxy,
        extra_headers={"client-id": cfg.xinvoice_client_id, "api-key": cfg.xinvoice_api_key},
        request_ssl=cfg.connector_ssl,
    )
    data = body.get("data") if isinstance(body.get("data"), dict) else body
    if not isinstance(data, dict):
        data = {}

    parsed_mst = pick_first(data, ["taxID", "taxCode", "mst", "id"]) or mst
    company_name = pick_first(data, ["name", "ten_cong_ty", "company_name"])
    address = pick_first(data, ["address", "dia_chi"])
    status = pick_first(data, ["status", "tinh_trang"])
    org_type = pick_first(data, ["orgType", "loai_to_chuc"])
    tax_department = pick_first(data, ["taxDepartment", "co_quan_thue"])

    row = map_record(
        source_name="xinvoice",
        api_code=str(body.get("code", "00")),
        api_desc=body.get("desc") or body.get("message"),
        mst=str(parsed_mst) if parsed_mst else mst,
        company_name=str(company_name) if company_name else None,
        address=str(address) if address else None,
    )
    if status:
        row["trang_thai_mst"] = str(status)
    if org_type:
        row["loai_to_chuc"] = str(org_type)
    if tax_department:
        row["co_quan_thue"] = str(tax_department)

    if row.get("mst") and row.get("ten_cong_ty"):
        return row, "success"
    return None, "xinvoice_missing_required_fields"


async def fetch_from_ttdn(
    session: aiohttp.ClientSession,
    mst: str,
    cfg: JobConfig,
    user_agent: str,
    proxy: str | None,
) -> tuple[dict[str, Any] | None, str]:
    url = cfg.ttdn_url_template.format(mst=mst)
    _, body = await fetch_json(session, url, user_agent, proxy, request_ssl=cfg.connector_ssl)

    data = body.get("data") if isinstance(body.get("data"), dict) else body
    if not isinstance(data, dict):
        data = {}

    parsed_mst = pick_first(data, ["mst", "MaSoThue", "taxCode", "id"]) or mst
    company_name = pick_first(data, ["Title", "title", "TenCongTy", "name"])
    address = pick_first(data, ["DiaChiCongTy", "address", "dia_chi"])
    industry = pick_first(data, ["NganhNgheTitle", "NganhNghe", "industry"])
    capital = pick_first(data, ["VonDieuLe", "capital"])
    reg_date = pick_first(data, ["NgayCap", "NgayDangKy", "registration_date"])

    row = map_record(
        source_name="thongtindoanhnghiep",
        api_code=str(body.get("code", "00")),
        api_desc=body.get("desc") or body.get("message"),
        mst=str(parsed_mst) if parsed_mst else mst,
        company_name=str(company_name) if company_name else None,
        address=str(address) if address else None,
        industry=str(industry) if industry else None,
    )
    if capital:
        row["von_dieu_le"] = str(capital)
    if reg_date:
        row["ngay_dang_ky"] = str(reg_date)

    if row.get("mst") and row.get("ten_cong_ty"):
        return row, "success"
    return None, "ttdn_missing_required_fields"


async def fetch_with_fallback(
    session: aiohttp.ClientSession,
    mst: str,
    cfg: JobConfig,
    user_agents: list[str],
    proxies: list[str],
) -> tuple[dict[str, Any] | None, str, str, list[str]]:
    last_reason = "unknown"
    tried_sources: list[str] = []
    for source_name in cfg.source_order:
        for attempt_idx in range(cfg.source_retries + 1):
            tried_sources.append(source_name)
            ua = random.choice(user_agents)
            proxy = random.choice(proxies) if proxies else None
            if source_name == "vietqr":
                row, reason = await fetch_from_vietqr(session, mst, cfg, ua, proxy)
            elif source_name == "esgoo":
                row, reason = await fetch_from_esgoo(session, mst, cfg, ua, proxy)
            elif source_name == "thongtindoanhnghiep":
                row, reason = await fetch_from_ttdn(session, mst, cfg, ua, proxy)
            elif source_name == "xinvoice":
                row, reason = await fetch_from_xinvoice(session, mst, cfg, ua, proxy)
            elif source_name == "dkkd":
                row, reason = await fetch_from_dkkd(session, mst, cfg, ua, proxy)
            elif source_name == "masothue":
                row, reason = await fetch_from_masothue(session, mst, cfg, ua, proxy)
            elif source_name == "gdt":
                row, reason = await fetch_from_template_source(
                    "gdt",
                    cfg.gdt_url_template,
                    session,
                    mst,
                    ua,
                    proxy,
                    cfg.connector_ssl,
                )
            elif source_name == "third_party":
                row, reason = await fetch_from_template_source(
                    "third_party",
                    cfg.third_party_url_template,
                    session,
                    mst,
                    ua,
                    proxy,
                    cfg.connector_ssl,
                )
            else:
                row, reason = None, f"unsupported_source:{source_name}"

            if row:
                return row, source_name, "success", tried_sources
            last_reason = reason

            fatal_reasons = {
                "template_not_configured",
                "xinvoice_missing_credentials",
            }
            if (
                attempt_idx < cfg.source_retries
                and reason not in fatal_reasons
                and not str(reason).startswith("unsupported_source:")
            ):
                await asyncio.sleep(cfg.source_retry_backoff_ms / 1000.0)
    return None, "none", last_reason, tried_sources


def load_non_empty_lines(path: Path | None) -> list[str]:
    if not path:
        return []
    if not path.exists():
        raise FileNotFoundError(f"Khong tim thay file: {path}")
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


async def worker(
    queue: asyncio.Queue[str | object],
    stop_signal: object,
    cfg: JobConfig,
    session: aiohttp.ClientSession,
    user_agents: list[str],
    proxies: list[str],
    output: list[dict[str, Any]],
    manual_review: list[dict[str, Any]],
    stats: dict[str, int],
    quality_by_source: dict[str, dict[str, int]],
    lock: asyncio.Lock,
) -> None:
    while True:
        item = await queue.get()
        try:
            if item == stop_signal:
                return

            mst = str(item)
            chosen_source = "none"
            row: dict[str, Any] | None = None
            reason = "no_data"
            tried_sources: list[str] = []

            attempt = 0
            while attempt <= cfg.max_retries:
                row, chosen_source, reason, tried_sources = await fetch_with_fallback(
                    session=session,
                    mst=mst,
                    cfg=cfg,
                    user_agents=user_agents,
                    proxies=proxies,
                )
                if reason in {"429", "Too Many Requests"}:
                    await asyncio.sleep(cfg.backoff * (2**attempt) + random.uniform(0.0, 0.8))
                    attempt += 1
                    continue
                break

            rescue_used = 0
            while not row and rescue_used < cfg.rescue_rounds:
                rescue_used += 1
                await asyncio.sleep(max(0.15, cfg.backoff))
                row, chosen_source, reason, rescue_tried = await fetch_with_fallback(
                    session=session,
                    mst=mst,
                    cfg=cfg,
                    user_agents=user_agents,
                    proxies=proxies,
                )
                tried_sources.extend(rescue_tried)

            for source_name in tried_sources:
                quality_by_source[source_name]["attempt"] += 1

            if row and chosen_source in quality_by_source:
                quality_by_source[chosen_source]["success"] += 1
                for source_name in tried_sources:
                    if source_name != chosen_source:
                        quality_by_source[source_name]["fail"] += 1
            else:
                for source_name in tried_sources:
                    quality_by_source[source_name]["fail"] += 1

            if not row:
                async with lock:
                    stats["manual_review"] = stats.get("manual_review", 0) + 1
                    manual_review.append(
                        {
                            "mst": mst,
                            "reason": reason,
                            "source_order": cfg.source_order,
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                        }
                    )
                await asyncio.sleep(cfg.pause_ms / 1000.0)
                continue

            if cfg.only_hn_hcm and not looks_like_hn_hcm(row.get("dia_chi")):
                async with lock:
                    stats["filtered_not_hn_hcm"] = stats.get("filtered_not_hn_hcm", 0) + 1
                await asyncio.sleep(cfg.pause_ms / 1000.0)
                continue

            async with lock:
                output.append(row)
                stats["ok"] = stats.get("ok", 0) + 1
            await asyncio.sleep(cfg.pause_ms / 1000.0)
        finally:
            queue.task_done()


async def crawl_mst(
    msts: list[str],
    cfg: JobConfig,
    user_agents: list[str],
    proxies: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int], dict[str, dict[str, int]]]:
    queue: asyncio.Queue[str | object] = asyncio.Queue()
    stop_signal = object()
    for mst in msts:
        await queue.put(mst)
    for _ in range(cfg.workers):
        await queue.put(stop_signal)

    output: list[dict[str, Any]] = []
    manual_review: list[dict[str, Any]] = []
    stats: dict[str, int] = {}
    quality_by_source = {src: {"attempt": 0, "success": 0, "fail": 0} for src in cfg.source_order}
    lock = asyncio.Lock()
    connector = aiohttp.TCPConnector(limit=max(10, cfg.workers * 2), ssl=cfg.connector_ssl)

    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [
            asyncio.create_task(
                worker(
                    queue=queue,
                    stop_signal=stop_signal,
                    cfg=cfg,
                    session=session,
                    user_agents=user_agents,
                    proxies=proxies,
                    output=output,
                    manual_review=manual_review,
                    stats=stats,
                    quality_by_source=quality_by_source,
                    lock=lock,
                )
            )
            for _ in range(cfg.workers)
        ]
        await asyncio.gather(*tasks)
    return output, manual_review, stats, quality_by_source


def deduplicate(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    best: dict[str, dict[str, Any]] = {}
    for row in records:
        mst = row.get("mst")
        if not mst:
            continue
        current = best.get(mst)
        if current is None:
            best[mst] = row
            continue
        current_score = int(current.get("api_code") == "00") * 10 + len(current.get("dia_chi") or "")
        row_score = int(row.get("api_code") == "00") * 10 + len(row.get("dia_chi") or "")
        if row_score > current_score:
            best[mst] = row
    deduped = list(best.values())
    return deduped, max(0, len(records) - len(deduped))


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def upsert_supabase(rows: list[dict[str, Any]], batch_size: int) -> int:
    dsn = os.environ.get("SUPABASE_DB_URL")
    if not dsn:
        raise RuntimeError("Thieu SUPABASE_DB_URL")
    try:
        import psycopg2
        from psycopg2.extras import execute_values
    except ImportError as exc:
        raise RuntimeError("Chua cai psycopg2-binary, chay pip install -r requirements.txt") from exc

    sql = """
    INSERT INTO vn_enterprises (
      mst, ten_cong_ty, nam_thanh_lap, sdt, email, dia_chi, nganh_nghe_kinh_doanh,
      ten_quoc_te, ten_ngan, nguon_chinh, api_code, api_desc, updated_at
    )
    VALUES %s
    ON CONFLICT (mst) DO UPDATE SET
      ten_cong_ty = EXCLUDED.ten_cong_ty,
      nam_thanh_lap = EXCLUDED.nam_thanh_lap,
      sdt = EXCLUDED.sdt,
      email = EXCLUDED.email,
      dia_chi = EXCLUDED.dia_chi,
      nganh_nghe_kinh_doanh = EXCLUDED.nganh_nghe_kinh_doanh,
      ten_quoc_te = EXCLUDED.ten_quoc_te,
      ten_ngan = EXCLUDED.ten_ngan,
      nguon_chinh = EXCLUDED.nguon_chinh,
      api_code = EXCLUDED.api_code,
      api_desc = EXCLUDED.api_desc,
      updated_at = EXCLUDED.updated_at;
    """
    cols = [
        "mst",
        "ten_cong_ty",
        "nam_thanh_lap",
        "sdt",
        "email",
        "dia_chi",
        "nganh_nghe_kinh_doanh",
        "ten_quoc_te",
        "ten_ngan",
        "nguon_chinh",
        "api_code",
        "api_desc",
        "updated_at",
    ]
    total = 0
    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:
            for i in range(0, len(rows), batch_size):
                chunk = rows[i : i + batch_size]
                values = [tuple(row.get(c) for c in cols) for row in chunk]
                execute_values(cur, sql, values, page_size=batch_size)
                total += len(chunk)
        conn.commit()
    return total


def upsert_bigquery(rows: list[dict[str, Any]], table: str) -> int:
    if not table:
        raise RuntimeError("Thieu --bigquery-table (vi du: my-prj.dataset.vn_enterprises)")
    try:
        from google.cloud import bigquery
    except ImportError as exc:
        raise RuntimeError("Chua cai google-cloud-bigquery, chay pip install -r requirements.txt") from exc

    client = bigquery.Client()
    job = client.load_table_from_json(rows, table)
    job.result()
    if job.errors:
        raise RuntimeError(f"BigQuery load error: {job.errors}")
    return len(rows)


def parse_source_order(raw: str) -> list[str]:
    items = [x.strip() for x in raw.split(",") if x.strip()]
    if not items:
        return ["vietqr"]
    invalid = [x for x in items if x not in SUPPORTED_SOURCES]
    if invalid:
        raise ValueError(f"Nguon khong hop le: {','.join(invalid)}")
    return items


def is_placeholder_url(url: str | None) -> bool:
    if not url:
        return True
    lower = url.lower().strip()
    return ("your-" in lower and "endpoint" in lower) or ("example.com" in lower)


def build_effective_source_order(args: argparse.Namespace) -> list[str]:
    if args.source_profile == "official3":
        source_order = list(OFFICIAL3_SOURCE_ORDER)
    else:
        source_order = parse_source_order(args.source_order)

    if "gdt" in source_order and is_placeholder_url(args.gdt_url_template):
        source_order = [s for s in source_order if s != "gdt"]
    if "xinvoice" in source_order and (not args.xinvoice_client_id or not args.xinvoice_api_key):
        source_order = [s for s in source_order if s != "xinvoice"]
    # Current public default DKKD endpoint is unstable (404/invalid payload in many environments).
    # Keep it only when user explicitly provides a custom endpoint or forces default endpoint usage.
    if (
        "dkkd" in source_order
        and args.dkkd_lookup_url.strip() == DKKD_LOOKUP_URL
        and not args.force_default_dkkd
    ):
        source_order = [s for s in source_order if s != "dkkd"]
    return source_order


def build_ssl_config(insecure_no_verify_ssl: bool) -> ssl.SSLContext | bool:
    if insecure_no_verify_ssl:
        return False
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Crawl du lieu doanh nghiep VN theo MST (async, compliant).")
    p.add_argument("input", type=Path, help="File danh sach MST, moi dong 1 ma")
    p.add_argument("--output", type=Path, default=Path("out/vn_enterprises.jsonl"))
    p.add_argument("--manual-review-file", type=Path, default=Path("out/manual_review_queue.jsonl"))
    p.add_argument("--quality-report-file", type=Path, default=Path("out/quality_report.json"))
    p.add_argument("--workers", type=int, default=20)
    p.add_argument("--max-retries", type=int, default=4)
    p.add_argument("--backoff", type=float, default=1.5)
    p.add_argument("--pause-ms", type=int, default=70, help="Nghi giua request de giam burst")
    p.add_argument("--source-retries", type=int, default=1, help="So lan retry moi source truoc khi fallback")
    p.add_argument("--source-retry-backoff-ms", type=int, default=120, help="Nghi giua cac lan retry source")
    p.add_argument("--rescue-rounds", type=int, default=1, help="So lan quet lai full source-order truoc manual review")
    p.add_argument(
        "--source-profile",
        choices=["custom", "official3"],
        default="custom",
        help="official3 = dkkd -> gdt -> vietqr -> esgoo -> thongtindoanhnghiep -> xinvoice -> masothue",
    )
    p.add_argument("--source-order", type=str, default="vietqr,esgoo,thongtindoanhnghiep,xinvoice")
    p.add_argument("--vietqr-base-url", type=str, default=os.environ.get("VIETQR_API_BASE", VIETQR_BASE_URL))
    p.add_argument(
        "--gdt-url-template",
        type=str,
        default=os.environ.get("GDT_API_TEMPLATE", ""),
        help="VD: https://example.com/gdt/business/{mst}",
    )
    p.add_argument(
        "--third-party-url-template",
        type=str,
        default=os.environ.get("THIRD_PARTY_API_TEMPLATE", ""),
        help="VD: https://example.com/company/{mst}",
    )
    p.add_argument(
        "--masothue-url-template",
        type=str,
        default=os.environ.get("MASOTHUE_URL_TEMPLATE", MASOTHUE_SEARCH_URL),
        help="VD: https://masothue.com/Search/?q={mst}",
    )
    p.add_argument(
        "--dkkd-lookup-url",
        type=str,
        default=os.environ.get("DKKD_LOOKUP_URL", DKKD_LOOKUP_URL),
        help="Endpoint POST tra cuu dang ky kinh doanh",
    )
    p.add_argument(
        "--force-default-dkkd",
        action="store_true",
        help="Buoc giu dkkd trong source-order ngay ca khi dang dung default endpoint",
    )
    p.add_argument(
        "--esgoo-url-template",
        type=str,
        default=os.environ.get("ESGOO_URL_TEMPLATE", ESGOO_URL_TEMPLATE),
        help="VD: https://esgoo.net/api-mst/{mst}.htm",
    )
    p.add_argument(
        "--xinvoice-url-template",
        type=str,
        default=os.environ.get("XINVOICE_URL_TEMPLATE", "https://api.xinvoice.vn/gdt-api/tax-payer-records/{mst}"),
        help="VD: https://api.xinvoice.vn/gdt-api/tax-payer-records/{mst}",
    )
    p.add_argument(
        "--xinvoice-client-id",
        type=str,
        default=os.environ.get("XINVOICE_CLIENT_ID", ""),
        help="client-id cho XInvoice",
    )
    p.add_argument(
        "--xinvoice-api-key",
        type=str,
        default=os.environ.get("XINVOICE_API_KEY", ""),
        help="api-key cho XInvoice",
    )
    p.add_argument(
        "--ttdn-url-template",
        type=str,
        default=os.environ.get("TTDN_URL_TEMPLATE", TTDN_URL_TEMPLATE),
        help="VD: https://thongtindoanhnghiep.co/api/company/{mst}",
    )
    p.add_argument("--user-agent-file", type=Path, default=None)
    p.add_argument("--proxy-file", type=Path, default=None)
    p.add_argument("--allow-all-regions", action="store_true", help="Khong loc dia chi HN/HCM")
    p.add_argument("--insecure-no-verify-ssl", action="store_true", help="Tat verify SSL (chi dung de debug)")
    p.add_argument("--storage", choices=["none", "supabase", "bigquery"], default="none")
    p.add_argument("--supabase-batch-size", type=int, default=1000)
    p.add_argument("--bigquery-table", type=str, default="")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    if args.workers < 1 or args.workers > 100:
        print("workers nen trong khoang [1, 100]", file=sys.stderr)
        raise SystemExit(2)
    try:
        source_order = build_effective_source_order(args)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2)
    if not source_order:
        print("Khong con nguon hop le sau khi loc theo cau hinh endpoint/credential.", file=sys.stderr)
        raise SystemExit(2)

    raw_msts = [normalize_mst(line) for line in args.input.read_text(encoding="utf-8").splitlines()]
    msts = [m for m in raw_msts if m]
    unique_msts = sorted(set(msts))
    if not unique_msts:
        print("Khong co MST hop le trong file input.", file=sys.stderr)
        raise SystemExit(2)

    user_agents = load_non_empty_lines(args.user_agent_file) or DEFAULT_USER_AGENTS
    proxies = load_non_empty_lines(args.proxy_file)
    cfg = JobConfig(
        workers=args.workers,
        max_retries=args.max_retries,
        backoff=args.backoff,
        pause_ms=args.pause_ms,
        only_hn_hcm=not args.allow_all_regions,
        source_order=source_order,
        vietqr_base_url=args.vietqr_base_url,
        gdt_url_template=args.gdt_url_template,
        third_party_url_template=args.third_party_url_template,
        masothue_url_template=args.masothue_url_template,
        dkkd_lookup_url=args.dkkd_lookup_url,
        esgoo_url_template=args.esgoo_url_template,
        xinvoice_url_template=args.xinvoice_url_template,
        ttdn_url_template=args.ttdn_url_template,
        xinvoice_client_id=args.xinvoice_client_id,
        xinvoice_api_key=args.xinvoice_api_key,
        connector_ssl=build_ssl_config(args.insecure_no_verify_ssl),
        source_retries=max(0, int(args.source_retries)),
        source_retry_backoff_ms=max(0, int(args.source_retry_backoff_ms)),
        rescue_rounds=max(0, int(args.rescue_rounds)),
    )

    records, manual_review, stats, quality_by_source = asyncio.run(
        crawl_mst(
            msts=unique_msts,
            cfg=cfg,
            user_agents=user_agents,
            proxies=proxies,
        )
    )
    deduped, duplicates_removed = deduplicate(records)
    write_jsonl(args.output, deduped)
    write_jsonl(args.manual_review_file, manual_review)

    pushed = 0
    if args.storage == "supabase":
        pushed = upsert_supabase(deduped, batch_size=args.supabase_batch_size)
    elif args.storage == "bigquery":
        pushed = upsert_bigquery(deduped, table=args.bigquery_table)

    quality_report = {
        "input_total": len(msts),
        "input_unique": len(unique_msts),
        "source_order": source_order,
        "stats": stats,
        "quality_by_source": quality_by_source,
        "output_records_raw": len(records),
        "output_records_dedup": len(deduped),
        "duplicates_removed": duplicates_removed,
        "manual_review_count": len(manual_review),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(args.quality_report_file, quality_report)

    summary = {
        "input_total": len(msts),
        "input_unique": len(unique_msts),
        "crawl_stats": stats,
        "quality_by_source": quality_by_source,
        "output_records": len(records),
        "dedup_records": len(deduped),
        "duplicates_removed": duplicates_removed,
        "manual_review_count": len(manual_review),
        "storage": args.storage,
        "storage_written": pushed,
        "output_file": str(args.output),
        "manual_review_file": str(args.manual_review_file),
        "quality_report_file": str(args.quality_report_file),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
