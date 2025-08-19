import os
import random
import string
import sys
from PyQt5 import QtWidgets, QtGui, QtCore

# ===== Secure Delete Logic =====
def overwrite_and_delete(file_path, passes=3):
    if not os.path.isfile(file_path):
        return False
    try:
        length = os.path.getsize(file_path)
        with open(file_path, "r+b", buffering=0) as f:
            for _ in range(passes):
                f.seek(0)
                f.write(os.urandom(length))
                f.flush()
                os.fsync(f.fileno())
        dir_name = os.path.dirname(file_path)
        temp_name = file_path
        for _ in range(3):
            new_name = os.path.join(
                dir_name, ''.join(random.choices(string.ascii_letters + string.digits, k=12))
            )
            os.rename(temp_name, new_name)
            temp_name = new_name
        os.remove(temp_name)
        return True
    except Exception as e:
        print(f"[-] Error wiping {file_path}: {e}")
        return False

def secure_delete_directory(dir_path, passes=3):
    success_count = 0
    for root, dirs, files in os.walk(dir_path, topdown=False):
        for name in files:
            if overwrite_and_delete(os.path.join(root, name), passes):
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

# ===== GUI Application =====
class WipeWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ARYWIPE - Hardcore File & Device Wiper")

        # Allow resizing instead of fixed size
        self.resize(700, 500)
        self.setMinimumSize(500, 400)

        self.setStyleSheet("background-color: #121212; color: #FFFFFF; font-family: Consolas; font-size: 14px;")
        self.layout = QtWidgets.QVBoxLayout()

        # ===== App Banner =====
        self.banner = QtWidgets.QLabel("⛓️ ARYWIPE ⛓️\n🔥 Select files, directories, or mounted devices to securely wipe:")
        self.banner.setAlignment(QtCore.Qt.AlignCenter)
        self.banner.setWordWrap(True)
        self.banner.setStyleSheet("font-size: 20px; color: #00FF88; font-weight: bold;")
        self.layout.addWidget(self.banner)

        # ===== File List =====
        self.file_list = QtWidgets.QListWidget()
        self.file_list.setStyleSheet("background-color: #1E1E1E; border: 1px solid #00FF88;")
        self.layout.addWidget(self.file_list)

        # ===== Buttons Layout =====
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

        # ===== Wipe Button =====
        self.btn_wipe = QtWidgets.QPushButton("🔒 Wipe Selected")
        self.btn_wipe.setStyleSheet(self.button_style())
        self.btn_wipe.clicked.connect(self.wipe_selected)
        self.layout.addWidget(self.btn_wipe)

        # ===== Status Label =====
        self.status = QtWidgets.QLabel("")
        self.status.setAlignment(QtCore.Qt.AlignCenter)
        self.status.setStyleSheet("color: #FF5555; font-size: 13px;")
        self.layout.addWidget(self.status)

        self.setLayout(self.layout)

    def button_style(self):
        return ("QPushButton { background-color: #00FF88; color: #000000; border-radius: 10px; padding: 10px; font-weight: bold; }"
                "QPushButton:hover { background-color: #00CC66; }")

    def add_files(self):
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(self, "Select Files to Wipe")
        for f in files:
            self.file_list.addItem(f)

    def add_directory(self):
        dir_path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Directory to Wipe")
        if dir_path:
            self.file_list.addItem(dir_path)

    def add_device(self):
        # Let user choose a mounted path like /media/username/pendrive (Linux) or drive letter on Windows
        device_path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Mounted Device Path")
        if device_path:
            self.file_list.addItem(device_path)

    def wipe_selected(self):
        items = [self.file_list.item(i).text() for i in range(self.file_list.count())]
        if not items:
            self.status.setText("No files, directories, or devices selected.")
            return
        count = 0
        for item in items:
            if os.path.isfile(item):
                if overwrite_and_delete(item):
                    count += 1
            elif os.path.isdir(item):
                count += secure_delete_directory(item)
        self.status.setText(f"🚀 Wiped {count} item(s) securely!")
        self.file_list.clear()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon.fromTheme("edit-delete"))
    window = WipeWindow()
    window.show()
    sys.exit(app.exec_())
