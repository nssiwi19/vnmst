"""
agent_utils.py — Shared utilities for Multi-Agent CRM system.

Cung cấp:
  - retry_with_backoff: Decorator tự động retry khi gặp lỗi API (rate limit, timeout)
  - validate_crm_output: Kiểm tra output CRM B2B không rỗng và không chứa placeholder
  - validate_markdown_report: Kiểm tra báo cáo Market Research có cấu trúc Markdown hợp lệ
  - setup_agent_logger: Thiết lập logging chuẩn cho từng pipeline
"""

import functools
import logging
import re
import time
from typing import Callable, Optional


# ---------------------------------------------------------------------------
# 1. Logging
# ---------------------------------------------------------------------------

def setup_agent_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Tạo logger chuẩn cho mỗi agent pipeline.
    Ghi ra console với format rõ ràng: [timestamp] [LEVEL] [pipeline] message
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger


# ---------------------------------------------------------------------------
# 2. Retry with Exponential Backoff
# ---------------------------------------------------------------------------

class AgentRetryError(Exception):
    """Raised when all retry attempts are exhausted."""
    pass


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 2.0,
    max_delay: float = 30.0,
    retryable_exceptions: tuple = (Exception,),
    logger: Optional[logging.Logger] = None,
) -> Callable:
    """
    Decorator: tự động retry một hàm khi gặp exception.
    Sử dụng exponential backoff (delay * 2^attempt) để tránh API rate limit.

    Args:
        max_retries: Số lần retry tối đa (mặc định 3).
        base_delay: Thời gian chờ ban đầu giữa các lần retry (giây).
        max_delay: Thời gian chờ tối đa (giây).
        retryable_exceptions: Tuple các exception class nên retry.
        logger: Logger instance (nếu None sẽ tạo mới).
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            _logger = logger or setup_agent_logger(func.__qualname__)
            last_exception = None

            for attempt in range(1, max_retries + 1):
                try:
                    _logger.info(
                        "Attempt %d/%d — calling %s",
                        attempt, max_retries, func.__name__,
                    )
                    result = func(*args, **kwargs)

                    # Nếu kết quả trả về rỗng, coi như thất bại nhẹ
                    if result is None or (isinstance(result, str) and not result.strip()):
                        _logger.warning(
                            "Attempt %d returned empty result — retrying", attempt
                        )
                        last_exception = AgentRetryError("Empty result returned")
                        if attempt < max_retries:
                            delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                            _logger.info("Waiting %.1fs before retry...", delay)
                            time.sleep(delay)
                        continue

                    _logger.info("Attempt %d succeeded", attempt)
                    return result

                except retryable_exceptions as exc:
                    last_exception = exc
                    _logger.warning(
                        "Attempt %d failed: %s: %s",
                        attempt, type(exc).__name__, str(exc),
                    )
                    if attempt < max_retries:
                        delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                        _logger.info("Waiting %.1fs before retry...", delay)
                        time.sleep(delay)

            # Hết retry — raise lỗi cuối cùng
            raise AgentRetryError(
                f"All {max_retries} attempts failed for {func.__name__}. "
                f"Last error: {last_exception}"
            )

        return wrapper
    return decorator


# ---------------------------------------------------------------------------
# 3. Output Validation — CRM B2B
# ---------------------------------------------------------------------------

# Các placeholder phổ biến mà LLM hay tạo ra thay vì dữ liệu thực
_PLACEHOLDER_PATTERNS = [
    r"\[Tên của bạn\]",
    r"\[Chức danh\]",
    r"\[Số điện thoại\]",
    r"\[Email\]",
    r"\[Tên công ty\]",
    r"\[.*?\]",  # Bất kỳ ngoặc vuông nào chứa text
]


def validate_crm_output(result: str) -> dict:
    """
    Kiểm tra output từ CRM B2B pipeline:
      - Không rỗng
      - Không chứa các placeholder [Tên của bạn], [Chức danh]...
      - Có nội dung đủ dài (>50 ký tự)
      - Có chữ ký Esgoo CRM

    Returns:
        dict: {"valid": bool, "issues": list[str], "sanitized": str}
    """
    issues = []

    if not result or not result.strip():
        return {"valid": False, "issues": ["Output rỗng"], "sanitized": ""}

    cleaned = result.strip()

    # Kiểm tra placeholder
    found_placeholders = []
    for pattern in _PLACEHOLDER_PATTERNS:
        matches = re.findall(pattern, cleaned, flags=re.IGNORECASE)
        if matches:
            found_placeholders.extend(matches)

    if found_placeholders:
        issues.append(
            f"Phát hiện {len(found_placeholders)} placeholder cần thay thế: "
            + ", ".join(set(found_placeholders))
        )

    # Kiểm tra độ dài
    if len(cleaned) < 50:
        issues.append(f"Output quá ngắn ({len(cleaned)} ký tự, cần >=50)")

    # Kiểm tra chữ ký Esgoo
    has_signature = any(
        keyword in cleaned.lower()
        for keyword in ["esgoo", "hỗ trợ kỹ thuật", "đội ngũ hỗ trợ"]
    )
    if not has_signature:
        issues.append("Thiếu chữ ký Esgoo CRM trong email phản hồi")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "sanitized": cleaned,
    }


# ---------------------------------------------------------------------------
# 4. Output Validation — Market Research Report
# ---------------------------------------------------------------------------

def validate_markdown_report(result: str) -> dict:
    """
    Kiểm tra output từ Market Research pipeline:
      - Không rỗng
      - Có ít nhất 1 heading Markdown (# hoặc ##)
      - Có nội dung đủ dài (>100 ký tự)
      - Không chứa cảnh báo lỗi tool thay vì nội dung thực

    Returns:
        dict: {"valid": bool, "issues": list[str], "sanitized": str}
    """
    issues = []

    if not result or not result.strip():
        return {"valid": False, "issues": ["Báo cáo rỗng"], "sanitized": ""}

    cleaned = result.strip()

    # Kiểm tra Markdown heading
    has_heading = bool(re.search(r"^#{1,3}\s+.+", cleaned, re.MULTILINE))
    if not has_heading:
        issues.append("Báo cáo thiếu heading Markdown (# hoặc ##)")

    # Kiểm tra độ dài
    if len(cleaned) < 100:
        issues.append(f"Báo cáo quá ngắn ({len(cleaned)} ký tự, cần >=100)")

    # Kiểm tra lỗi tool leaked vào output
    error_indicators = [
        "Lỗi tìm kiếm:",
        "Lỗi truy vấn",
        "rate limit",
        "API error",
    ]
    for indicator in error_indicators:
        if indicator.lower() in cleaned.lower():
            issues.append(f"Báo cáo chứa thông báo lỗi: '{indicator}'")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "sanitized": cleaned,
    }
