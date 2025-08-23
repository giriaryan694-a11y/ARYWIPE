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
import webbrowser
import threading
from PyQt5 import QtWidgets, QtGui, QtCore
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

# ===== Secure Delete Logic =====
def aes_encrypt_file(file_path):
    try:
        length = os.path.getsize(file_path)
        key = os.urandom(32)
        iv = os.urandom(16)
        cipher = Cipher(algorithms.AES(key), modes.CFB(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        with open(file_path, "r+b") as f:
            data = f.read()
            f.seek(0)
            f.write(encryptor.update(data) + encryptor.finalize())
            f.flush()
            os.fsync(f.fileno())
        return True
    except Exception as e:
        print(f"[-] AES encryption failed: {e}")
        return False

def secure_overwrite(file_path, passes=3):
    try:
        length = os.path.getsize(file_path)
        for _ in range(passes):
            with open(file_path, "r+b") as f:
                data = os.urandom(length)
                f.seek(0)
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
        return True
    except Exception as e:
        print(f"[-] Overwrite failed: {e}")
        return False

def overwrite_and_delete(file_path, passes=3, method="random", aes=False):
    if not os.path.isfile(file_path):
        return False
    try:
        if aes:
            aes_encrypt_file(file_path)
        if method == "random":
            secure_overwrite(file_path, passes)
        elif method == "dod":
            length = os.path.getsize(file_path)
            patterns = [b'\xFF', b'\x00']
            with open(file_path, "r+b") as f:
                for p in patterns:
                    f.seek(0)
                    f.write(p * length)
                    f.flush()
                    os.fsync(f.fileno())
                f.seek(0)
                f.write(os.urandom(length))
                f.flush()
                os.fsync(f.fileno())
        elif method == "gutmann":
            length = os.path.getsize(file_path)
            gutmann_patterns = [b'\x55', b'\xAA', b'\x92', b'\x49', b'\x24'] * 7
            with open(file_path, "r+b") as f:
                for p in gutmann_patterns:
                    f.seek(0)
                    f.write(p * length)
                    f.flush()
                    os.fsync(f.fileno())
        # Random rename before deletion
        dir_name = os.path.dirname(file_path)
        temp_name = file_path
        for _ in range(3):
            new_name = os.path.join(dir_name, ''.join(random.choices(string.ascii_letters + string.digits, k=12)))
            os.rename(temp_name, new_name)
            temp_name = new_name
        os.remove(temp_name)
        return True
    except Exception as e:
        print(f"[-] Error wiping {file_path}: {e}")
        return False

def secure_delete_directory(dir_path, passes=3, method="random", aes=False):
    success_count = 0
    for root, dirs, files in os.walk(dir_path, topdown=False):
        for name in files:
            if overwrite_and_delete(os.path.join(root, name), passes, method, aes):
                success_count += 1
        for name in dirs:
            try:
                os.rmdir(os.path.join(root, name))
            except Exception as e:
                print(f"[-] Error removing dir {name}: {e}")
    try:
        os.rmdir(dir_path)
    except Exception as e:
        print(f"[-] Error removing {dir_path}: {e}")
    return success_count

# ===== Worker for threading =====
class WipeWorker(QtCore.QObject):
    progress_signal = QtCore.pyqtSignal(int)
    status_signal = QtCore.pyqtSignal(str)
    finished_signal = QtCore.pyqtSignal()

    def __init__(self, items, method, aes):
        super().__init__()
        self.items = items
        self.method = method
        self.aes = aes

    def run(self):
        total = len(self.items)
        for idx, item in enumerate(self.items, 1):
            status_text = f"{item} - "
            if os.path.isfile(item):
                success = overwrite_and_delete(item, method=self.method, aes=self.aes)
            elif os.path.isdir(item):
                success = secure_delete_directory(item, method=self.method, aes=self.aes) > 0
            else:
                success = False
            self.status_signal.emit(status_text + ("Deleted" if success else "Failed"))
            self.progress_signal.emit(int(idx / total * 100))
        self.finished_signal.emit()

# ===== GUI Application =====
class WipeWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ARYWIPE - Hardcore File & Device Wiper")
        self.resize(700, 650)
        self.setStyleSheet("background-color: #121212; color: #FFFFFF; font-family: Consolas; font-size: 14px;")
        self.layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.layout)

        # Banner
        self.banner = QtWidgets.QLabel("⛓️ ARYWIPE ⛓️\n🔥 Select files, directories, or mounted devices to securely wipe:")
        self.banner.setAlignment(QtCore.Qt.AlignCenter)
        self.banner.setWordWrap(True)
        self.banner.setStyleSheet("font-size: 20px; color: #00FF88; font-weight: bold;")
        self.layout.addWidget(self.banner)

        # File list
        self.file_list = QtWidgets.QListWidget()
        self.file_list.setStyleSheet("background-color: #1E1E1E; border: 1px solid #00FF88;")
        self.layout.addWidget(self.file_list)

        # Buttons
        btn_layout = QtWidgets.QHBoxLayout()
        self.btn_add_file = QtWidgets.QPushButton("Add Files")
        self.btn_add_file.setStyleSheet(self.button_style())
        self.btn_add_file.clicked.connect(self.add_files)
        btn_layout.addWidget(self.btn_add_file)

        self.btn_add_dir = QtWidgets.QPushButton("Add Directory")
        self.btn_add_dir.setStyleSheet(self.button_style())
        self.btn_add_dir.clicked.connect(self.add_directory)
        btn_layout.addWidget(self.btn_add_dir)

        self.btn_add_device = QtWidgets.QPushButton("Select Device")
        self.btn_add_device.setStyleSheet(self.button_style())
        self.btn_add_device.clicked.connect(self.add_device)
        btn_layout.addWidget(self.btn_add_device)
        self.layout.addLayout(btn_layout)

        # Method selection
        self.layout.addWidget(QtWidgets.QLabel("Select Wipe Method:"))
        self.method_combo = QtWidgets.QComboBox()
        self.method_combo.addItems(["random", "dod", "gutmann"])
        self.method_combo.setStyleSheet("background-color: #1E1E1E; color: #00FF88;")
        self.layout.addWidget(self.method_combo)

        # AES checkbox
        self.aes_checkbox = QtWidgets.QCheckBox("Use AES Pre-Encryption for extra security")
        self.aes_checkbox.setStyleSheet("color: #00FF88;")
        self.layout.addWidget(self.aes_checkbox)

        # Progress bar
        self.progress_bar = QtWidgets.QProgressBar()
        self.layout.addWidget(self.progress_bar)

        # Wipe button
        self.btn_wipe = QtWidgets.QPushButton("🔒 Wipe Selected")
        self.btn_wipe.setStyleSheet(self.button_style())
        self.btn_wipe.clicked.connect(self.wipe_selected)
        self.layout.addWidget(self.btn_wipe)

        # Status list
        self.status_list = QtWidgets.QListWidget()
        self.status_list.setStyleSheet("background-color: #1E1E1E; color: #00FF88; border: 1px solid #00FF88;")
        self.layout.addWidget(self.status_list)

        # Footer
        footer_layout = QtWidgets.QHBoxLayout()
        self.made_by = QtWidgets.QLabel("Made by Aryan Giri")
        self.made_by.setStyleSheet("color: #00FF88; font-weight: bold;")
        footer_layout.addWidget(self.made_by)
        self.btn_github = QtWidgets.QPushButton("GitHub Repo")
        self.btn_github.setStyleSheet(self.button_style())
        self.btn_github.clicked.connect(lambda: webbrowser.open("https://github.com/giriaryan694-a11y/ARYWIPE"))
        footer_layout.addWidget(self.btn_github)
        self.layout.addLayout(footer_layout)

    def button_style(self):
        return ("QPushButton { background-color: #00FF88; color: #000000; border-radius: 10px; padding: 10px; font-weight: bold; }"
                "QPushButton:hover { background-color: #00CC66; }")

    def add_files(self):
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(self, "Select Files to Wipe")
        self.file_list.addItems(files)

    def add_directory(self):
        dir_path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Directory to Wipe")
        if dir_path:
            self.file_list.addItem(dir_path)

    def add_device(self):
        device_path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Mounted Device Path")
        if device_path:
            self.file_list.addItem(device_path)

    def wipe_selected(self):
        items = [self.file_list.item(i).text() for i in range(self.file_list.count())]
        if not items:
            return
        method = self.method_combo.currentText()
        aes = self.aes_checkbox.isChecked()

        # Clear status and progress
        self.status_list.clear()
        self.progress_bar.setValue(0)

        # Setup worker in a thread
        self.thread = QtCore.QThread()
        self.worker = WipeWorker(items, method, aes)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress_signal.connect(self.progress_bar.setValue)
        self.worker.status_signal.connect(self.status_list.addItem)
        self.worker.finished_signal.connect(self.thread.quit)
        self.worker.finished_signal.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()
        self.file_list.clear()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = WipeWindow()
    window.show()
    sys.exit(app.exec_())
