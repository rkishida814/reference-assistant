import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QCheckBox, QComboBox, QGroupBox,
    QFileDialog, QTableView, QHeaderView, QMessageBox, QApplication, QSpinBox
)
from PyQt6.QtGui import QKeySequence, QClipboard, QAction
from PyQt6.QtCore import Qt, QTimer, QEvent
from core.reference_model import ReferenceModel
from core.metadata_fetcher import fetch_metadata
from core.autosave import AutoSaver
from core.exporter import export_to_txt, export_to_docx
from PyQt6.QtGui import QDrag

class ReferenceTableView(QTableView):
    def startDrag(self, supportedActions):
        indexes = self.selectedIndexes()
        if not indexes:
            return
            
        row = indexes[0].row()
        
        # Create a visual pixmap of the entire row
        rect = self.visualRect(self.model().index(row, 0))
        for col in range(1, self.model().columnCount()):
            rect = rect.united(self.visualRect(self.model().index(row, col)))
            
        rect = rect.intersected(self.viewport().rect())
        pixmap = self.viewport().grab(rect)
        
        drag = QDrag(self)
        drag.setPixmap(pixmap)
        
        # Set hotspot relative to the mouse cursor
        from PyQt6.QtGui import QCursor
        hotspot = self.viewport().mapFromGlobal(QCursor.pos()) - rect.topLeft()
        drag.setHotSpot(hotspot)
        
        mime_data = self.model().mimeData(indexes)
        drag.setMimeData(mime_data)
        
        drag.exec(supportedActions)

