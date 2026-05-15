"""
Gọi Binance USD-M Futures (signed) và xử lý lỗi algo orders.
Dùng chung cho hd_order, hd_order_123, hd_update_cho_va_khop.
"""
import hashlib
import hmac
import json
import logging
import time
import urllib.parse

import requests

import cst

logger = logging.getLogger(__name__)

FAPI_BASE = 'https://fapi.binance.com'

# 400 + các mã này = không có lịch sử algo / symbol không hỗ trợ query → coi như []
ALGO_QUERY_EMPTY_BINANCE_CODES = frozenset({
    -1121,   # Invalid symbol
    -2013,   # Order does not exist
    -2011,   # Unknown order sent
    -4140,   # Invalid symbol status
    -4108,   # Symbol is on delivering/settling/closed
})


def clean_futures_symbol(symbol: str) -> str:
    return symbol.replace('/', '').replace(':USDT', '').upper().strip()


def parse_binance_error_body(response) -> tuple:
    """Trả (code int|None, msg str)."""
    if response is None:
        return None, ''
    try:
        data = response.json()
        if isinstance(data, dict):
            code = data.get('code')
            if code is not None:
                try:
                    code = int(code)
                except (TypeError, ValueError):
                    pass
            return code, str(data.get('msg', '') or '')
    except (json.JSONDecodeError, ValueError):
        pass
    try:
        return None, (response.text or '')[:300]
    except Exception:
        return None, ''


def is_algo_query_empty_error(http_status: int, response) -> bool:
    """
    HTTP 400 từ openAlgoOrders / allAlgoOrders thường là symbol không có algo
    hoặc không hỗ trợ endpoint — không phải lỗi mạng → trả [] thay vì fail-safe.
    """
    if http_status != 400:
        return False
    code, msg = parse_binance_error_body(response)
    if code in ALGO_QUERY_EMPTY_BINANCE_CODES:
        return True
    msg_l = (msg or '').lower()
    if 'invalid symbol' in msg_l or 'unknown symbol' in msg_l:
        return True
    if 'order does not exist' in msg_l:
        return True
    return False


def futures_signed_request(
    method: str,
    endpoint: str,
    params=None,
    *,
    api_key=None,
    secret_key=None,
    max_retries: int = 3,
    timeout: int = 10,
):
    """
    Gọi FAPI có ký. Trả JSON thành công, hoặc None nếu lỗi thật sau retry.
    Không nuốt HTTP 400 — caller dùng is_algo_query_empty_error().
    """
    if params is None:
        params = {}
    if api_key is None:
        api_key = cst.key_binance
    if secret_key is None:
        secret_key = cst.secret_binance

    url = f'{FAPI_BASE}{endpoint}'
    headers = {'X-MBX-APIKEY': api_key}
    method = method.upper()

    for attempt in range(max_retries):
        req_params = dict(params)
        req_params['timestamp'] = int(time.time() * 1000)
        if 'recvWindow' not in req_params:
            req_params['recvWindow'] = 60000

        query_string = urllib.parse.urlencode(req_params)
        signature = hmac.new(
            secret_key.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256,
        ).hexdigest()
        req_params['signature'] = signature

        try:
            if method == 'GET':
                response = requests.get(url, params=req_params, headers=headers, timeout=timeout)
            elif method == 'DELETE':
                response = requests.delete(url, params=req_params, headers=headers, timeout=timeout)
            else:
                logger.error(f'[FAPI] Method không hỗ trợ: {method}')
                return None

            response.raise_for_status()
            return response.json()

        except requests.exceptions.Timeout:
            wait = 2 ** (attempt + 1)
            logger.warning(f'[FAPI] Timeout {attempt + 1}/{max_retries} {endpoint}, chờ {wait}s')
            if attempt < max_retries - 1:
                time.sleep(wait)

        except requests.exceptions.HTTPError as e:
            resp = e.response
            status = resp.status_code if resp is not None else 0
            if is_algo_query_empty_error(status, resp):
                code, msg = parse_binance_error_body(resp)
                logger.debug(
                    f'[FAPI] {endpoint} HTTP {status} coi như không có algo order '
                    f'(code={code}, msg={msg[:80] if msg else ""})'
                )
                return []
            wait = 2 ** (attempt + 1)
            code, msg = parse_binance_error_body(resp)
            logger.warning(
                f'[FAPI] HTTP {status} {attempt + 1}/{max_retries} {endpoint} '
                f'code={code} msg={msg[:120] if msg else ""}'
            )
            if attempt < max_retries - 1:
                time.sleep(wait)

        except Exception as e:
            wait = 2 ** (attempt + 1)
            logger.warning(f'[FAPI] Lỗi {attempt + 1}/{max_retries} {endpoint}: {e}')
            if attempt < max_retries - 1:
                time.sleep(wait)

    logger.error(f'[FAPI] Hết retry cho {endpoint}')
    return None


def normalize_algo_orders_response(response, symbol_hint: str = ''):
    """
    Chuẩn hóa body algo API.
    None = lỗi thật; [] = thành công, không có order; list = có order.
    """
    if response is None:
        return None
    if response == []:
        return []
    if isinstance(response, list):
        return response
    if isinstance(response, dict):
        if 'data' in response:
            data = response['data']
            return data if isinstance(data, list) else []
        code = response.get('code')
        try:
            code = int(code) if code is not None else None
        except (TypeError, ValueError):
            code = None
        if code in (200, 0) or str(code) == '200':
            return []
        if code in ALGO_QUERY_EMPTY_BINANCE_CODES:
            return []
        logger.warning(f'[FAPI] Response algo không rõ cho {symbol_hint}: {response}')
        return None
    logger.warning(f'[FAPI] Kiểu response không hỗ trợ cho {symbol_hint}: {type(response)}')
    return None


def fetch_algo_orders_for_symbol(symbol: str, *, history_hours: int = 24):
    """
    Lấy algo orders cho 1 symbol.
    1) openAlgoOrders?symbol= (lệnh đang mở — tránh 400 allAlgoOrders)
    2) allAlgoOrders?symbol=&startTime= (lịch sử gần để bắt TRIGGERED/CANCELED mới)
    Gộp theo algoId, bỏ trùng.
    """
    symbol_clean = clean_futures_symbol(symbol)
    if not symbol_clean or '-' in symbol_clean:
        return []

    merged = {}
    for order in _fetch_open_algo_orders(symbol_clean) or []:
        aid = order.get('algoId')
        if aid is not None:
            merged[aid] = order

    history = _fetch_all_algo_orders_recent(symbol_clean, history_hours)
    if history is None:
        # Lỗi thật khi lấy history — nếu đã có open thì vẫn trả open
        return list(merged.values()) if merged else None
    for order in history:
        aid = order.get('algoId')
        if aid is not None:
            merged[aid] = order

    return list(merged.values())


def _fetch_open_algo_orders(symbol_clean: str):
    response = futures_signed_request(
        'GET', '/fapi/v1/openAlgoOrders', {'symbol': symbol_clean}, max_retries=2
    )
    return normalize_algo_orders_response(response, symbol_clean)


def _fetch_all_algo_orders_recent(symbol_clean: str, history_hours: int):
    start_ms = int((time.time() - history_hours * 3600) * 1000)
    response = futures_signed_request(
        'GET',
        '/fapi/v1/allAlgoOrders',
        {'symbol': symbol_clean, 'startTime': start_ms, 'limit': 500},
        max_retries=3,
    )
    return normalize_algo_orders_response(response, symbol_clean)
