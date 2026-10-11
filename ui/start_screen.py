import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog, QHBoxLayout,
    QMainWindow
)
from PyQt6.QtCore import Qt
from ui.editor_screen import EditorScreen

class StartScreen(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Reference List Creation Assistant")
        self.resize(600, 400)
        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        title_label = QLabel("Reference List Creation Assistant")
        font = title_label.font()
        font.setPointSize(20)
        font.setBold(True)
        title_label.setFont(font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.new_btn = QPushButton("New List")
        self.new_btn.setMinimumHeight(50)
        self.new_btn.clicked.connect(self.create_new_list)
        
        self.load_btn = QPushButton("Load Existing List")
        self.load_btn.setMinimumHeight(50)
        self.load_btn.clicked.connect(self.load_existing_list)
        
        layout.addWidget(title_label)
        layout.addSpacing(30)
        layout.addWidget(self.new_btn)
        layout.addWidget(self.load_btn)
        
        central_widget.setLayout(layout)

    def create_new_list(self):
        default_dir = "/Users/kishida/.gemini/reference_app/list"
        os.makedirs(default_dir, exist_ok=True)
        self.open_editor(list_name="Untitled_List", save_path=os.path.join(default_dir, "Untitled_List.txt"))

    def load_existing_list(self):
        options = QFileDialog.Option.DontUseNativeDialog
        default_dir = "/Users/kishida/.gemini/reference_app/list"
        os.makedirs(default_dir, exist_ok=True)
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Reference List", default_dir, "Text Files (*.txt);;All Files (*)", options=options
        )
        if file_path:
            list_name = os.path.splitext(os.path.basename(file_path))[0]
            self.open_editor(list_name=list_name, save_path=file_path)

    def open_editor(self, list_name, save_path):
        self.editor_screen = EditorScreen(list_name, save_path, start_screen=self)
        self.editor_screen.show()
        self.hide()
