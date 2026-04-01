import cst
from enum import Enum

spreadsheetId = cst.spreadsheet_id

tab_list_all_ma = "100 mã (50 tăng và 50 giảm)"
tab_cho_va_khop = "Chờ và khớp"
tab_white_list = "list"

tab_dat_lenh = cst.tab_dat_lenh

import os.path
import numpy as np

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Timeout HTTP tránh treo vô hạn khi mạng/Google chậm (mặc định httplib2 có thể không timeout)
try:
  import httplib2
  from google_auth_httplib2 import AuthorizedHttp
  _GSHEET_HTTP_TIMEOUT_SEC = 120
except ImportError:
  httplib2 = None
  AuthorizedHttp = None
  _GSHEET_HTTP_TIMEOUT_SEC = None
from google.auth.exceptions import RefreshError  # ✅ Thêm import RefreshError
import logging

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = None
service = None
spreadsheets_service = None  # Cache spreadsheets() resource
_service_initialized = False  # Flag để tránh tạo service nhiều lần

def init_sheet_api():
  global creds, service, spreadsheets_service, _service_initialized
  
  # ✅ LUÔN LUÔN kiểm tra token validity, ngay cả khi service đã khởi tạo
  # Xác định đường dẫn tuyệt đối của token.json (trong thư mục hiện tại)
  current_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
  token_path = os.path.join(current_dir, "token.json")
  credentials_path = os.path.join(current_dir, "credentials.json")
  
  print(f"📁 Thư mục làm việc: {current_dir}", flush=True)
  print(f"📄 Đường dẫn token.json: {token_path}", flush=True)
  print(f"📄 Token.json tồn tại: {os.path.exists(token_path)}", flush=True)
  logger.info(f"Thư mục làm việc: {current_dir}, Token path: {token_path}, Exists: {os.path.exists(token_path)}")
  
  # Load credentials từ file (nếu có)
  if os.path.exists(token_path):
    try:
      creds = Credentials.from_authorized_user_file(token_path, SCOPES)
      print("✅ Đã load token từ token.json", flush=True)
      logger.info("Đã load token từ token.json")
    except Exception as e:
      print(f"⚠️ Lỗi khi load token.json: {e}, sẽ tạo token mới", flush=True)
      logger.warning(f"Lỗi khi load token.json: {e}", exc_info=True)
      creds = None
  else:
    print("⚠️ Không tìm thấy token.json", flush=True)
    logger.info("Không tìm thấy token.json")
    creds = None
  
  # ✅ Logic kiểm tra token theo thứ tự ưu tiên:
  # 1. Nếu token hợp lệ (valid và chưa expired) → Dùng luôn
  # 2. Nếu token expired nhưng có refresh_token → Refresh
  # 3. Nếu không có token hoặc refresh_token bị mất → Tạo mới
  
  if not creds:
    # Trường hợp 1: Chưa có token, tạo mới
    print("🔑 Chưa có token, đang tạo mới...", flush=True)
    logger.info("Chưa có token, đang tạo mới")
    if not os.path.exists(credentials_path):
      error_msg = f"❌ Không tìm thấy credentials.json tại {credentials_path}"
      print(error_msg, flush=True)
      logger.error(error_msg)
      raise FileNotFoundError(f"credentials.json không tồn tại tại {credentials_path}")
    flow = InstalledAppFlow.from_client_secrets_file(
        credentials_path, SCOPES
    )
    creds = flow.run_local_server(port=0)
    print("✅ Đã tạo token mới thành công.", flush=True)
    logger.info("Đã tạo token mới thành công")
    
    # Lưu token mới
    with open(token_path, "w") as token:
      token.write(creds.to_json())
    print(f"✅ Đã lưu token vào {token_path}", flush=True)
    logger.info(f"Đã lưu token vào {token_path}")
    
    # Reset service để dùng token mới
    _service_initialized = False
    spreadsheets_service = None
    
  elif creds.expired and creds.refresh_token:
    # Trường hợp 2: Token expired nhưng có refresh_token → Refresh
    try:
      logger.info("Token đã expired, đang refresh...")
      print("🔄 Token đã expired, đang refresh...", flush=True)
      creds.refresh(Request())
      print("✅ Đã làm mới Google token thành công.", flush=True)
      logger.info("Đã refresh token thành công")
      
      # Lưu token mới
      with open(token_path, "w") as token:
        token.write(creds.to_json())
      print(f"✅ Đã lưu token mới vào {token_path}", flush=True)
      logger.info(f"Đã lưu token mới vào {token_path}")
      
      # Reset service để dùng token mới
      _service_initialized = False
      spreadsheets_service = None
      
    except Exception as e:
      # Nếu refresh thất bại (token bị revoke), xóa token.json và tạo mới
      print(f"⚠️ Không thể làm mới token: {e}", flush=True)
      print("🔄 Xóa token cũ và tạo mới...", flush=True)
      logger.warning(f"Không thể refresh token: {e}, tạo token mới")
      
      if os.path.exists(token_path):
        os.remove(token_path)
        print(f"🗑️ Đã xóa token.json cũ tại {token_path}", flush=True)
        logger.info(f"Đã xóa token.json cũ tại {token_path}")
      
      if not os.path.exists(credentials_path):
        error_msg = f"❌ Không tìm thấy credentials.json tại {credentials_path}"
        print(error_msg, flush=True)
        logger.error(error_msg)
        raise FileNotFoundError(f"credentials.json không tồn tại tại {credentials_path}")
      
      flow = InstalledAppFlow.from_client_secrets_file(
          credentials_path, SCOPES
      )
      creds = flow.run_local_server(port=0)
      print("✅ Đã tạo token mới thành công.", flush=True)
      logger.info("Đã tạo token mới sau khi refresh thất bại")
      
      # Lưu token mới
      with open(token_path, "w") as token:
        token.write(creds.to_json())
      print(f"✅ Đã lưu token mới vào {token_path}", flush=True)
      logger.info(f"Đã lưu token mới vào {token_path}")
      
      # Reset service để dùng token mới
      _service_initialized = False
      spreadsheets_service = None
      
  elif not creds.valid:
    # Trường hợp 3: Token không valid nhưng chưa expired (có thể do vấn đề khác)
    # Thử refresh nếu có refresh_token, nếu không thì tạo mới
    if creds.refresh_token:
      try:
        logger.info("Token không valid nhưng có refresh_token, đang refresh...")
        print("🔄 Token không valid, đang thử refresh...", flush=True)
        creds.refresh(Request())
        print("✅ Đã refresh token thành công.", flush=True)
        logger.info("Đã refresh token thành công")
        
        # Lưu token mới
        with open(token_path, "w") as token:
          token.write(creds.to_json())
        print(f"✅ Đã lưu token mới vào {token_path}", flush=True)
        logger.info(f"Đã lưu token mới vào {token_path}")
        
        # Reset service để dùng token mới
        _service_initialized = False
        spreadsheets_service = None
      except Exception as e:
        print(f"⚠️ Không thể refresh token: {e}, tạo token mới...", flush=True)
        logger.warning(f"Không thể refresh token: {e}, tạo token mới")
        
        if os.path.exists(token_path):
          os.remove(token_path)
          print(f"🗑️ Đã xóa token.json cũ tại {token_path}", flush=True)
          logger.info(f"Đã xóa token.json cũ tại {token_path}")
        
        if not os.path.exists(credentials_path):
          error_msg = f"❌ Không tìm thấy credentials.json tại {credentials_path}"
          print(error_msg, flush=True)
          logger.error(error_msg)
          raise FileNotFoundError(f"credentials.json không tồn tại tại {credentials_path}")
        
        flow = InstalledAppFlow.from_client_secrets_file(
            credentials_path, SCOPES
        )
        creds = flow.run_local_server(port=0)
        print("✅ Đã tạo token mới thành công.", flush=True)
        logger.info("Đã tạo token mới sau khi refresh thất bại")
        
        # Lưu token mới
        with open(token_path, "w") as token:
          token.write(creds.to_json())
        print(f"✅ Đã lưu token mới vào {token_path}", flush=True)
        logger.info(f"Đã lưu token mới vào {token_path}")
        
        # Reset service để dùng token mới
        _service_initialized = False
        spreadsheets_service = None
    else:
      # Không có refresh_token → Tạo mới
      print("⚠️ Token không valid và không có refresh_token, tạo token mới...", flush=True)
      logger.warning("Token không valid và không có refresh_token, tạo token mới")
      
      if os.path.exists(token_path):
        os.remove(token_path)
        print(f"🗑️ Đã xóa token.json cũ tại {token_path}", flush=True)
        logger.info(f"Đã xóa token.json cũ tại {token_path}")
      
      if not os.path.exists(credentials_path):
        error_msg = f"❌ Không tìm thấy credentials.json tại {credentials_path}"
        print(error_msg, flush=True)
        logger.error(error_msg)
        raise FileNotFoundError(f"credentials.json không tồn tại tại {credentials_path}")
      
      flow = InstalledAppFlow.from_client_secrets_file(
          credentials_path, SCOPES
      )
      creds = flow.run_local_server(port=0)
      print("✅ Đã tạo token mới thành công.", flush=True)
      logger.info("Đã tạo token mới")
      
      # Lưu token mới
      with open(token_path, "w") as token:
        token.write(creds.to_json())
      print(f"✅ Đã lưu token mới vào {token_path}", flush=True)
      logger.info(f"Đã lưu token mới vào {token_path}")
      
      # Reset service để dùng token mới
      _service_initialized = False
      spreadsheets_service = None
  else:
    # Trường hợp 4: Token hợp lệ và chưa expired → Dùng luôn
    print("✅ Token hợp lệ, sử dụng token hiện có", flush=True)
    logger.info("Token hợp lệ, sử dụng token hiện có")
  
  # Tạo service nếu chưa có hoặc đã bị reset
  if not _service_initialized or service is None or spreadsheets_service is None:
    try:
      # Tạo service: dùng HTTP có timeout để không bị "đứng im" khi Sheet API không phản hồi
      if httplib2 is not None and AuthorizedHttp is not None and _GSHEET_HTTP_TIMEOUT_SEC:
        http_timeout = httplib2.Http(timeout=_GSHEET_HTTP_TIMEOUT_SEC)
        authed_http = AuthorizedHttp(creds, http=http_timeout)
        service = build("sheets", "v4", http=authed_http)
        logger.info(f"Google Sheets client: HTTP timeout {_GSHEET_HTTP_TIMEOUT_SEC}s")
      else:
        service = build("sheets", "v4", credentials=creds)
      # ✅ Cache spreadsheets() resource để không phải tạo lại
      spreadsheets_service = service.spreadsheets()
      _service_initialized = True  # Đánh dấu đã khởi tạo
      print("✅ Google Sheets service đã khởi tạo thành công.", flush=True)
      logger.info("Google Sheets service đã khởi tạo thành công")
    except HttpError as err:
      print(f"❌ Lỗi khởi tạo Google Sheets service: {err}", flush=True)
      logger.error(f"Lỗi khởi tạo Google Sheets service: {err}", exc_info=True)
      _service_initialized = False
      spreadsheets_service = None

