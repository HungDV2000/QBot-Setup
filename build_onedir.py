#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build Script - --onedir Mode (giống MAXBirkinCat 207.96)
Build tất cả modules thành .exe files với cấu trúc folder (--onedir)
Output: Folder chứa .exe files + thư viện Python được extract
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

# ========================================
# CẤU HÌNH BUILD
# ========================================

# Danh sách các module cần build (giống MAXBirkinCat 207.96 - 9 modules, không có check_status)
MODULES = [
    "hd_order.py",
    "hd_order_123.py", 
    "hd_update_all.py",
    "hd_update_price.py",
    "hd_update_cho_va_khop.py",
    "hd_update_danhmuc.py",
    "hd_alert_possition_and_open_order.py",
    "hd_cancel_orders_schedule.py",
    "hd_isolated_crossed_converter.py",
    # "check_status.py",  # Bỏ qua như bản build MAXBirkinCat 207.96
]

# Hidden imports - các module Python cần include
HIDDEN_IMPORTS = [
    # Local modules
    'cst',
    'utils',
    'gg_sheet_factory',
    'telegram_factory',
    'binance_utils',
    'binance_order',
    
    # Google API
    'google.auth.transport.requests',
    'google.oauth2.credentials',
    'google_auth_oauthlib.flow',
    'googleapiclient.discovery',
    'googleapiclient.errors',
    
    # Trading & Telegram
    'telegram',
    'telegram.ext',
    'ccxt',
    'ccxt.base.errors',
    
    # Data processing
    'pandas',
    'numpy',
    'asyncio',
    'aiohttp',
    'requests',
]

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
# MAIN BUILD FUNCTIONS
# ========================================

def check_requirements():
    """Kiểm tra yêu cầu hệ thống"""
    print_step("Kiểm tra yêu cầu hệ thống...")
    
    # Check Python version
    py_version = sys.version_info
    print(f"Python version: {py_version.major}.{py_version.minor}.{py_version.micro}")
    if py_version.major < 3 or (py_version.major == 3 and py_version.minor < 9):
        print_error("Cần Python 3.9 trở lên!")
        return False
    
    # Check PyInstaller
    try:
        import PyInstaller
        print(f"PyInstaller version: {PyInstaller.__version__}")
        print_success("PyInstaller đã cài đặt")
    except ImportError:
        print_error("PyInstaller chưa được cài đặt!")
        print("\nCài đặt PyInstaller:")
        print("  python3 -m pip install pyinstaller")
        return False
    
    # Check Python packages (critical for hidden imports)
    print_step("Kiểm tra Python packages...")
    critical_packages = {
        'google.auth': 'google-auth',
        'googleapiclient': 'google-api-python-client',
        'google_auth_oauthlib': 'google-auth-oauthlib',
        'telegram': 'python-telegram-bot',
        'ccxt': 'ccxt',
        'pandas': 'pandas',
        'numpy': 'numpy',
        'aiohttp': 'aiohttp',
        'requests': 'requests',
    }
    
    missing_packages = []
    import importlib
    
    for module_name, package_name in critical_packages.items():
        try:
            # Try to import the module directly (more reliable than find_loader)
            importlib.import_module(module_name)
            print(f"  ✓ {module_name}")
        except (ImportError, ModuleNotFoundError):
            # If import fails, try to import base module
            base_module = module_name.split('.')[0]
            try:
                importlib.import_module(base_module)
                print(f"  ✓ {module_name} (base module {base_module} found)")
            except (ImportError, ModuleNotFoundError):
                missing_packages.append((module_name, package_name))
                print_warning(f"  ❌ {module_name} (package: {package_name})")
        except Exception as e:
            # Other exceptions - assume package exists but log warning
            print_warning(f"  ⚠️  {module_name} (warning: {str(e)[:50]})")
    
    if missing_packages:
        print_error(f"Thiếu {len(missing_packages)} packages quan trọng!")
        print("\nCài đặt các packages thiếu:")
        packages_to_install = [pkg for _, pkg in missing_packages]
        print(f"  pip install {' '.join(set(packages_to_install))}")
        print("\nHoặc cài tất cả:")
        print("  pip install google-auth google-auth-oauthlib google-api-python-client python-telegram-bot ccxt pandas numpy aiohttp requests")
        return False
    
    # Check modules exist
    print_step("Kiểm tra các module files...")
    missing_modules = []
    for module in MODULES:
        if not Path(module).exists():
            missing_modules.append(module)
            print_warning(f"  ❌ Module file không tồn tại: {module}")
        else:
            print(f"  ✓ {module}")
    
    if missing_modules:
        print_warning(f"Thiếu {len(missing_modules)} module files, sẽ bỏ qua chúng")
    
    print_success("Kiểm tra yêu cầu hoàn tất")
    return True

