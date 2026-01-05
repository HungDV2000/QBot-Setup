#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script tự động extract và decompile từ PyInstaller .exe về Python source code
Sử dụng: python3 extract_from_exe.py <path_to_exe_file>
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from datetime import datetime

# ========================================
# HELPER FUNCTIONS
# ========================================

def print_header(text):
    """In header đẹp"""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)

def print_step(text):
    """In bước đang thực hiện"""
    print(f"\n🔹 {text}")

def print_success(text):
    """In thông báo thành công"""
    print(f"✅ {text}")

def print_error(text):
    """In thông báo lỗi"""
    print(f"❌ {text}")

def print_warning(text):
    """In cảnh báo"""
    print(f"⚠️  {text}")

# ========================================
# MAIN FUNCTIONS
# ========================================

def check_tools():
    """Kiểm tra các công cụ cần thiết"""
    print_step("Kiểm tra công cụ cần thiết...")
    
    # Check Python version
    py_version = sys.version_info
    print(f"  Python version: {py_version.major}.{py_version.minor}.{py_version.micro}")
    if py_version.major < 3 or (py_version.major == 3 and py_version.minor < 7):
        print_warning("  Python 3.7+ được khuyến nghị")
    
    tools_status = {
        'pyinstxtractor': False,
        'uncompyle6': False,
    }
    
    # Check uncompyle6
    try:
        import uncompyle6
        print(f"  ✓ uncompyle6: {uncompyle6.__version__}")
        tools_status['uncompyle6'] = True
    except ImportError:
        print_warning("  ❌ uncompyle6 chưa được cài đặt")
        print("    Cài đặt: pip install uncompyle6")
    
    # Check pyinstxtractor
    # Tải pyinstxtractor.py từ internet nếu chưa có
    pyinstxtractor_path = Path("pyinstxtractor.py")
    if not pyinstxtractor_path.exists():
        print_warning("  ❌ pyinstxtractor.py chưa có trong thư mục hiện tại")
        print("    Đang tải pyinstxtractor.py...")
        
        try:
            # Try using requests first (more reliable)
            try:
                import requests
                url = "https://raw.githubusercontent.com/extremecoders-re/pyinstxtractor/master/pyinstxtractor.py"
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                with open("pyinstxtractor.py", 'wb') as f:
                    f.write(response.content)
                print_success("  ✓ Đã tải pyinstxtractor.py (dùng requests)")
                tools_status['pyinstxtractor'] = True
            except ImportError:
                # Fallback to urllib if requests not available
                try:
                    import urllib.request
                    url = "https://raw.githubusercontent.com/extremecoders-re/pyinstxtractor/master/pyinstxtractor.py"
                    urllib.request.urlretrieve(url, "pyinstxtractor.py")
                    print_success("  ✓ Đã tải pyinstxtractor.py (dùng urllib)")
                    tools_status['pyinstxtractor'] = True
                except Exception as e2:
                    print_error(f"  Không thể tải pyinstxtractor.py: {e2}")
                    print_warning("    Vui lòng tải thủ công:")
                    print("    1. Truy cập: https://raw.githubusercontent.com/extremecoders-re/pyinstxtractor/master/pyinstxtractor.py")
                    print("    2. Copy nội dung và lưu vào file pyinstxtractor.py trong thư mục hiện tại")
                    print("    3. Chạy lại script")
        except Exception as e:
            print_error(f"  Lỗi khi tải pyinstxtractor.py: {e}")
            print_warning("    Vui lòng tải thủ công:")
            print("    1. Truy cập: https://raw.githubusercontent.com/extremecoders-re/pyinstxtractor/master/pyinstxtractor.py")
            print("    2. Copy nội dung và lưu vào file pyinstxtractor.py trong thư mục hiện tại")
            print("    3. Chạy lại script")
    else:
        print(f"  ✓ pyinstxtractor.py đã có")
        tools_status['pyinstxtractor'] = True
    
    if not all(tools_status.values()):
        print_error("\nMột số công cụ còn thiếu!")
        print("\nCài đặt:")
        print("  pip install uncompyle6")
        return False
    
    print_success("Tất cả công cụ đã sẵn sàng")
    return True