def reset_sheet_api():
  """Reset service để tạo lại kết nối mới (dùng khi token refresh)"""
  global service, spreadsheets_service, _service_initialized
  service = None
  spreadsheets_service = None
  _service_initialized = False
  print("🔄 Đã reset Google Sheets service.", flush=True)

def force_refresh_token():
  """
  Force refresh token khi gặp lỗi RefreshError
  Xóa token cũ và tạo mới nếu cần
  """
  global creds, _service_initialized
  
  logger.warning("⚠️ Token hết hạn hoặc bị revoke, đang force refresh...")
  print("⚠️ Token hết hạn hoặc bị revoke, đang force refresh...", flush=True)
  
  # Reset service
  reset_sheet_api()
  
  # Xóa token.json để force tạo mới
  if os.path.exists("token.json"):
    os.remove("token.json")
    print("🗑️ Đã xóa token.json cũ", flush=True)
  
  # Tạo token mới
  try:
    flow = InstalledAppFlow.from_client_secrets_file(
        "credentials.json", SCOPES
    )
    creds = flow.run_local_server(port=0)
    
    # Lưu token mới
    with open("token.json", "w") as token:
      token.write(creds.to_json())
    
    print("✅ Đã tạo token mới thành công", flush=True)
    logger.info("Đã tạo token mới thành công")
    
    # Khởi tạo lại service
    init_sheet_api()
    return True
    
  except Exception as e:
    print(f"❌ Lỗi khi tạo token mới: {e}", flush=True)
    logger.error(f"Lỗi khi tạo token mới: {e}", exc_info=True)
    return False