def clean_previous_builds():
    """Xóa các file build trước đó"""
    print_step("Dọn dẹp các file build cũ...")
    
    dirs_to_remove = ['build', 'dist', '__pycache__', 'dist_onedir']
    for dir_name in dirs_to_remove:
        if Path(dir_name).exists():
            shutil.rmtree(dir_name)
            print(f"  Đã xóa: {dir_name}/")
    
    # Remove .spec files
    for spec_file in Path(".").glob("*.spec"):
        spec_file.unlink()
        print(f"  Đã xóa: {spec_file.name}")
    
    print_success("Dọn dẹp hoàn tất")

def build_single_module(module_name):
    """Build một module thành .exe với --onedir mode"""
    print_header(f"BUILD: {module_name}")
    
    # Kiểm tra file tồn tại
    if not Path(module_name).exists():
        print_error(f"File không tồn tại: {module_name}")
        return False
    
    # Tạo command PyInstaller
    exe_name = module_name.replace('.py', '')
    
    cmd = [
        sys.executable,  # python3 executable
        '-m', 'PyInstaller',
        # KHÔNG có --onefile → sẽ dùng --onedir (directory mode)
        '--console',       # Console app (để xem logs)
        '--name', exe_name,
        '--clean',         # Clean cache
    ]
    
    # Add hidden imports
    for hidden_import in HIDDEN_IMPORTS:
        cmd.extend(['--hidden-import', hidden_import])
    
    # Add module
    cmd.append(module_name)
    
    # Print command
    print(f"\nCommand: {' '.join(cmd)}\n")
    sys.stdout.flush()
    
    # Run PyInstaller
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8'
        )
        
        # Print output
        if result.stdout:
            for line in result.stdout.splitlines():
                if 'ERROR' in line or 'Error' in line:
                    print(f"  ⚠️  {line}")
                elif 'WARNING' in line or 'Warning' in line:
                    print(f"  ⚠️  {line}")
                elif 'Successfully' in line or 'completed' in line:
                    print(f"  ✓ {line}")
        
        # Check result
        if result.returncode == 0:
            # Với --onedir, output sẽ ở trong dist/exe_name/exe_name.exe
            exe_dir = Path('dist') / exe_name
            exe_file = exe_dir / f"{exe_name}.exe"
            
            if exe_dir.exists():
                print_success(f"Build thành công: {module_name}")
                print(f"  Output folder: {exe_dir}")
                return True
            else:
                print_error(f"Build failed - không tìm thấy folder output: {exe_dir}")
                return False
        else:
            print_error(f"Build failed với exit code: {result.returncode}")
            return False
            
    except Exception as e:
        print_error(f"Exception khi build: {e}")
        import traceback
        traceback.print_exc()
        return False

def merge_output_folders():
    """Merge tất cả output folders vào 1 folder duy nhất (giống MAXBirkinCat 207.96)"""
    print_header("MERGE OUTPUT FOLDERS")
    
    dist_dir = Path("dist")
    if not dist_dir.exists():
        print_error("Folder dist/ không tồn tại!")
        return False
    
    # Tạo folder output cuối cùng
    output_dir = Path("dist_onedir")
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir()
    
    print_step(f"Tạo folder output: {output_dir}")
    
    # Danh sách các folders đã build
    built_folders = []
    
    # Merge từng folder
    for module in MODULES:
        if not Path(module).exists():
            continue
        
        exe_name = module.replace('.py', '')
        source_folder = dist_dir / exe_name
        
        if not source_folder.exists():
            print_warning(f"Folder không tồn tại: {source_folder}")
            continue
        
        print_step(f"Merging {exe_name}...")
        
        # Kiểm tra xem có _internal folder không
        internal_source = source_folder / "_internal"
        source_to_merge = internal_source if internal_source.exists() else source_folder
        
        # Copy tất cả files và folders từ source (hoặc _internal/) vào output_dir root
        items_copied = 0
        items_skipped = 0
        
        for item in source_to_merge.iterdir():
            dest = output_dir / item.name
            
            # Nếu đã tồn tại, chỉ skip nếu là file (folders sẽ được merge)
            if dest.exists() and dest.is_file():
                items_skipped += 1
                continue
            
            try:
                if item.is_file():
                    shutil.copy2(item, dest)
                    items_copied += 1
                elif item.is_dir():
                    # Nếu folder đã tồn tại, merge nội dung (không ghi đè)
                    if dest.exists():
                        # Merge nội dung folder
                        for subitem in item.rglob('*'):
                            if subitem.is_file():
                                rel_path = subitem.relative_to(item)
                                subdest = dest / rel_path
                                subdest.parent.mkdir(parents=True, exist_ok=True)
                                if not subdest.exists():
                                    shutil.copy2(subitem, subdest)
                                    items_copied += 1
                    else:
                        # Copy toàn bộ folder
                        shutil.copytree(item, dest, dirs_exist_ok=True)
                        items_copied += 1
            except Exception as e:
                print_warning(f"  Không thể copy {item.name}: {e}")
        
        # Copy file .exe chính vào root của output_dir
        exe_file = source_folder / f"{exe_name}.exe"
        if exe_file.exists():
            dest_exe = output_dir / f"{exe_name}.exe"
            if not dest_exe.exists():
                shutil.copy2(exe_file, dest_exe)
            print(f"  ✓ Copied: {exe_name}.exe ({items_copied} items, {items_skipped} skipped)")
            built_folders.append(exe_name)
    
    print_success(f"Đã merge {len(built_folders)} modules vào {output_dir}")
    
    # Đảm bảo không còn _internal/ folder (đã được merge ở trên)
    # Nếu còn sót, flatten nó
    flatten_any_remaining_internal_folders(output_dir)
    
    return True

