from PyQt6.QtCore import QAbstractTableModel, Qt, QModelIndex, pyqtSignal
import json

class ReferenceModel(QAbstractTableModel):
    # Emitted whenever the internal data changes (useful for auto-save)
    data_changed_signal = pyqtSignal()
    
    def __init__(self, entries=None):
        super().__init__()
        self.entries = entries if entries is not None else []
        self._undo_stack = []
        self._suspend_snapshot = False
        self._max_authors = self._calculate_max_authors()
        self._headers = self._build_headers()
        self.style_config = {}
        
    def snapshot(self):
        import copy
        self._undo_stack.append(copy.deepcopy(self.entries))
        if len(self._undo_stack) > 50:
            self._undo_stack.pop(0)
            
    def undo(self):
        if self._undo_stack:
            self.layoutAboutToBeChanged.emit()
            self.entries = self._undo_stack.pop()
            self._max_authors = self._calculate_max_authors()
            self._headers = self._build_headers()
            self.layoutChanged.emit()
            self.data_changed_signal.emit()

    def set_style_config(self, config):
        self.style_config = config
        self.layoutChanged.emit()

    def _calculate_max_authors(self):
        if not self.entries:
            return 1
        return max((len(e.get("authors", [])) for e in self.entries), default=1)

    def _build_headers(self):
        headers = ["🗑️", "↕"]
        for i in range(1, self._max_authors + 1):
            headers.extend([f"Author {i} First", f"Author {i} Last"])
        headers.extend([
            "Title", "Journal", "Vol", "Page 1", "Page 2", "Year", "DOI URL"
        ])
        return headers

    def add_entry(self, entry):
        self.snapshot()
        self.layoutAboutToBeChanged.emit()
        self.entries.append(entry)
        
        # Check if we need to expand columns
        new_authors_count = len(entry.get("authors", []))
        if new_authors_count > self._max_authors:
            self._max_authors = new_authors_count
            self._headers = self._build_headers()
            
        self.layoutChanged.emit()
        self.data_changed_signal.emit()

    def remove_entry(self, row):
        if 0 <= row < len(self.entries):
            self.snapshot()
            self.beginRemoveRows(QModelIndex(), row, row)
            self.entries.pop(row)
            self.endRemoveRows()
            
            # Recalculate max authors
            new_max = self._calculate_max_authors()
            if new_max != self._max_authors:
                self.layoutAboutToBeChanged.emit()
                self._max_authors = new_max
                self._headers = self._build_headers()
                self.layoutChanged.emit()
                
            self.data_changed_signal.emit()

    def get_entries(self):
        return self.entries

    def rowCount(self, parent=QModelIndex()):
        return len(self.entries)

    def columnCount(self, parent=QModelIndex()):
        return len(self._headers)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
            
        row = index.row()
        col = index.column()
        entry = self.entries[row]
        
        # Two control columns: 0=Trash, 1=Drag
        # Author cols count is self._max_authors * 2
        
        if role == Qt.ItemDataRole.TextAlignmentRole:
            if col in (0, 1):
                return Qt.AlignmentFlag.AlignCenter
                
        if role == Qt.ItemDataRole.FontRole:
            from PyQt6.QtGui import QFont
            font = QFont()
            if col in (0, 1):
                return font
                
            if 2 <= col < (self._max_authors * 2 + 2):
                font.setItalic(self.style_config.get("italic", {}).get("Author", False))
                font.setBold(self.style_config.get("bold", {}).get("Author", False))
                return font
                
            col_name = self._headers[col]
            base_field = ""
            if col_name == "Title": base_field = "Title"
            elif col_name == "Journal": base_field = "Journal"
            elif col_name == "Vol": base_field = "Vol"
            elif col_name in ("Page 1", "Page 2"): base_field = "Page"
            elif col_name == "Year": base_field = "Year"
            
            if base_field:
                font.setItalic(self.style_config.get("italic", {}).get(base_field, False))
                font.setBold(self.style_config.get("bold", {}).get(base_field, False))
                return font
            return None

        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            if col == 0: return "🗑️" if role == Qt.ItemDataRole.DisplayRole else ""
            if col == 1: return "↕" if role == Qt.ItemDataRole.DisplayRole else ""
            
            if 2 <= col < (self._max_authors * 2 + 2):
                author_idx = (col - 2) // 2
                is_first = ((col - 2) % 2 == 0)
                authors = entry.get("authors", [])
                if author_idx < len(authors):
                    val = authors[author_idx].get("first" if is_first else "last", "")
                    if is_first and self.style_config.get("initials", False) and val:
                        return f"{val[0]}."
                    return val
                return ""
                
            col_name = self._headers[col]
            if col_name == "Title":
                if self.style_config.get("hide_title", False):
                    return ""
                return entry.get("title", "")
            if col_name == "Journal": 
                if self.style_config.get("journal_abbrev", False):
                    sj = entry.get("short_journal", "")
                    return sj if sj else entry.get("journal", "")
                return entry.get("journal", "")
            if col_name == "Vol": return entry.get("vol", "")
            if col_name == "Page 1": return entry.get("page1", "")
            if col_name == "Page 2": return entry.get("page2", "")
            if col_name == "Year": 
                y = entry.get("year", "")
                if y and self.style_config.get("year_parens", False):
                    return f"({y})"
                return y
            if col_name == "DOI URL": return entry.get("doi_url", "")
            
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                if section < len(self._headers):
                    return self._headers[section]
            elif orientation == Qt.Orientation.Vertical:
                return str(section + 1)
        return None

    # --- Editing Support ---
    def flags(self, index):
        default_flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if not index.isValid():
            return Qt.ItemFlag.ItemIsDropEnabled
            
        col = index.column()
        if col == 0:
            return default_flags # Clickable for delete
        elif col == 1:
            return default_flags | Qt.ItemFlag.ItemIsDragEnabled # Drag handle
        else:
            return default_flags | Qt.ItemFlag.ItemIsDropEnabled | Qt.ItemFlag.ItemIsEditable

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if not index.isValid() or role != Qt.ItemDataRole.EditRole:
            return False
            
        row = index.row()
        col = index.column()
        entry = self.entries[row]
        
        val_str = str(value)
        
        if col in (0, 1):
            return False
            
        current_val = self.data(index, Qt.ItemDataRole.EditRole) or ""
        if str(current_val) == val_str:
            return False
            
        if not self._suspend_snapshot:
            self.snapshot()
            
        if 2 <= col < (self._max_authors * 2 + 2):
            author_idx = (col - 2) // 2
            is_first = ((col - 2) % 2 == 0)
            authors = entry.get("authors", [])
            # Pad authors list if needed
            while len(authors) <= author_idx:
                authors.append({"first": "", "last": ""})
            authors[author_idx]["first" if is_first else "last"] = val_str
            entry["authors"] = authors
        else:
            col_name = self._headers[col]
            if col_name == "Title": entry["title"] = val_str
            elif col_name == "Journal": 
                if self.style_config.get("journal_abbrev", False):
                    entry["short_journal"] = val_str
                else:
                    entry["journal"] = val_str
            elif col_name == "Vol": entry["vol"] = val_str
            elif col_name == "Page 1": entry["page1"] = val_str
            elif col_name == "Page 2": entry["page2"] = val_str
            elif col_name == "Year": entry["year"] = val_str
            elif col_name == "DOI URL": entry["doi_url"] = val_str

        self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole])
        self.data_changed_signal.emit()
        return True

    # --- Drag & Drop Reordering Support ---
    def supportedDropActions(self):
        return Qt.DropAction.MoveAction

    def mimeTypes(self):
        return ["application/x-reference-row"]

    def mimeData(self, indexes):
        from PyQt6.QtCore import QMimeData
        mime_data = QMimeData()
        if not indexes:
            return mime_data
        
        # Take the row of the first selected index
        row = str(indexes[0].row()).encode('utf-8')
        mime_data.setData("application/x-reference-row", row)
        return mime_data

    def dropMimeData(self, data, action, row, col, parent):
        if action == Qt.DropAction.IgnoreAction:
            return True
        if not data.hasFormat("application/x-reference-row"):
            return False
            
        source_row = int(data.data("application/x-reference-row").data().decode('utf-8'))
        
        target_row = row
        if target_row == -1:
            if parent.isValid():
                target_row = parent.row()
            else:
                target_row = self.rowCount()
                
        if source_row == target_row or source_row == target_row - 1:
            return False
            
        self.snapshot()
        self.beginMoveRows(QModelIndex(), source_row, source_row, QModelIndex(), target_row)
        
        dest = target_row
        if source_row < target_row:
            dest -= 1
            
        item = self.entries.pop(source_row)
        self.entries.insert(dest, item)
        
        self.endMoveRows()
        self.data_changed_signal.emit()
        
        # Return False to prevent default row removal behavior from QTableView
        return False
