import pytest
import sys
import os
from PyQt6.QtWidgets import QApplication

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.reference_model import ReferenceModel
from PyQt6.QtCore import Qt

# Need a Qt Application to instantiate QAbstractTableModel without errors in some PyQt versions
app = QApplication.instance() or QApplication(sys.argv)

def test_reference_model_add_remove():
    model = ReferenceModel()
    assert model.rowCount() == 0
    assert model._max_authors == 1
    
    # Add entry 1
    model.add_entry({
        "authors": [{"first": "A", "last": "B"}],
        "title": "Title 1"
    })
    
    assert model.rowCount() == 1
    assert model._max_authors == 1
    
    # Add entry 2 with 3 authors
    model.add_entry({
        "authors": [
            {"first": "A", "last": "B"},
            {"first": "C", "last": "D"},
            {"first": "E", "last": "F"}
        ],
        "title": "Title 2"
    })
    
    assert model.rowCount() == 2
    assert model._max_authors == 3
    # Columns: 2 (Trash, Drag) + 3 authors * 2 (First, Last) + 7 static = 15
    assert model.columnCount() == 15
    
    # Remove the entry with 3 authors
    model.remove_entry(1)
    
    assert model.rowCount() == 1
    assert model._max_authors == 1
    assert model.columnCount() == 11  # 2 + 1 author * 2 + 7

def test_reference_model_display_role():
    model = ReferenceModel()
    model.add_entry({
        "authors": [{"first": "John", "last": "Smith"}],
        "title": "A Great Paper",
        "year": "2023"
    })
    
    # Title index: for max_authors=1, Title is at col 4 (0=Trash, 1=Drag, 2=A1F, 3=A1L, 4=Title, ...)
    title_idx = model.index(0, 4)
    assert model.data(title_idx, role=Qt.ItemDataRole.DisplayRole) == "A Great Paper"
    
    # Author index
    auth_first_idx = model.index(0, 2)
    assert model.data(auth_first_idx, role=Qt.ItemDataRole.DisplayRole) == "John"
    
def test_reference_model_styles():
    model = ReferenceModel()
    model.add_entry({
        "authors": [{"first": "John", "last": "Smith"}],
        "title": "A Great Paper",
        "year": "2023"
    })
    
    # Apply initials style
    model.set_style_config({"initials": True})
    auth_first_idx = model.index(0, 2)
    assert model.data(auth_first_idx, role=Qt.ItemDataRole.DisplayRole) == "J."
    
    # Apply hide title style
    model.set_style_config({"hide_title": True})
    title_idx = model.index(0, 4)
    assert model.data(title_idx, role=Qt.ItemDataRole.DisplayRole) == ""