def execute_with_retry(func, *args, max_retries=2, **kwargs):
  """
  Wrapper function để tự động retry khi gặp RefreshError
  
  Args:
    func: Function cần gọi (lambda hoặc callable)
    max_retries: Số lần thử lại tối đa (mặc định 2)
    *args, **kwargs: Arguments cho func
  
  Returns:
    Kết quả từ func
  """
  for attempt in range(max_retries + 1):
    try:
      return func()
      
    except RefreshError as e:
      logger.error(f"❌ RefreshError (lần thử {attempt + 1}/{max_retries + 1}): {e}")
      print(f"❌ RefreshError (lần thử {attempt + 1}/{max_retries + 1}): {e}", flush=True)
      
      if attempt < max_retries:
        # Thử force refresh token
        print(f"🔄 Đang thử refresh token (lần {attempt + 1})...", flush=True)
        if force_refresh_token():
          print("✅ Refresh token thành công, thử lại API call...", flush=True)
          continue
        else:
          print("❌ Không thể refresh token, dừng retry", flush=True)
          raise
      else:
        # Hết số lần thử
        print(f"❌ Đã thử {max_retries + 1} lần nhưng vẫn lỗi RefreshError", flush=True)
        logger.critical(f"Không thể refresh token sau {max_retries + 1} lần thử")
        raise
        
    except HttpError as e:
      # ✅ Xử lý lỗi 403 (Permission denied) - có thể do token hết hạn
      if e.resp.status == 403:
        logger.error(f"❌ HttpError 403 - Permission denied (lần thử {attempt + 1}/{max_retries + 1}): {e}")
        print(f"❌ HttpError 403 - Permission denied (lần thử {attempt + 1}/{max_retries + 1}): {e}", flush=True)
        
        if attempt < max_retries:
          # Thử force refresh token khi gặp 403
          print(f"🔄 Đang thử refresh token do lỗi 403 (lần {attempt + 1})...", flush=True)
          if force_refresh_token():
            print("✅ Refresh token thành công, thử lại API call...", flush=True)
            logger.info("Đã refresh token thành công sau lỗi 403, thử lại API call")
            continue
          else:
            print("❌ Không thể refresh token, dừng retry", flush=True)
            logger.error("Không thể refresh token sau lỗi 403")
            raise
        else:
          # Hết số lần thử
          print(f"❌ Đã thử {max_retries + 1} lần nhưng vẫn lỗi 403", flush=True)
          logger.critical(f"Không thể giải quyết lỗi 403 sau {max_retries + 1} lần thử")
          raise
      else:
        # Lỗi HttpError khác (không phải 403)
        logger.error(f"HttpError (status {e.resp.status}): {e}")
        print(f"An error occurred: {e}", flush=True)
        raise
      
    except Exception as e:
      # Lỗi không xác định
      logger.error(f"Unexpected error: {e}", exc_info=True)
      print(f"Unexpected error: {e}", flush=True)
      raise