def flatten_any_remaining_internal_folders(output_dir):
    """Kiểm tra và flatten bất kỳ _internal/ folder nào còn sót lại"""
    print_step("Kiểm tra và flatten các _internal/ folders còn sót...")
    
    # Tìm tất cả _internal folders
    internal_dirs = list(output_dir.rglob("_internal"))
    
    if not internal_dirs:
        print("  ✓ Không có _internal/ folder nào")
        return
    
    for internal_dir in internal_dirs:
        if not internal_dir.is_dir():
            continue
        
        print(f"  Flattening: {internal_dir.relative_to(output_dir)}")
        moved_count = 0
        skipped_count = 0
        
        # Di chuyển tất cả files và folders từ _internal/ ra parent
        parent_dir = internal_dir.parent
        
        for item in internal_dir.iterdir():
            dest = parent_dir / item.name
            
            if dest.exists():
                # Nếu là folder, merge nội dung
                if item.is_dir() and dest.is_dir():
                    for subitem in item.rglob('*'):
                        if subitem.is_file():
                            rel_path = subitem.relative_to(item)
                            subdest = dest / rel_path
                            subdest.parent.mkdir(parents=True, exist_ok=True)
                            if not subdest.exists():
                                shutil.copy2(subitem, subdest)
                                moved_count += 1
                else:
                    skipped_count += 1
                continue
            
            try:
                if item.is_file():
                    shutil.move(str(item), str(dest))
                    moved_count += 1
                elif item.is_dir():
                    shutil.move(str(item), str(dest))
                    moved_count += 1
            except Exception as e:
                print_warning(f"    Không thể di chuyển {item.name}: {e}")
        
        # Xóa _internal/ folder
        try:
            if internal_dir.exists():
                if any(internal_dir.iterdir()):
                    # Còn files - force remove
                    shutil.rmtree(internal_dir)
                else:
                    internal_dir.rmdir()
                print(f"    ✓ Đã xóa {internal_dir.name}/ ({moved_count} moved, {skipped_count} skipped)")
        except Exception as e:
            print_warning(f"    Không thể xóa {internal_dir}: {e}")
    
    print_success("Đã flatten tất cả _internal/ folders")

def copy_config_files():
    """Copy config files vào output folder"""
    print_step("Copy config files...")
    
    output_dir = Path("dist_onedir")
    if not output_dir.exists():
        print_error("Folder dist_onedir/ chưa được tạo!")
        return False
    
    # Copy config.ini.example
    if Path('config.ini.example').exists():
        shutil.copy2('config.ini.example', output_dir / 'config.ini.example')
        print(f"  ✓ Copied: config.ini.example")
    
    # Copy credentials.json nếu có (optional)
    if Path('credentials.json').exists():
        print_warning("Phát hiện credentials.json - KHÔNG copy (bảo mật)")
        print("  User cần tự copy credentials.json vào dist_onedir/")
    
    print_success("Copy config files hoàn tất")

