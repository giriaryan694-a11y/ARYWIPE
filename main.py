#########################################
# Author: Aryan
# Copyright: 2025 Aryan
# GitHub: https://github.com/giriaryan694-a11y
# Note: Unauthorized copying without credit is prohibited
#########################################
import os
import random
import string
import sys
import time
import shutil
import threading
import platform
import stat
import subprocess
import gc
import uuid
import re
import pyfiglet  # pip install pyfiglet
from PyQt5 import QtWidgets, QtGui, QtCore
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

# ==========================================
# SYSTEM GUARDRAILS & SAFETY
# ==========================================

def get_platform():
    return platform.system()

def is_critical_path(path):
    """
    PREVENTS OS SUICIDE.
    Returns True if the user tries to wipe system critical directories.
    """
    path = os.path.abspath(path)
    plat = get_platform()
    
    # 1. Protect Root
    if path == os.path.abspath(os.sep): 
        return True
        
    if plat == "Windows":
        sys_root = os.environ.get('SystemRoot', 'C:\\Windows')
        if path.lower().startswith(sys_root.lower()):
            return True
    else:
        criticals = ['/bin', '/boot', '/dev', '/etc', '/lib', '/lib64', '/proc', '/run', '/sbin', '/sys', '/usr', '/var']
        for crit in criticals:
            if path.startswith(crit):
                return True
    return False

def elevate_priority():
    """Request High Priority."""
    try:
        if get_platform() == 'Windows':
            import ctypes
            ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x00000100)
        else:
            os.nice(-19)
    except:
        pass