def get_dat_lenh(range):
  RANGE_NAME = f"'{tab_dat_lenh}'!{range}"
  init_sheet_api()
  
  def _execute():
    result = (
      spreadsheets_service  # ✅ Dùng cached resource
      .values()
      .get(spreadsheetId=spreadsheetId, range=RANGE_NAME)
      .execute()
    )
    return result.get("values", [])
  
  return execute_with_retry(_execute)

def get_cho_va_khop(range):
  RANGE_NAME = f"'{tab_cho_va_khop}'!{range}"
  init_sheet_api()
  
  def _execute():
    result = (
      spreadsheets_service  # ✅ Dùng cached resource
      .values()
      .get(spreadsheetId=spreadsheetId, range=RANGE_NAME)
      .execute()
    )
    return result.get("values", [])
  
  return execute_with_retry(_execute)
  
def get_100_ma(range):
  RANGE_NAME = f"'{tab_list_all_ma}'!{range}"
  init_sheet_api()
  
  def _execute():
    result = (
      spreadsheets_service  # ✅ Dùng cached resource
      .values()
      .get(spreadsheetId=spreadsheetId, range=RANGE_NAME)
      .execute()
    )
    return result.get("values", [])
  
  return execute_with_retry(_execute)
  
def get_white_list():
    RANGE_NAME = f"'{tab_white_list}'!A1:A1000"
    print("📡 Đang đọc whitelist từ Google Sheet (tab 'list')...", flush=True)
    logger.info("Đang đọc whitelist từ Google Sheet (tab 'list')...")
    init_sheet_api()
    
    def _execute():
        result = (
            spreadsheets_service  # ✅ Dùng cached resource
            .values()
            .get(spreadsheetId=spreadsheetId, range=RANGE_NAME)
            .execute()
        )
        rows = result.get("values", [])
        whitelist = []
        for row in rows:
            if not row or not row[0].strip():
                continue
            symbol = row[0].strip().upper()
            # Fix: Chuyển đổi format đúng
            # Từ sheet: "BTC/USDT" → "BTC/USDT:USDT" (format Binance futures)
            if symbol.endswith("/USDT"):
                whitelist.append(symbol + ":USDT")
            elif not symbol.endswith(":USDT"):
                # Nếu chỉ có tên mã (không có /USDT), thêm /USDT:USDT
                whitelist.append(symbol + "/USDT:USDT")
            else:
                whitelist.append(symbol)
        return whitelist
    
    return execute_with_retry(_execute)