def create_readme():
    """Tạo README.txt cho output folder"""
    print_step("Tạo README.txt...")
    
    output_dir = Path("dist_onedir")
    if not output_dir.exists():
        return False
    
    # Lấy build date (cross-platform)
    build_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    readme_content = f"""QBot - Trading Bot Distribution (--onedir Mode)

Build date: {build_date}
Python version: {sys.version.split()[0]}
Build mode: --onedir (directory mode)

CÁC MODULE ĐÃ BUILD:
"""
    for module in MODULES:
        if Path(module).exists():
            readme_content += f"  - {module.replace('.py', '.exe')}\n"
    
    readme_content += f"""
CẤU TRÚC:
  - Các file .exe ở root folder
  - Thư viện Python trong các subfolders (numpy/, pandas/, etc.)
  - config.ini.example: File config mẫu

HƯỚNG DẪN SỬ DỤNG:
  1. Copy credentials.json vào folder này (nếu cần)
  2. Tạo config.ini từ config.ini.example
  3. Điền thông tin API vào config.ini
  4. Chạy các file .exe trực tiếp

LƯU Ý:
  - Cần giữ nguyên cấu trúc folder để các .exe chạy được
  - KHÔNG xóa các subfolders (numpy/, pandas/, etc.)
  - Mỗi .exe cần tất cả files trong folder này

Build được tạo từ source04062025
"""
    
    readme_path = output_dir / "README.txt"
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print_success("Đã tạo README.txt")
    return True

def show_summary():
    """Hiển thị tổng kết"""
    print_header("BUILD HOÀN TẤT")
    
    output_dir = Path("dist_onedir")
    if not output_dir.exists():
        print_error("Build failed - không có output folder!")
        return
    
    # Đếm số file .exe
    exe_files = list(output_dir.glob("*.exe"))
    
    print(f"\n✅ Đã build thành công: {len(exe_files)} modules")
    print(f"\n📁 Output folder: {output_dir.absolute()}")
    
    # Tính kích thước
    try:
        total_size = sum(f.stat().st_size for f in output_dir.rglob('*') if f.is_file())
        size_mb = total_size / (1024 * 1024)
        print(f"📦 Tổng kích thước: {size_mb:.1f} MB")
    except:
        pass
    
    print(f"\n📋 Các file .exe:")
    for exe_file in sorted(exe_files):
        try:
            size_mb = exe_file.stat().st_size / (1024 * 1024)
            print(f"  - {exe_file.name} ({size_mb:.1f} MB)")
        except:
            print(f"  - {exe_file.name}")
    
    print(f"\n🎯 Cấu trúc:")
    print(f"  ✅ --onedir mode (folder chứa .exe + libraries)")
    print(f"  ✅ {len(exe_files)} modules")
    print(f"  ✅ Thư viện Python được extract")
    
    print(f"\n📝 Bước tiếp theo:")
    print(f"  1. Kiểm tra folder: {output_dir}")
    print(f"  2. Copy credentials.json nếu cần")
    print(f"  3. Tạo config.ini từ config.ini.example")
    print(f"  4. Test chạy các .exe files")

# ========================================
# MAIN
# ========================================

def main():
    """Main function"""
    print_header("QBot - Build Script (--onedir Mode)")
    print("Build mode: --onedir (directory mode)")
    print("Output: Folder chứa .exe files + thư viện Python")
    print("Cấu trúc:")
    
    # Check requirements
    if not check_requirements():
        print_error("Kiểm tra yêu cầu thất bại!")
        sys.exit(1)
    
    # Clean previous builds
    clean_previous_builds()
    
    # Build từng module
    print_header("BUILDING MODULES")
    success_count = 0
    failed_modules = []
    
    for i, module in enumerate(MODULES, 1):
        if not Path(module).exists():
            print_warning(f"[{i}/{len(MODULES)}] Skip: {module} (not found)")
            continue
        
        print(f"\n[{i}/{len(MODULES)}] ", end="")
        if build_single_module(module):
            success_count += 1
        else:
            failed_modules.append(module)
    
    # Summary
    print_header("BUILD SUMMARY")
    print(f"✅ Thành công: {success_count}/{len(MODULES)}")
    if failed_modules:
        print(f"❌ Thất bại: {len(failed_modules)}")
        for module in failed_modules:
            print(f"  - {module}")
    
    if success_count == 0:
        print_error("Không có module nào được build thành công!")
        sys.exit(1)
    
    # Merge output folders
    if not merge_output_folders():
        print_error("Lỗi khi merge output folders!")
        sys.exit(1)
    
    # Copy config files
    copy_config_files()
    
    # Create README
    create_readme()
    
    # Show summary
    show_summary()

if __name__ == '__main__':
    try:
        main()
        # Build completed successfully
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n\n⚠️  Build bị hủy bởi user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Lỗi không mong đợi: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