class EditorScreen(QMainWindow):
    def __init__(self, list_name, save_path, start_screen=None):
        super().__init__()
        self.list_name = list_name
        self.save_path = save_path
        self.start_screen = start_screen
        
        self.setWindowTitle("Reference Editor")
        self.resize(1000, 700)
        
        # Initialize the Reference Model
        self.model = ReferenceModel()
        
        # Setup AutoSaver
        self.auto_saver = AutoSaver(self.model, lambda: self.save_path, self.get_style_config)
        
        self.init_ui()
        self._setup_mac_edit_menu()
        
        # Load existing data OR set defaults
        loaded_config = None
        if os.path.exists(self.save_path) and os.path.getsize(self.save_path) > 0:
            loaded_config = self.auto_saver.load_from_file(self.save_path)
            
        if loaded_config:
            self.apply_style_config(loaded_config)
        else:
            self._apply_default_styles()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # -------------------------------
        # HEADER
        # -------------------------------
        header_layout = QHBoxLayout()
        
        self.btn_back = QPushButton("Back")
        self.btn_back.clicked.connect(self.go_back)
        
        self.line_list_name = QLineEdit(self.list_name)
        self.line_list_name.setPlaceholderText("List Name")
        self.line_list_name.editingFinished.connect(self.on_list_name_changed)
        
        self.lbl_path = QLabel(self.save_path)
        self.btn_change_path = QPushButton("Change Folder")
        self.btn_change_path.clicked.connect(self.change_save_folder)
        
        header_layout.addWidget(self.btn_back)
        header_layout.addSpacing(20)
        header_layout.addWidget(QLabel("List Name:"))
        header_layout.addWidget(self.line_list_name)
        header_layout.addStretch()
        header_layout.addWidget(QLabel("Save to:"))
        header_layout.addWidget(self.lbl_path)
        header_layout.addWidget(self.btn_change_path)
        
        main_layout.addLayout(header_layout)

        # -------------------------------
        # INPUT SECTION
        # -------------------------------
        input_layout = QHBoxLayout()
        self.line_doi_url = QLineEdit()
        self.line_doi_url.setPlaceholderText("Enter or drag & drop URL / DOI here...")
        self.line_doi_url.setMinimumHeight(40)
        
        self.btn_load = QPushButton("Load Metadata")
        self.btn_load.setMinimumHeight(40)
        self.btn_load.clicked.connect(self.load_metadata)
        
        self.btn_append = QPushButton("Append from List")
        self.btn_append.setMinimumHeight(40)
        self.btn_append.clicked.connect(self.append_from_list)
        
        input_layout.addWidget(self.line_doi_url)
        input_layout.addWidget(self.btn_load)
        input_layout.addWidget(self.btn_append)
        
        main_layout.addLayout(input_layout)

        # -------------------------------
        # STYLE SETTINGS PANEL
        # -------------------------------
        style_layout = QVBoxLayout()
        
        # --- General Options Group ---
        gen_group = QGroupBox("General Options")
        gen_layout = QHBoxLayout()
        
        self.chk_initials = QCheckBox("First Name Initials")
        self.chk_hide_title = QCheckBox("Hide Title")
        self.chk_journal_abbrev = QCheckBox("Journal Abbrev")
        self.chk_year_parens = QCheckBox("(Year)")
        self.chk_end_period = QCheckBox("End Period (.)")
        
        gen_layout.addWidget(self.chk_initials)
        gen_layout.addWidget(self.chk_hide_title)
        gen_layout.addWidget(self.chk_journal_abbrev)
        gen_layout.addWidget(self.chk_year_parens)
        gen_layout.addWidget(self.chk_end_period)
        
        gen_layout.addSpacing(20)
        self.combo_doi_export = QComboBox()
        self.combo_doi_export.addItems(["No DOI", "URL (https://doi.org/...)", "DOI Only (doi:...)"])
        gen_layout.addWidget(QLabel("DOI:"))
        gen_layout.addWidget(self.combo_doi_export)
        
        gen_layout.addStretch()
        gen_group.setLayout(gen_layout)
        style_layout.addWidget(gen_group)

        # --- Font Styling Group ---
        font_group = QGroupBox("Font Styling")
        font_layout = QHBoxLayout()
        font_style_fields = ["Author", "Title", "Journal", "Vol", "Page", "Year"]
        
        self.chk_italics = {}
        font_layout.addWidget(QLabel("Italic:"))
        for field in font_style_fields:
            chk = QCheckBox(field)
            self.chk_italics[field] = chk
            font_layout.addWidget(chk)
            
        font_layout.addSpacing(20)
        
        self.chk_bold = {}
        font_layout.addWidget(QLabel("Bold:"))
        for field in font_style_fields:
            chk = QCheckBox(field)
            self.chk_bold[field] = chk
            font_layout.addWidget(chk)
        
        font_layout.addStretch()
        font_group.setLayout(font_layout)
        style_layout.addWidget(font_group)

        # --- Structure & Delimiters Group ---
        struct_group = QGroupBox("Structure & Delimiters")
        struct_layout = QHBoxLayout()
        
        self.combo_ordering = QComboBox()
        self.combo_ordering.addItems([
            "Vol, Page, Year",
            "Year, Vol, Page",
            "Vol, Year, Page",
            "Year, Page, Vol"
        ])
        struct_layout.addWidget(QLabel("Order:"))
        struct_layout.addWidget(self.combo_ordering)
        struct_layout.addSpacing(15)
        
        self.combo_author_fmt = QComboBox()
        self.combo_author_fmt.addItems([
            "First Last (John Smith)",
            "Last, First (Smith, John)"
        ])
        struct_layout.addWidget(QLabel("Author Fmt:"))
        struct_layout.addWidget(self.combo_author_fmt)
        struct_layout.addSpacing(15)
        
        delim_options = [",", ";", ":", ".", " "]
        
        self.delim_label_widgets = {}
        self.delims = {}
        delim_labels = {
            "author_author": "Authors",
            "author_title": "Author-Title",
            "title_journal": "Title-Journal",
            "journal_vol": "Journal-Vol",
            "vol_page": "Vol-Page",
            "page_year": "Page-Year"
        }
        
        for key, text in delim_labels.items():
            lbl = QLabel(text)
            struct_layout.addWidget(lbl)
            self.delim_label_widgets[key] = lbl
            
            cb = QComboBox()
            cb.addItems(delim_options)
            self.delims[key] = cb
            struct_layout.addWidget(cb)
            
        struct_layout.addStretch()
        struct_group.setLayout(struct_layout)
        style_layout.addWidget(struct_group)

        # --- Authors Visibility Group ---
        vis_group = QGroupBox("Authors Visibility")
        vis_layout = QHBoxLayout()
        
        vis_layout.addWidget(QLabel("Hide after (N):"))
        self.spin_hide_author = QSpinBox()
        self.spin_hide_author.setRange(0, 99)
        self.spin_hide_author.setValue(0)
        self.spin_hide_author.setSpecialValueText("Don't Hide")
        vis_layout.addWidget(self.spin_hide_author)
        
        self.btn_hide_author = QPushButton("Apply Hide")
        self.btn_hide_author.clicked.connect(self.apply_author_hide)
        vis_layout.addWidget(self.btn_hide_author)
        
        vis_layout.addSpacing(15)
        self.chk_export_et_al = QCheckBox("Export as 'et al.'")
        self.chk_export_et_al.setChecked(True)
        self.chk_export_et_al.toggled.connect(self.update_preview)
        vis_layout.addWidget(self.chk_export_et_al)
        
        vis_layout.addStretch()
        vis_group.setLayout(vis_layout)
        style_layout.addWidget(vis_group)

        main_layout.addLayout(style_layout)

        # -------------------------------
        # TABLE VIEW
        # -------------------------------
        self.table_view = ReferenceTableView()
        # Allows individual cell selection
        self.table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectItems)
        # Enable editing directly on current cell without selecting whole row
        self.table_view.setSelectionMode(QTableView.SelectionMode.ExtendedSelection)
        # Enable drag and drop reordering
        self.table_view.setDragDropMode(QTableView.DragDropMode.InternalMove)
        # Drop indicator only between rows
        self.table_view.setDropIndicatorShown(True)
        # Only row dragging
        self.table_view.setDragDropOverwriteMode(False)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table_view.setModel(self.model)
        
        # Control column sizing
        self.table_view.horizontalHeader().resizeSection(0, 30)
        self.table_view.horizontalHeader().resizeSection(1, 40)
        
        # Handle Trash Clicks
        self.table_view.clicked.connect(self.on_table_clicked)
        
        # Install event filter for keyboard shortcuts
        self.table_view.installEventFilter(self)
        
        main_layout.addWidget(self.table_view)

        # Connect all style widgets to update preview
        self._connect_style_signals()
        self.combo_ordering.currentTextChanged.connect(self.on_ordering_changed)
        self.on_ordering_changed()  # Initialize labels

        # -------------------------------
        # BOTTOM ACTION ROW
        # -------------------------------
        bottom_layout = QHBoxLayout()
        self.btn_export_txt = QPushButton("Export as TXT")
        self.btn_export_txt.clicked.connect(self.export_txt)
        
        self.btn_export_docx = QPushButton("Export as DOCX")
        self.btn_export_docx.clicked.connect(self.export_docx)
        
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.btn_export_txt)
        bottom_layout.addWidget(self.btn_export_docx)
        
        main_layout.addLayout(bottom_layout)

    def _setup_mac_edit_menu(self):
        menubar = self.menuBar()
        edit_menu = menubar.addMenu("Edit")
        
        act_undo = QAction("Undo", self)
        act_undo.setShortcut(QKeySequence.StandardKey.Undo)
        act_undo.triggered.connect(self._on_undo)
        edit_menu.addAction(act_undo)
        
        act_redo = QAction("Redo", self)
        act_redo.setShortcut(QKeySequence.StandardKey.Redo)
        act_redo.triggered.connect(self._on_redo)
        edit_menu.addAction(act_redo)
        
        edit_menu.addSeparator()
        
        act_cut = QAction("Cut", self)
        act_cut.setShortcut(QKeySequence.StandardKey.Cut)
        act_cut.triggered.connect(self._on_cut)
        edit_menu.addAction(act_cut)
        
        act_copy = QAction("Copy", self)
        act_copy.setShortcut(QKeySequence.StandardKey.Copy)
        act_copy.triggered.connect(self._on_copy)
        edit_menu.addAction(act_copy)
        
        act_paste = QAction("Paste", self)
        act_paste.setShortcut(QKeySequence.StandardKey.Paste)
        act_paste.triggered.connect(self._on_paste)
        edit_menu.addAction(act_paste)
        
        act_all = QAction("Select All", self)
        act_all.setShortcut(QKeySequence.StandardKey.SelectAll)
        act_all.triggered.connect(self._on_select_all)
        edit_menu.addAction(act_all)

    def _on_undo(self):
        focus = QApplication.focusWidget()
        # QTableView editor wrapper is a QWidget but its children have undo.
        # But we only want table-level undo when the table itself is focused or editing.
        # For simplicity, if focus is within table, do model undo. 
        # Actually it's cleaner: if it's the table, do model undo. If it's a line edit, do native undo.
        if focus == self.table_view or self.table_view.isAncestorOf(focus):
            self.model.undo()
        elif hasattr(focus, "undo"):
            focus.undo()

    def _on_redo(self):
        focus = QApplication.focusWidget()
        if hasattr(focus, "redo"):
            focus.redo()

    def _on_cut(self):
        focus = QApplication.focusWidget()
        if focus == self.table_view:
            self.copy_selection() # Just copy for table view, no delete
        elif hasattr(focus, "cut"):
            focus.cut()

    def _on_copy(self):
        focus = QApplication.focusWidget()
        if focus == self.table_view:
            self.copy_selection()
        elif hasattr(focus, "copy"):
            focus.copy()

    def _on_paste(self):
        focus = QApplication.focusWidget()
        if focus == self.table_view:
            self.paste_selection()
        elif hasattr(focus, "paste"):
            focus.paste()

    def _on_select_all(self):
        focus = QApplication.focusWidget()
        if focus == self.table_view:
            self.table_view.selectAll()
        elif hasattr(focus, "selectAll"):
            focus.selectAll()

    def apply_author_hide(self):
        n = self.spin_hide_author.value()
        max_authors = self.model._max_authors
        
        # Column 0: Trash, Column 1: Reorder
        # Author 1 First: 2, Author 1 Last: 3
        # Author i First: 2 + (i-1)*2
        # Author i Last:  3 + (i-1)*2
        
        for i in range(1, max_authors + 1):
            col_first = 2 + (i - 1) * 2
            col_last = col_first + 1
            
            should_hide = (n > 0 and i > n)
            self.table_view.setColumnHidden(col_first, should_hide)
            self.table_view.setColumnHidden(col_last, should_hide)
            
        self.update_preview()

    def apply_style_config(self, config):
        self.chk_initials.setChecked(config.get("initials", False))
        self.chk_hide_title.setChecked(config.get("hide_title", False))
        self.chk_journal_abbrev.setChecked(config.get("journal_abbrev", False))
        self.chk_year_parens.setChecked(config.get("year_parens", False))
        self.chk_end_period.setChecked(config.get("end_period", False))
        
        self.combo_doi_export.setCurrentText(config.get("doi_export", "No DOI"))
        self.combo_ordering.setCurrentText(config.get("ordering", "Vol, Page, Year"))
        self.combo_author_fmt.setCurrentText(config.get("author_format", "First Last (John Smith)"))
        
        self.spin_hide_author.setValue(config.get("hide_author_after", 0))
        self.chk_export_et_al.setChecked(config.get("export_et_al", True))
        self.apply_author_hide()
        
        italics = config.get("italic", {})
        for field, chk in self.chk_italics.items():
            chk.setChecked(italics.get(field, False))
            
        bolds = config.get("bold", {})
        for field, chk in self.chk_bold.items():
            chk.setChecked(bolds.get(field, False))
            
        delims = config.get("delims", {})
        for key, cb in self.delims.items():
            cb.setCurrentText(delims.get(key, ","))

    def _apply_default_styles(self):
        config = {
            "initials": True,
            "hide_title": False,
            "journal_abbrev": True,
            "year_parens": False,
            "end_period": True,
            "doi_export": "DOI Only (doi:...)",
            "ordering": "Vol, Page, Year",
            "author_format": "First Last (John Smith)",
            "hide_author_after": 0,
            "export_et_al": True,
            "italic": {"Journal": True},
            "bold": {},
            "delims": {
                "author_title": ".",
            }
        }
        self.apply_style_config(config)

    def on_table_clicked(self, index):
        if index.column() == 0:
            reply = QMessageBox.question(self, "Delete Row", f"Are you sure you want to delete row {index.row() + 1}?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.model.remove_entry(index.row())

    def go_back(self):
        if self.start_screen:
            self.start_screen.show()
        self.close()

    def on_list_name_changed(self):
        new_name = self.line_list_name.text().strip()
        if not new_name:
            self.line_list_name.setText(self.list_name)
            return
            
        new_path = os.path.join(os.path.dirname(self.save_path), f"{new_name}.txt")
        if os.path.exists(new_path) and new_path != self.save_path:
            QMessageBox.warning(self, "Error", f"A file named {new_name}.txt already exists.")
            self.line_list_name.setText(self.list_name)
        else:
            # Rename the underlying file if it exists, etc.
            self.list_name = new_name
            self.save_path = new_path
            self.lbl_path.setText(self.save_path)
            # Make sure we actually rename the physical file later in autosave logic

    def change_save_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Save Folder")
        if folder:
            self.save_path = os.path.join(folder, f"{self.list_name}.txt")
            self.lbl_path.setText(self.save_path)

    def load_metadata(self):
        input_text = self.line_doi_url.text().strip()
        if not input_text:
            QMessageBox.warning(self, "Input Error", "Please enter a URL or DOI.")
            return
            
        self.btn_load.setEnabled(False)
        self.btn_load.setText("Loading...")
        
        try:
            entry = fetch_metadata(input_text)
            self.model.add_entry(entry)
            self.line_doi_url.clear()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to fetch metadata:\n{e}")
        finally:
            self.btn_load.setEnabled(True)
            self.btn_load.setText("Load Metadata")

    def append_from_list(self):
        options = QFileDialog.Option.DontUseNativeDialog
        default_dir = "/Users/kishida/.gemini/reference_app/list"
        os.makedirs(default_dir, exist_ok=True)
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Append from Reference List", default_dir, "Text Files (*.txt);;All Files (*)", options=options
        )
        if file_path:
            import json
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    entries = json.load(f)
                for entry in entries:
                    self.model.add_entry(entry)
                QMessageBox.information(self, "Success", f"Appended {len(entries)} items.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load entries from file:\n{e}")

    def on_ordering_changed(self):
        ordering = self.combo_ordering.currentText()
        parts = [p.strip() for p in ordering.split(",")]
        
        # Determine exactly the transitions
        # Journal is always before these parts
        labels = []
        labels.append(f"Journal-{parts[0]}")
        labels.append(f"{parts[0]}-{parts[1]}")
        labels.append(f"{parts[1]}-{parts[2]}")
        
        # "Journal-Vol", "Vol-Page", "Page-Year" mapped from the dict keys
        keys_to_update = ["journal_vol", "vol_page", "page_year"]
        
        for k, label_text in zip(keys_to_update, labels):
            if k in self.delim_label_widgets:
                self.delim_label_widgets[k].setText(label_text)

    def eventFilter(self, source, event):
        # We don't need to manually consume these in eventFilter as the QActions handle them
        # However, keeping this acts as a direct fallback if QAction routes fail for any reason.
        if source is self.table_view and event.type() == QEvent.Type.KeyPress:
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier or event.modifiers() & Qt.KeyboardModifier.MetaModifier:
                if event.key() == Qt.Key.Key_C:
                    self.copy_selection()
                    return True
                elif event.key() == Qt.Key.Key_V:
                    self.paste_selection()
                    return True
                elif event.key() == Qt.Key.Key_A:
                    self.table_view.selectAll()
                    return True
                elif event.key() == Qt.Key.Key_Z:
                    self.model.undo()
                    return True
        return super().eventFilter(source, event)

    def copy_selection(self):
        indexes = self.table_view.selectedIndexes()
        if not indexes:
            return
        
        # Sort indexes by row and then column
        indexes = sorted(indexes, key=lambda idx: (idx.row(), idx.column()))
        
        clipboard_text = ""
        current_row = indexes[0].row()
        
        for idx in indexes:
            if idx.row() != current_row:
                clipboard_text += "\n"
                current_row = idx.row()
            else:
                if idx != indexes[0] and clipboard_text and not clipboard_text.endswith("\n"):
                    clipboard_text += "\t"
            
            data = self.model.data(idx, Qt.ItemDataRole.EditRole) or ""
            clipboard_text += str(data)
            
        QApplication.clipboard().setText(clipboard_text)

    def paste_selection(self):
        text = QApplication.clipboard().text()
        if not text:
            return
            
        indexes = self.table_view.selectedIndexes()
        if not indexes:
            return
            
        # Simplistic paste: paste start at the top-left selected index
        indexes = sorted(indexes, key=lambda idx: (idx.row(), idx.column()))
        start_idx = indexes[0]
        start_row = start_idx.row()
        start_col = start_idx.column()
        
        self.model._suspend_snapshot = True
        self.model.snapshot()
        
        rows = text.split("\n")
        for r_offset, row_text in enumerate(rows):
            if not row_text and r_offset == len(rows) - 1:
                continue # ignore trailing newline
            cols = row_text.split("\t")
            for c_offset, col_text in enumerate(cols):
                target_row = start_row + r_offset
                target_col = start_col + c_offset
                
                if target_row < self.model.rowCount() and target_col < self.model.columnCount():
                    # Check if edit enabled
                    idx = self.model.index(target_row, target_col)
                    flags = self.model.flags(idx)
                    if flags & Qt.ItemFlag.ItemIsEditable:
                        self.model.setData(idx, col_text, Qt.ItemDataRole.EditRole)
                        
        self.model._suspend_snapshot = False

    def _connect_style_signals(self):
        # Update preview whenever any style setting changes
        self.chk_initials.toggled.connect(self.update_preview)
        self.chk_hide_title.toggled.connect(self.update_preview)
        self.chk_journal_abbrev.toggled.connect(self.update_preview)
        self.chk_year_parens.toggled.connect(self.update_preview)
        
        self.combo_ordering.currentIndexChanged.connect(self.update_preview)
        self.combo_author_fmt.currentIndexChanged.connect(self.update_preview)
        
        for chk in self.chk_italics.values():
            chk.toggled.connect(self.update_preview)
            
        for chk in self.chk_bold.values():
            chk.toggled.connect(self.update_preview)
            
        for cb in self.delims.values():
            cb.currentIndexChanged.connect(self.update_preview)

    def update_preview(self):
        self.model.set_style_config(self.get_style_config())

    def get_style_config(self):
        config = {
            "initials": self.chk_initials.isChecked(),
            "hide_title": self.chk_hide_title.isChecked(),
            "journal_abbrev": self.chk_journal_abbrev.isChecked(),
            "year_parens": self.chk_year_parens.isChecked(),
            "end_period": self.chk_end_period.isChecked(),
            "doi_export": self.combo_doi_export.currentText(),
            "ordering": self.combo_ordering.currentText(),
            "author_format": self.combo_author_fmt.currentText(),
            "hide_author_after": self.spin_hide_author.value(),
            "export_et_al": self.chk_export_et_al.isChecked(),
            "italic": {field: chk.isChecked() for field, chk in self.chk_italics.items()},
            "bold": {field: chk.isChecked() for field, chk in self.chk_bold.items()},
            "delims": {key: cb.currentText() for key, cb in self.delims.items()}
        }
        return config

    def export_txt(self):
        default_name = f"{self.list_name}.txt"
        default_dir = os.path.expanduser("~/Documents")
        default_path = os.path.join(default_dir, default_name)
        options = QFileDialog.Option.DontUseNativeDialog
        file_path, _ = QFileDialog.getSaveFileName(self, "Export TXT", default_path, "Text Files (*.txt)", options=options)
        if file_path:
            config = self.get_style_config()
            try:
                export_to_txt(self.model.get_entries(), config, file_path)
                QMessageBox.information(self, "Success", f"Exported to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export TXT:\n{e}")

    def export_docx(self):
        default_name = f"{self.list_name}.docx"
        default_dir = os.path.expanduser("~/Documents")
        default_path = os.path.join(default_dir, default_name)
        options = QFileDialog.Option.DontUseNativeDialog
        file_path, _ = QFileDialog.getSaveFileName(self, "Export DOCX", default_path, "Word Documents (*.docx)", options=options)
        if file_path:
            config = self.get_style_config()
            try:
                export_to_docx(self.model.get_entries(), config, file_path)
                QMessageBox.information(self, "Success", f"Exported to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export DOCX:\n{e}")