def update(tab_name, array_index, value_array):
  index = 2 + array_index
  RANGE_NAME = f"'{tab_name}'!B{index}:P1000"
  init_sheet_api()
  
  def _execute():
    values = [
            value_array
    ]
    body = {"values": values}
    print(body)
    result = (
        spreadsheets_service  # ✅ Dùng cached resource
        .values()
        .update(
            spreadsheetId=spreadsheetId ,
            range=RANGE_NAME,
            valueInputOption="USER_ENTERED",
            body=body,
        )
        .execute()
    )
    print(f"{result.get('updatedCells')} cells updated.")
    return result
  
  return execute_with_retry(_execute)
  
def update_single_value(tab_name, range, value):
  RANGE_NAME = f"'{tab_name}'!{range}"
  init_sheet_api()
  
  def _execute():
    values = [
            [value]
    ]
    body = {"values": values}
    print(body)
    result = (
        spreadsheets_service  # ✅ Dùng cached resource
        .values()
        .update(
            spreadsheetId=spreadsheetId ,
            range=RANGE_NAME,
            valueInputOption="USER_ENTERED",
            body=body,
        )
        .execute()
    )
    print(f"{result.get('updatedCells')} cells updated.")
    return result
  
  return execute_with_retry(_execute)


def update_single_value_to_sheet(sheet_spreadsheet_id: str, sheet_tab_name: str, range: str, value: str):
  """
  Ghi một ô vào sheet bất kỳ (theo spreadsheet_id + tab).
  Dùng khi 1 bot điều khiển nhiều sheet (multi-sheet): ghi đúng sheet theo mã.
  Cùng dùng credentials hiện tại (token.json).
  """
  RANGE_NAME = f"'{sheet_tab_name}'!{range}"
  init_sheet_api()

  def _execute():
    values = [[value]]
    body = {"values": values}
    result = (
      spreadsheets_service
      .values()
      .update(
        spreadsheetId=sheet_spreadsheet_id,
        range=RANGE_NAME,
        valueInputOption="USER_ENTERED",
        body=body,
      )
      .execute()
    )
    logger.info(f"[SHEET] Đã ghi {RANGE_NAME} = '{value}' (spreadsheet {sheet_spreadsheet_id[:8]}...)")
    return result

  return execute_with_retry(_execute)