def nuke_attributes(file_path):
    """
    Strips file flags with RETRY logic to handle OS locking.
    """
    sys_plat = get_platform()
    
    for attempt in range(3):
        try:
            os.chmod(file_path, stat.S_IWRITE | stat.S_IREAD)
            
            if sys_plat == "Windows":
                subprocess.run(['attrib', '-r', '-a', '-s', '-h', file_path], 
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=0x08000000)
            elif sys_plat == "Darwin":
                subprocess.run(['chflags', 'nouchg', file_path], 
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif sys_plat == "Linux":
                subprocess.run(['chattr', '-i', file_path], 
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            return # Success
        except:
            time.sleep(0.1) # Wait and retry

def kill_snapshots():
    """
    Attempts to remove Shadow Copies/TimeMachine.
    Returns (Success: bool, Message: str)
    """
    sys_plat = get_platform()
    try:
        if sys_plat == "Windows":
            res = subprocess.run("vssadmin Delete Shadows /All /Quiet", shell=True, 
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=0x08000000)
            if res.returncode != 0:
                return False, "Failed (Need Admin)"
            return True, "Shadow Copies Purged"
        
        elif sys_plat == "Darwin":
            # 1. List Snapshots
            list_cmd = subprocess.run(["tmutil", "listlocalsnapshots", "/"], 
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            output = list_cmd.stdout
            
            # 2. Parse and Destroy
            # Output format: com.apple.TimeMachine.2023-01-01-120000
            snapshots = re.findall(r'com\.apple\.TimeMachine\.(\S+)', output)
            
            if not snapshots:
                return True, "No Snapshots Found"

            fail_count = 0
            for date_str in snapshots:
                del_cmd = subprocess.run(["tmutil", "deletelocalsnapshots", date_str],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if del_cmd.returncode != 0:
                    fail_count += 1
            
            if fail_count > 0:
                return False, f"Failed to purge {fail_count} snaps (Need Sudo)"
            return True, "All Snapshots Purged"
            
        return True, "Skipped (Linux)"
    except:
        return False, "Error Executing Prune"

def force_block_allocation(file_path):
    """Inflates tiny files. Skips Symlinks."""
    if os.path.islink(file_path):
        return
        
    try:
        size = os.path.getsize(file_path)
        if size < 4096:
            padding = 4096 - size
            with open(file_path, "ab") as f:
                f.write(os.urandom(padding))
                f.flush()
                os.fsync(f.fileno())
    except:
        pass

# ==========================================
# CORE WIPING ENGINE
# ==========================================

def force_flush(f):
    f.flush()
    os.fsync(f.fileno())

def aes_encrypt_file(file_path):
    """Phase 1: AES-256 inplace encryption (Stream Mode)."""
    try:
        length = os.path.getsize(file_path)
        key = os.urandom(32)
        iv = os.urandom(16)
        cipher = Cipher(algorithms.AES(key), modes.CFB(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        
        chunk_size = 1024 * 1024 
        with open(file_path, "r+b") as f:
            bytes_processed = 0
            while bytes_processed < length:
                f.seek(bytes_processed)
                data = f.read(chunk_size)
                if not data: break
                
                encrypted_data = encryptor.update(data)
                f.seek(bytes_processed)
                f.write(encrypted_data)
                
                bytes_processed += len(data)
            
            force_flush(f)
        
        del key; del iv; del cipher
        gc.collect()
        return True
    except Exception:
        return False

def secure_overwrite(file_path, method="random"):
    """Phase 2: Physical Sector Overwriting."""
    try:
        length = os.path.getsize(file_path)
        chunk_size = 1024 * 1024 
        
        patterns = []
        if method == "paranoid":
            patterns = [b'\xFF', b'\x00'] + ['random'] * 5
        elif method == "gutmann":
            patterns = [b'\x55', b'\xAA', 'random', b'\x00', b'\xFF'] * 2
        else: 
            patterns = ['random', 'random', b'\x00']

        with open(file_path, "r+b") as f:
            for pattern in patterns:
                f.seek(0)
                written = 0
                while written < length:
                    write_len = min(chunk_size, length - written)
                    if pattern == 'random':
                        data = os.urandom(write_len)
                    else:
                        repeats = write_len // len(pattern) + 1
                        data = (pattern * repeats)[:write_len]
                    f.write(data)
                    written += write_len
                force_flush(f)
        return True
    except Exception:
        return False

def wipe_process(file_path, method="random"):
    # 0. SYMLINK CHECK (Critical Safety)
    if os.path.islink(file_path):
        try:
            os.unlink(file_path) # Just unlink, don't follow!
            return True
        except:
            return False

    if not os.path.isfile(file_path): return False
    
    try:
        nuke_attributes(file_path)
        force_block_allocation(file_path)

        if not aes_encrypt_file(file_path):
            return False 
        
        if not secure_overwrite(file_path, method):
            return False
        
        # Rename Loop (Collision Free)
        dir_name = os.path.dirname(file_path)
        temp_name = file_path
        
        for _ in range(3): 
            new_name = os.path.join(dir_name, "wipe_" + uuid.uuid4().hex[:12])
            renamed = False
            for attempt in range(3):
                try:
                    os.rename(temp_name, new_name)
                    temp_name = new_name
                    renamed = True
                    break
                except OSError:
                    time.sleep(0.1)
            
            if not renamed: break
        
        try: os.utime(temp_name, (315532800, 315532800)) 
        except: pass

        with open(temp_name, "w") as f:
            f.truncate(0)
        os.remove(temp_name)
        
        return True
    except Exception:
        return False

def secure_delete_directory(dir_path, method="random"):
    success_count = 0
    # 1. Wipe all files
    for root, dirs, files in os.walk(dir_path, topdown=False):
        for name in files:
            if wipe_process(os.path.join(root, name), method):
                success_count += 1
        
        # 2. Rename directories
        for name in dirs:
            try: 
                dpath = os.path.join(root, name)
                new_dname = os.path.join(root, "rm_" + uuid.uuid4().hex[:8])
                os.rename(dpath, new_dname)
            except: pass
    
    # 3. Nuke structure
    try:
        shutil.rmtree(dir_path, ignore_errors=True)
    except: 
        pass
        
    return success_count

# ==========================================
# WORKER & GUI
# ==========================================
class WipeWorker(QtCore.QObject):
    progress_signal = QtCore.pyqtSignal(int)
    status_signal = QtCore.pyqtSignal(str)
    finished_signal = QtCore.pyqtSignal()
    snapshot_fail_signal = QtCore.pyqtSignal() # New signal for partial security

    def __init__(self, items, method):
        super().__init__()
        self.items = items
        self.method = method

    def run(self):
        elevate_priority()
        
        self.status_signal.emit("Initializing & Checking Privileges...")
        vss_status, vss_msg = kill_snapshots()
        
        if not vss_status:
             self.status_signal.emit(f"⚠️ VSS/Snapshot: {vss_msg}")
             self.snapshot_fail_signal.emit() # Trigger warning
             time.sleep(1.5)
        else:
             self.status_signal.emit(f"✔ VSS/Snapshot: {vss_msg}")

        total = len(self.items)
        if total == 0:
            self.finished_signal.emit()
            return

        for idx, item in enumerate(self.items, 1):
            if os.path.isfile(item) or os.path.islink(item):
                self.status_signal.emit(f"Scrubbing: {os.path.basename(item)}")
                success = wipe_process(item, method=self.method)
                if not success:
                    self.status_signal.emit(f"-> FAILED (Access Denied)")
            elif os.path.isdir(item):
                self.status_signal.emit(f"Dir Tree: {os.path.basename(item)}")
                secure_delete_directory(item, method=self.method)
            
            self.progress_signal.emit(int(idx / total * 100))
        
        self.finished_signal.emit()

class WipeWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"ARYWIPE - {get_platform()} Ultimate")
        self.resize(800, 780)
        self.setStyleSheet("""
            QWidget { 
                background-color: #050505; 
                color: #00FF00; 
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace; 
                font-size: 12px; 
            }
            QListWidget { background-color: #0F0F0F; border: 1px solid #333; color: #EEE; }
            QComboBox { background-color: #111; border: 1px solid #00FF00; padding: 5px; color: #00FF00; }
            QProgressBar { border: 1px solid #00FF00; text-align: center; color: #000; }
            QProgressBar::chunk { background-color: #00FF00; }
            QLabel { font-weight: bold; }
        """)
        self.layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.layout)

        try:
            banner_text = pyfiglet.figlet_format("ARYWIPE", font="slant")
        except:
            banner_text = "ARYWIPE"
            
        self.banner = QtWidgets.QLabel(banner_text)
        self.banner.setAlignment(QtCore.Qt.AlignCenter)
        self.banner.setStyleSheet("font-size: 14px; color: #00FF00; margin-bottom: 5px; white-space: pre;")
        self.layout.addWidget(self.banner)
        
        self.sub_banner = QtWidgets.QLabel(f"ULTIMATE EDITION | {get_platform().upper()}")
        self.sub_banner.setAlignment(QtCore.Qt.AlignCenter)
        self.sub_banner.setStyleSheet("color: #FF0000; margin-bottom: 5px; letter-spacing: 1px;")
        self.layout.addWidget(self.sub_banner)

        # WARNING PANEL
        self.warn_panel = QtWidgets.QLabel(
            "⚠️ FORENSIC LIMITATIONS:\n"
            "1. SSD Wear-Leveling may retain data fragments.\n"
            "2. Filesystem Journals (NTFS/EXT4) may keep metadata.\n"
            "For Top Secret data, use Full Disk Encryption + ARYWIPE."
        )
        self.warn_panel.setAlignment(QtCore.Qt.AlignCenter)
        self.warn_panel.setStyleSheet("color: #FFA500; font-size: 11px; border: 1px solid #FFA500; padding: 8px; margin: 10px; background-color: #111;")
        self.layout.addWidget(self.warn_panel)

        self.file_list = QtWidgets.QListWidget()
        self.layout.addWidget(self.file_list)

        grid = QtWidgets.QGridLayout()
        self.btn_add_file = QtWidgets.QPushButton("Add File")
        self.btn_add_file.setStyleSheet(self.btn_style_normal())
        self.btn_add_file.clicked.connect(self.add_files)
        
        self.btn_add_dir = QtWidgets.QPushButton("Add Folder")
        self.btn_add_dir.setStyleSheet(self.btn_style_normal())
        self.btn_add_dir.clicked.connect(self.add_directory)

        grid.addWidget(self.btn_add_file, 0, 0)
        grid.addWidget(self.btn_add_dir, 0, 1)
        self.layout.addLayout(grid)

        self.layout.addWidget(QtWidgets.QLabel("ALGORITHM:"))
        self.method_combo = QtWidgets.QComboBox()
        self.method_combo.addItems([
            "paranoid (Schneier 7-Pass + AES)",
            "legacy (Gutmann 35-Pass - Outdated for SSDs)",
            "random (3-Pass + AES - Standard)"
        ])
        self.layout.addWidget(self.method_combo)

        self.progress_bar = QtWidgets.QProgressBar()
        self.layout.addWidget(self.progress_bar)

        self.btn_wipe = QtWidgets.QPushButton("INITIATE DESTRUCTION")
        self.btn_wipe.setStyleSheet(self.btn_style_nuke())
        self.btn_wipe.clicked.connect(self.wipe_selected)
        self.layout.addWidget(self.btn_wipe)

        self.status_list = QtWidgets.QListWidget()
        self.layout.addWidget(self.status_list)

        self.footer = QtWidgets.QLabel("Made By Aryan Giri")
        self.footer.setAlignment(QtCore.Qt.AlignCenter)
        self.footer.setStyleSheet("color: #555; font-size: 11px; margin-top: 15px; border-top: 1px solid #222; padding-top: 5px;")
        self.layout.addWidget(self.footer)

    def btn_style_normal(self):
        return "QPushButton { background-color: #111; color: #CCC; border: 1px solid #444; padding: 12px; } QPushButton:hover { background-color: #222; }"

    def btn_style_nuke(self):
        return "QPushButton { background-color: #000; color: #FF0000; border: 2px solid #FF0000; padding: 18px; font-size: 13px; font-weight: bold; } QPushButton:hover { background-color: #220000; }"

    def set_partial_security_warning(self):
        """Visual alert if snapshots fail"""
        self.sub_banner.setText("⚠️ PARTIAL SECURITY: ADMIN RIGHTS MISSING ⚠️")
        self.sub_banner.setStyleSheet("color: #FF00FF; font-weight: bold; font-size: 12px; background-color: #220022; padding: 5px;")

    def add_files(self):
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(self, "Select Files")
        safe_files = []
        for f in files:
            if is_critical_path(f):
                QtWidgets.QMessageBox.critical(self, "Safety Lock", f"Cannot wipe system path: {f}")
            else:
                safe_files.append(f)
        self.file_list.addItems(safe_files)

    def add_directory(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Directory")
        if path:
            if is_critical_path(path):
                QtWidgets.QMessageBox.critical(self, "Safety Lock", f"Cannot wipe system directory: {path}")
            else:
                self.file_list.addItem(path)

    def wipe_selected(self):
        items = [self.file_list.item(i).text() for i in range(self.file_list.count())]
        if not items: return

        reply = QtWidgets.QMessageBox.question(self, 'FINAL WARNING', 
            "DATA WILL BE UNRECOVERABLE.\n\nAlgorithm: " + self.method_combo.currentText() + "\n\nProceed?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)

        if reply == QtWidgets.QMessageBox.Yes:
            method = self.method_combo.currentText().split(" ")[0]
            self.status_list.clear()
            self.progress_bar.setValue(0)
            # Reset banner safety
            self.sub_banner.setText(f"ULTIMATE EDITION | {get_platform().upper()}")
            self.sub_banner.setStyleSheet("color: #FF0000; margin-bottom: 5px; letter-spacing: 1px;")

            self.thread = QtCore.QThread()
            self.worker = WipeWorker(items, method)
            self.worker.moveToThread(self.thread)
            self.thread.started.connect(self.worker.run)
            self.worker.progress_signal.connect(self.progress_bar.setValue)
            self.worker.status_signal.connect(self.status_list.addItem)
            self.worker.snapshot_fail_signal.connect(self.set_partial_security_warning)
            self.worker.finished_signal.connect(self.thread.quit)
            self.worker.finished_signal.connect(self.worker.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)
            self.thread.finished.connect(lambda: self.file_list.clear())
            self.thread.start()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = WipeWindow()
    window.show()
    sys.exit(app.exec_())