def extract_exe(exe_file_path):
    """Extract PyInstaller .exe file"""
    print_step(f"Extract {exe_file_path.name}...")
    
    exe_file = Path(exe_file_path)
    if not exe_file.exists():
        print_error(f"File không tồn tại: {exe_file}")
        return None
    
    # Check pyinstxtractor.py exists
    pyinstxtractor = Path("pyinstxtractor.py")
    if not pyinstxtractor.exists():
        # Try in current directory
        pyinstxtractor = Path.cwd() / "pyinstxtractor.py"
        if not pyinstxtractor.exists():
            print_error("pyinstxtractor.py không tìm thấy!")
            print("Vui lòng tải thủ công và đặt trong thư mục hiện tại")
            return None
    
    # Output directory
    extracted_dir = exe_file.parent / f"{exe_file.stem}_extracted"
    
    # Clean old extraction if exists
    if extracted_dir.exists():
        print(f"  Xóa folder cũ: {extracted_dir}")
        shutil.rmtree(extracted_dir)
    
    # Run pyinstxtractor - use absolute path
    try:
        pyinstxtractor_abs = pyinstxtractor.resolve()
        exe_file_abs = exe_file.resolve()
        
        result = subprocess.run(
            [sys.executable, str(pyinstxtractor_abs), str(exe_file_abs)],
            capture_output=True,
            text=True,
            cwd=Path.cwd()  # Run from current directory
        )
        
        if result.returncode != 0:
            print_error(f"Extract failed với return code: {result.returncode}")
            if result.stderr:
                print(f"Error: {result.stderr}")
            if result.stdout:
                print(f"Output: {result.stdout[-500:]}")  # Last 500 chars
            return None
        
        if extracted_dir.exists():
            print_success(f"Extract thành công: {extracted_dir}")
            return extracted_dir
        else:
            # Check if extracted in current directory
            possible_dir = Path(f"{exe_file.stem}_extracted")
            if possible_dir.exists():
                print_success(f"Extract thành công: {possible_dir}")
                return possible_dir
            else:
                print_error("Không tìm thấy folder extracted")
                return None
                
    except Exception as e:
        print_error(f"Lỗi khi extract: {e}")
        import traceback
        traceback.print_exc()
        return None

def find_pyc_files(extracted_dir):
    """Tìm tất cả file .pyc trong extracted directory"""
    print_step("Tìm các file .pyc...")
    
    pyc_files = list(Path(extracted_dir).rglob("*.pyc"))
    print(f"  Tìm thấy {len(pyc_files)} file .pyc")
    
    return pyc_files