def replace_nan(array, replace_value):
    nan_indices = np.isnan(array)
    array[nan_indices] = replace_value
    return array

def update_multi(tab_name, array_index, array_2d, from_column_alphabet_name):
  # Fix: Nếu array_index < 0, dùng abs để ghi từ hàng đó trực tiếp
  # Nếu array_index >= 0, dùng công thức 2 + array_index (giữ backward compatibility)
  if array_index < 0:
      index = abs(array_index)
  else:
      index = 2 + array_index
  
  # Fix: Mở rộng range đến cột AZ để đủ chứa tất cả data (52 cột)
  RANGE_NAME = f"'{tab_name}'!{from_column_alphabet_name}{index}:AZ1000"
  
  
  print("----------------------------")
  print(f"Ghi {len(array_2d)} dòng vào {RANGE_NAME}", flush=True)
  init_sheet_api()

  def _execute():
    values = array_2d
    body = {"values": values}
    result = (
        spreadsheets_service  # ✅ Dùng cached resource
        .values()
        .update(
            spreadsheetId=spreadsheetId ,
            range=RANGE_NAME,
            valueInputOption="USER_ENTERED",
            body=body,
        )
        .execute()
    )
    print(f"{result.get('updatedCells')} cells updated.", flush=True)
    return result
  
  return execute_with_retry(_execute)

def clear_multi(tab_name, array_index,  from_column_alphabet_name, end_row=1000, end_column="AZ"):
  """
  Clear dữ liệu trong sheet
  Args:
    tab_name: Tên tab
    array_index: Index (sẽ được convert thành row = 2 + array_index, hoặc nếu < 0 thì dùng abs)
    from_column_alphabet_name: Cột bắt đầu (VD: "A")
    end_row: Hàng kết thúc (default: 1000)
    end_column: Cột kết thúc (default: "AZ")
  """
  # Fix: Nếu array_index < 0, dùng abs để clear từ hàng đó trực tiếp
  # Nếu array_index >= 0, dùng công thức 2 + array_index (giữ backward compatibility)
  if array_index < 0:
      index = abs(array_index)
  else:
      index = 2 + array_index
  
  RANGE_NAME = f"'{tab_name}'!{from_column_alphabet_name}{index}:{end_column}{end_row}"
  print(f"Clear range: {RANGE_NAME}")
  init_sheet_api()

  def _execute():
    result = spreadsheets_service.values().clear(  # ✅ Dùng cached resource
          spreadsheetId=spreadsheetId,
          range=RANGE_NAME,
      ).execute()
    return result
  
  return execute_with_retry(_execute)