def decompile_pyc(pyc_file, output_dir):
    """Decompile một file .pyc về .py"""
    try:
        # Tạo output path giữ nguyên cấu trúc thư mục
        rel_path = pyc_file.relative_to(pyc_file.parts[0])
        py_file = output_dir / rel_path.with_suffix('.py')
        
        # Tạo parent directory
        py_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Decompile
        result = subprocess.run(
            [sys.executable, '-m', 'uncompyle6', str(pyc_file)],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            # Write to file
            with open(py_file, 'w', encoding='utf-8') as f:
                f.write(result.stdout)
            return True, None
        else:
            error_msg = result.stderr or result.stdout
            return False, error_msg
            
    except Exception as e:
        return False, str(e)

def decompile_all(pyc_files, extracted_dir, output_base_dir):
    """Decompile tất cả file .pyc"""
    print_step(f"Decompile {len(pyc_files)} file .pyc...")
    
    # Tạo output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(output_base_dir) / f"decompiled_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    success_count = 0
    failed_count = 0
    failed_files = []
    
    for i, pyc_file in enumerate(pyc_files, 1):
        rel_path = pyc_file.relative_to(extracted_dir)
        print(f"  [{i}/{len(pyc_files)}] Decompiling: {rel_path}...", end=" ")
        
        success, error = decompile_pyc(pyc_file, output_dir)
        
        if success:
            print("✓")
            success_count += 1
        else:
            print("❌")
            failed_count += 1
            failed_files.append((rel_path, error))
            print(f"      Error: {str(error)[:100]}")
    
    print(f"\n  ✅ Thành công: {success_count}/{len(pyc_files)}")
    if failed_count > 0:
        print(f"  ❌ Thất bại: {failed_count}/{len(pyc_files)}")
    
    # Save failed files list
    if failed_files:
        failed_list_path = output_dir / "_failed_files.txt"
        with open(failed_list_path, 'w', encoding='utf-8') as f:
            f.write("CÁC FILE DECOMPILE THẤT BẠI:\n\n")
            for file_path, error in failed_files:
                f.write(f"{file_path}\n")
                f.write(f"  Error: {error}\n\n")
        print(f"  📝 Danh sách file thất bại: {failed_list_path}")
    
    return output_dir

def extract_pyz_archive(extracted_dir):
    """Extract PYZ archive nếu có"""
    print_step("Kiểm tra và extract PYZ archive...")
    
    pyz_files = list(Path(extracted_dir).rglob("PYZ-*.pyz"))
    
    if not pyz_files:
        print("  Không tìm thấy PYZ archive")
        return None
    
    for pyz_file in pyz_files:
        print(f"  Tìm thấy: {pyz_file}")
        pyz_extracted = pyz_file.parent / f"{pyz_file.stem}_extracted"
        
        if pyz_extracted.exists():
            print(f"  ✓ Đã extract: {pyz_extracted}")
            continue
        
        # Try to extract using pyinstxtractor
        try:
            pyinstxtractor = Path("pyinstxtractor.py")
            if not pyinstxtractor.exists():
                pyinstxtractor = Path.cwd() / "pyinstxtractor.py"
            
            if pyinstxtractor.exists():
                pyinstxtractor_abs = pyinstxtractor.resolve()
                pyz_file_abs = pyz_file.resolve()
                result = subprocess.run(
                    [sys.executable, str(pyinstxtractor_abs), str(pyz_file_abs)],
                    capture_output=True,
                    text=True,
                    cwd=Path.cwd()
                )
            
            if pyz_extracted.exists():
                print_success(f"  ✓ Extract thành công: {pyz_extracted}")
            else:
                print_warning(f"  ⚠️  Không extract được: {pyz_file}")
        except Exception as e:
            print_warning(f"  ⚠️  Lỗi khi extract {pyz_file}: {e}")
    
    return pyz_files

def extract_single_exe(exe_file_path, output_base_dir="extracted_source"):
    """Extract và decompile một file .exe"""
    print_header(f"EXTRACT: {exe_file_path.name}")
    
    exe_file = Path(exe_file_path)
    if not exe_file.exists():
        print_error(f"File không tồn tại: {exe_file}")
        return None
    
    # Step 1: Extract .exe
    extracted_dir = extract_exe(exe_file)
    if not extracted_dir:
        return None
    
    # Step 2: Extract PYZ nếu có
    extract_pyz_archive(extracted_dir)
    
    # Step 3: Find all .pyc files
    pyc_files = find_pyc_files(extracted_dir)
    
    if not pyc_files:
        print_warning("Không tìm thấy file .pyc nào")
        return extracted_dir
    
    # Step 4: Decompile all .pyc files
    decompiled_dir = decompile_all(pyc_files, extracted_dir, output_base_dir)
    
    print_success(f"\nHoàn tất! Source code đã được decompile vào: {decompiled_dir}")
    
    return decompiled_dir

def extract_multiple_exes(exe_files, output_base_dir="extracted_source"):
    """Extract nhiều file .exe"""
    print_header("EXTRACT MULTIPLE FILES")
    
    results = {}
    
    for exe_file in exe_files:
        exe_path = Path(exe_file)
        print(f"\n{'='*70}")
        print(f"Processing: {exe_path.name}")
        print('='*70)
        
        result = extract_single_exe(exe_path, output_base_dir)
        results[exe_path.name] = result
    
    # Summary
    print_header("TỔNG KẾT")
    for name, result in results.items():
        if result:
            print(f"✅ {name}: {result}")
        else:
            print(f"❌ {name}: Failed")
    
    return results

# ========================================
# MAIN
# ========================================

def main():
    """Main function"""
    print_header("Extract Source Code từ PyInstaller .exe")
    
    # Check tools
    if not check_tools():
        print_error("Thiếu công cụ cần thiết!")
        sys.exit(1)
    
    # Parse arguments
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python3 extract_from_exe.py <exe_file_path>")
        print("  python3 extract_from_exe.py <exe_file1> <exe_file2> ...")
        print("\nExample:")
        print("  python3 extract_from_exe.py '../MAXBirkinCat 207.96/hd_order.exe'")
        print("  python3 extract_from_exe.py '*.exe'  # Extract tất cả .exe trong folder hiện tại")
        sys.exit(1)
    
    # Get exe files
    exe_files = []
    for arg in sys.argv[1:]:
        if '*' in arg:
            # Glob pattern
            exe_files.extend(Path('.').glob(arg))
        else:
            # Single file
            exe_files.append(Path(arg))
    
    # Filter only .exe files that exist
    exe_files = [f for f in exe_files if f.exists() and f.suffix.lower() == '.exe']
    
    if not exe_files:
        print_error("Không tìm thấy file .exe nào!")
        sys.exit(1)
    
    print(f"\nTìm thấy {len(exe_files)} file .exe:")
    for exe_file in exe_files:
        print(f"  - {exe_file}")
    
    # Extract
    if len(exe_files) == 1:
        result = extract_single_exe(exe_files[0])
    else:
        result = extract_multiple_exes(exe_files)
    
    if result:
        print_success("\n✅ Extract hoàn tất!")
        print(f"\n📁 Output directory: {result}")
        print("\n⚠️  LƯU Ý:")
        print("  - Code đã decompile có thể có lỗi syntax")
        print("  - Comments và docstrings đã bị mất")
        print("  - Formatting có thể không đúng")
        print("  - Cần review và fix thủ công")
    else:
        print_error("\n❌ Extract thất bại!")
        sys.exit(1)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Extract bị hủy bởi user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Lỗi không mong đợi: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
