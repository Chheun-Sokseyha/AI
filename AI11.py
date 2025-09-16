import sys
import sqlite3
import json
import re
import math
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from typing import List, Dict, Tuple, Optional
import pickle
import os
import threading
import time
import csv
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QLineEdit,
    QPushButton, QTextEdit, QTableView, QMessageBox, QTabWidget, QGroupBox,
    QFormLayout, QComboBox, QHeaderView, QFrame, QScrollArea, QSplitter,
    QAbstractItemView, QDialog, QDialogButtonBox, QTextBrowser, QCheckBox, QFileDialog,
    QStyle, QSizePolicy, QMenuBar, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QAbstractTableModel, QModelIndex, QVariant, QThread
from PyQt6.QtGui import QFont, QFontDatabase, QAction, QIcon, QPixmap, QPainter, QPen, QColor, QBrush, QLinearGradient, QRadialGradient

# Try to import speech recognition
try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False
    print("Speech recognition not available. pip install SpeechRecognition pyaudio")

# High-quality custom icon for the dictionary
class DictionaryIcon(QIcon):
    """Custom high-quality dictionary icon with book and Khmer/English text"""
    def __init__(self):
        super().__init__()
        self.create_icon()
    
    def create_icon(self):
        # Create a high-quality dictionary icon
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw book shape with gradient
        book_gradient = QLinearGradient(10, 10, 54, 54)
        book_gradient.setColorAt(0, QColor(30, 60, 120))  # Dark blue
        book_gradient.setColorAt(1, QColor(60, 100, 180))  # Lighter blue
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(book_gradient))
        painter.drawRoundedRect(10, 10, 44, 54, 5, 5)
        
        # Draw book spine
        spine_gradient = QLinearGradient(10, 10, 20, 64)
        spine_gradient.setColorAt(0, QColor(20, 40, 80))
        spine_gradient.setColorAt(1, QColor(40, 70, 140))
        painter.setBrush(QBrush(spine_gradient))
        painter.drawRoundedRect(10, 10, 10, 54, 5, 5)
        
        # Draw pages
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        painter.setBrush(Qt.GlobalColor.white)
        painter.drawRect(15, 15, 34, 44)
        
        # Draw text lines on pages
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        for y in range(20, 55, 6):
            painter.drawLine(18, y, 46, y)
        
        # Draw "EN" and "KH" text
        painter.setPen(QPen(QColor(30, 60, 120), 1))
        font = QFont("Arial", 10, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(18, 25, "EN")
        painter.drawText(35, 25, "KH")
        
        # Draw small decorative elements
        painter.setPen(QPen(QColor(255, 215, 0), 2))  # Gold color
        painter.drawPoint(27, 40)
        painter.drawPoint(32, 40)
        painter.drawPoint(37, 40)
        
        painter.end()
        self.addPixmap(pixmap)

# Icon helper function
def get_icon(name):
    """Get icon from Qt standard icons or create a simple one"""
    # Use our custom dictionary icon for the main app
    if name == "app":
        return DictionaryIcon()
    
    # Use only valid StandardPixmap values for PyQt6
    standard_icons = {
        "search": QStyle.StandardPixmap.SP_FileDialogContentsView,
        "voice": QStyle.StandardPixmap.SP_MediaVolume,
        "clear": QStyle.StandardPixmap.SP_DialogResetButton,
        "random": QStyle.StandardPixmap.SP_BrowserReload,
        "similar": QStyle.StandardPixmap.SP_FileDialogDetailedView,
        "add": QStyle.StandardPixmap.SP_DialogApplyButton,
        "edit": QStyle.StandardPixmap.SP_FileIcon,
        "delete": QStyle.StandardPixmap.SP_TrashIcon,
        "view": QStyle.StandardPixmap.SP_FileDialogInfoView,
        "refresh": QStyle.StandardPixmap.SP_BrowserReload,
        "export": QStyle.StandardPixmap.SP_DialogSaveButton,
        "reset": QStyle.StandardPixmap.SP_DialogResetButton,
        "cancel": QStyle.StandardPixmap.SP_DialogCancelButton,
        "update": QStyle.StandardPixmap.SP_DialogApplyButton,
        "ai": QStyle.StandardPixmap.SP_MessageBoxInformation,
        "close": QStyle.StandardPixmap.SP_DialogCloseButton,
        "theme": QStyle.StandardPixmap.SP_DesktopIcon,
        "dark": QStyle.StandardPixmap.SP_TitleBarMaxButton,
        "light": QStyle.StandardPixmap.SP_TitleBarNormalButton
    }
    
    if name in standard_icons:
        return QApplication.style().standardIcon(standard_icons[name])
    
    # Create a simple colored icon as fallback
    pixmap = QPixmap(24, 24)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    
    colors = {
        "search": Qt.GlobalColor.blue,
        "voice": Qt.GlobalColor.green,
        "clear": Qt.GlobalColor.red,
        "random": Qt.GlobalColor.magenta,
        "similar": Qt.GlobalColor.cyan,
        "add": Qt.GlobalColor.darkGreen,
        "edit": Qt.GlobalColor.darkBlue,
        "delete": Qt.GlobalColor.darkRed,
        "view": Qt.GlobalColor.darkYellow,
        "refresh": Qt.GlobalColor.darkCyan,
        "export": Qt.GlobalColor.darkMagenta,
        "reset": Qt.GlobalColor.gray,
        "cancel": Qt.GlobalColor.darkGray,
        "update": Qt.GlobalColor.yellow,
        "ai": Qt.GlobalColor.lightGray,
        "theme": Qt.GlobalColor.darkYellow,
        "dark": Qt.GlobalColor.black,
        "light": Qt.GlobalColor.white
    }
    
    color = colors.get(name, Qt.GlobalColor.black)
    painter.setPen(color)
    painter.setBrush(color)
    painter.drawRect(4, 4, 16, 16)
    painter.end()
    
    return QIcon(pixmap)

# Export System components
class ExpertDialog(QDialog):
    """Dialog for choosing expert options"""
    
    def __init__(self, font_manager, parent=None):
        super().__init__(parent)
        self.font_manager = font_manager
        self.export_format = "csv"
        self.export_data_type = "Dictionary"
        self.include_analytics = True
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Export Data Options")
        self.setModal(True)
        self.resize(600, 350)
        self.font_manager.apply_font(self)
        
        # Set window icon
        self.setWindowIcon(get_icon("export"))
        
        layout = QVBoxLayout()
        
        # Export format selection
        format_group = QGroupBox("Export Format")
        self.font_manager.apply_font(format_group, bold=True)
        format_layout = QVBoxLayout()
        
        self.format_csv = QCheckBox("CSV (Comma Separated Values)")
        self.format_json = QCheckBox("JSON (JavaScript Object Notation)")
        self.format_txt = QCheckBox("TXT (Plain Text)")
        self.format_html = QCheckBox("HTML (Web Page)")
        
        self.font_manager.apply_font(self.format_csv)
        self.font_manager.apply_font(self.format_json)
        self.font_manager.apply_font(self.format_txt)
        self.font_manager.apply_font(self.format_html)
        
        # Set Default
        self.format_csv.setChecked(True)
        
        format_layout.addWidget(self.format_csv)
        format_layout.addWidget(self.format_json)
        format_layout.addWidget(self.format_txt)
        format_layout.addWidget(self.format_html)
        format_group.setLayout(format_layout)
        
        # Data type selection
        data_group = QGroupBox("Data to Export")
        self.font_manager.apply_font(data_group, bold=True)
        data_layout = QVBoxLayout()
        
        self.data_dictionary = QCheckBox("Dictionary Entries")
        self.data_analytics = QCheckBox("Learning Analytics")
        self.data_profile = QCheckBox("User Profile")
        self.data_history = QCheckBox("Search History")
        
        self.font_manager.apply_font(self.data_dictionary)
        self.font_manager.apply_font(self.data_analytics)
        self.font_manager.apply_font(self.data_profile)
        self.font_manager.apply_font(self.data_history)
        
        # Set Default
        self.data_dictionary.setChecked(True)
        self.data_analytics.setChecked(True)
        
        data_layout.addWidget(self.data_dictionary)
        data_layout.addWidget(self.data_analytics)
        data_layout.addWidget(self.data_profile)
        data_layout.addWidget(self.data_history)
        data_group.setLayout(data_layout)
        
        # Options
        options_group = QGroupBox("Export Options")
        self.font_manager.apply_font(options_group, bold=True)
        options_layout = QVBoxLayout()
        
        self.include_timestamps = QCheckBox("Include Timestamps")
        self.include_metadata = QCheckBox("Include Metadata")
        self.compress_output = QCheckBox("Compress Large Files")
        
        self.font_manager.apply_font(self.include_timestamps)
        self.font_manager.apply_font(self.include_metadata)
        self.font_manager.apply_font(self.compress_output)
        
        self.include_timestamps.setChecked(True)
        self.include_metadata.setChecked(True)
        
        options_layout.addWidget(self.include_timestamps)
        options_layout.addWidget(self.include_metadata)
        options_layout.addWidget(self.compress_output)
        options_group.setLayout(options_layout)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.font_manager.apply_font(button_box)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        layout.addWidget(format_group)
        layout.addWidget(data_group)
        layout.addWidget(options_group)
        layout.addWidget(button_box)
        self.setLayout(layout)
    
    def get_export_settings(self):
        """Get selected export settings"""
        formats = []
        if self.format_csv.isChecked():
            formats.append("csv")
        if self.format_json.isChecked():
            formats.append("json")
        if self.format_txt.isChecked():
            formats.append("txt")
        if self.format_html.isChecked():
            formats.append("html")
            
        data_types = []
        if self.data_dictionary.isChecked():
            data_types.append("dictionary")
        if self.data_analytics.isChecked():
            data_types.append("analytics")
        if self.data_profile.isChecked():
            data_types.append("profile")
        if self.data_history.isChecked():
            data_types.append("history")
            
        options = {
            "include_timestamps": self.include_timestamps.isChecked(),
            "include_metadata": self.include_metadata.isChecked(),
            "compress_output": self.compress_output.isChecked()
        }
        
        print(f"Export settings - Formats: {formats}, Data types: {data_types}, Options: {options}")
        
        return formats, data_types, options

class DataExporter:
    """Handle data export in various formats"""
    def __init__(self, db, user_profile, font_manager):
        self.db = db
        self.user_profile = user_profile
        self.font_manager = font_manager
        
    def export_data(self, formats, data_types, options, base_filename):
        """Export data in specified formats"""
        results = []
        timestamps = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            # Ensure base directory exists
            base_dir = Path(base_filename).parent
            if not base_dir.exists():
                base_dir.mkdir(parents=True, exist_ok=True)
            
            for fmt in formats:
                for data_type in data_types:
                    try:
                        filename = f"{base_filename}_{data_type}_{timestamps}.{fmt}"
                        print(f"Attempting to export {data_type} to {filename} in {fmt} format")
                        
                        if fmt == "csv":
                            success = self.export_csv(data_type, filename, options)
                        elif fmt == "json":
                            success = self._export_json(data_type, filename, options)
                        elif fmt == "txt":
                            success = self._export_txt(data_type, filename, options)
                        elif fmt == "html":
                            success = self._export_html(data_type, filename, options)
                        else:
                            success = False
                            print(f"Unsupported format: {fmt}")
                            
                        results.append((filename, success))
                        print(f"Export to {filename}: {'Success' if success else 'Failed'}")
                        
                    except Exception as e:
                        error_msg = f"Error exporting {data_type} to {fmt}: {str(e)}"
                        print(error_msg)
                        results.append((f"{base_filename}_{data_type}_{timestamps}.{fmt}", False))
                        
            return results
                
        except Exception as e:
            error_msg = f"Fatal export error: {str(e)}"
            print(error_msg)
            return [(f"Export failed: {str(e)}", False)]
    
    def export_csv(self, data_type, filename, options):
        """Export data as CSV"""
        try:
            print(f"Exporting CSV: {data_type} to {filename}")
            
            with open(filename, 'w', newline='', encoding='utf-8') as csv_file:
                if data_type == 'dictionary':
                    writer = csv.writer(csv_file)
                    # Header
                    headers = ["ID", "English", "Khmer", "Type", "Definition", "Example"]
                    if options.get("include_timestamps"):
                        headers.extend(["Created", "Updated"])
                    if options.get("include_metadata"):
                        headers.extend(["Difficulty", "Frequency", "Cultural_Tags", "Grammar_Notes"])
                    writer.writerow(headers)
                    
                    # Data
                    words = self.db.read_all_words()
                    print(f"Found {len(words)} words to export")
                    
                    for word in words:
                        row = list(word[:6]) # Basic fields
                        if options.get("include_timestamps") and len(word) > 10:
                            row.extend([word[10], word[11]]) # created_at, updated_at
                        if options.get("include_metadata") and len(word) > 6:
                            row.extend([
                                word[6] if len(word) > 6 else "", # Difficulty
                                word[7] if len(word) > 7 else "", # Frequency
                                word[8] if len(word) > 8 else "", # Cultural_tags
                                word[9] if len(word) > 9 else "", # grammar_notes,
                            ])
                        writer.writerow(row)
                        
                elif data_type == "analytics":
                    writer = csv.writer(csv_file)
                    writer.writerow(["Metric", "Value", "Description"])
                    words = self.db.read_all_words()
                    user_facts = self.user_profile.get_user_facts()
                    analytics_data = [
                        ("Total_words", len(words), "Total dictionary entries"),
                        ("User_Level", user_facts.get("user_level", "unknown"), "Current difficulty level"),
                        ("Search_Count", user_facts.get("search_count", 0), "Total searches performed"),
                        ("Session_Time", user_facts.get("session_time", 0), "Current session time in seconds"),
                        ("Avg_Word_Length", user_facts.get("avg_word_length", 0), "Average search term length")
                    ]
                    
                    for metric, value, desc in analytics_data:
                        writer.writerow([metric, value, desc])
                        
                elif data_type == "profile":
                    writer = csv.writer(csv_file)
                    writer.writerow(["Setting", "Value"])
                    profile_data = [
                        ("Difficulty_Level", self.user_profile.profile.get("difficulty_level", "beginner")),
                        ("Language_Preference", self.user_profile.profile.get("language_preference", "english")),
                        ("Total_Searches", self.user_profile.profile.get("search_count", 0)),
                        ("Last_Active", self.user_profile.profile.get("last_active", "unknown"))
                    ]
                    
                    for setting, value in profile_data:
                        writer.writerow([setting, value])
                        
                elif data_type == "history":
                    writer = csv.writer(csv_file)
                    writer.writerow(["Term", "Type", "Found", "Timestamp"])
                    history = self.user_profile.profile.get("search_history", [])
                    if history:
                        for search in history[-100:]: # Last 100 searches
                            writer.writerow([
                                search.get("term", ""),
                                search.get("type", ""),
                                search.get("found", ""),
                                search.get("timestamp", "")
                            ])
                    else:
                        writer.writerow(["No search history available", "", "", ""])
                        
            print(f"CSV export successful: {filename}")
            return True         
        except Exception as e:
            print(f"CSV export error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _export_json(self, data_type, filename, options):
        """Export data as JSON"""
        try:
            print(f"Exporting JSON: {data_type} to {filename}")
            
            data = {}
            if data_type == "dictionary":
                words = self.db.read_all_words()
                data["dictionary"] = []
                for word in words:
                    word_dict = {
                        "id": word[0],
                        "english": word[1],
                        "khmer": word[2],
                        "type": word[3],
                        "definition": word[4],
                        "example": word[5]
                    }
                    
                    if options.get("include_metadata") and len(word) > 6:
                        word_dict.update({
                            "difficulty": word[6] if len(word) > 6 else "",
                            "frequency": word[7] if len(word) > 7 else "",
                            "cultural_tags": word[8] if len(word) > 8 else "",
                            "grammar_notes": word[9] if len(word) > 9 else ""
                        })
                        
                    if options.get("include_timestamps") and len(word) > 10:
                        word_dict.update({
                            "created_at": word[10] if len(word) > 10 else "",
                            "updated_at": word[11] if len(word) > 11 else ""
                        })
                        
                    data["dictionary"].append(word_dict)
                    
            elif data_type == "analytics":
                words = self.db.read_all_words()
                user_facts = self.user_profile.get_user_facts()
                data["analytics"] = {
                    "total_words": len(words),
                    "user_stats": user_facts,
                    "generated_at": datetime.now().isoformat() if options.get("include_timestamps") else None
                }
                
            elif data_type == "profile":
                data["user_profile"] = dict(self.user_profile.profile)
                # Convert defaultdicts to regular dicts for JSON serialization
                if "word_preferences" in data["user_profile"]:
                    data["user_profile"]["word_preferences"] = dict(data["user_profile"]["word_preferences"])
                if "favorite_word_types" in data["user_profile"]:
                    data["user_profile"]["favorite_word_types"] = dict(data["user_profile"]["favorite_word_types"])
                    
            elif data_type == "history":
                data["search_history"] = self.user_profile.profile.get("search_history", [])
                if not data["search_history"]:
                    data["search_history"] = [{"note": "No search history available"}]
                    
            if options.get("include_metadata"):
                data["export_metadata"] = {
                    "export_time": datetime.now().isoformat(),
                    "export_version": "2.1",
                    "data_type": data_type
                }
                
            with open(filename, 'w', encoding='utf-8') as json_file:
                json.dump(data, json_file, indent=2, ensure_ascii=False)
            
            print(f"JSON export successful: {filename}")
            return True
        except Exception as e:
            print(f"JSON export error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _export_txt(self, data_type, filename, options):
        """Export data as plain text"""
        try:
            print(f"Exporting TXT: {data_type} to {filename}")
            
            with open(filename, 'w', encoding='utf-8') as text_file:
                text_file.write(f"Khmer-English Dictionary Export\n")
                text_file.write(f"Data Type: {data_type.title()}\n")
                if options.get("include_timestamps"):
                    text_file.write(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                text_file.write("=" * 50 + "\n\n")
                
                if data_type == "dictionary":
                    words = self.db.read_all_words()
                    for word in words:
                        text_file.write(f"ID: {word[0]}\n")
                        text_file.write(f"English: {word[1]}\n")
                        text_file.write(f"Khmer: {word[2]}\n")
                        text_file.write(f"Type: {word[3]}\n")
                        if word[4]:
                            text_file.write(f"Definition: {word[4]}\n")
                        if word[5]:
                            text_file.write(f"Example: {word[5]}\n")
                        text_file.write("-" * 30 + "\n")
                        
                elif data_type == "analytics":
                    words = self.db.read_all_words()
                    user_facts = self.user_profile.get_user_facts()
                    text_file.write(f"Total Dictionary Entries: {len(words)}\n")
                    text_file.write(f"User Level: {user_facts.get('user_level', 'unknown')}\n")
                    text_file.write(f"Total Searches: {user_facts.get('search_count', 0)}\n")
                    text_file.write(f"Session Time: {user_facts.get('session_time', 0)} seconds\n")
                    
                elif data_type == "profile":
                    profile = self.user_profile.profile
                    for key, value in profile.items():
                        if key not in ["search_history", "word_preferences", "favorite_word_types"]:
                            text_file.write(f"{key.replace('_', ' ').title()}: {value}\n")
                            
                elif data_type == "history":
                    history = self.user_profile.profile.get("search_history", [])
                    if history:
                        for search in history[-50:]:
                            text_file.write(f"Term: {search.get('term', '')}\n")
                            text_file.write(f"Type: {search.get('type', '')}\n")
                            text_file.write(f"Found: {search.get('found', False)}\n")
                            text_file.write(f"Time: {search.get('timestamp', '')}\n")
                            text_file.write("-" * 20 + "\n")
                    else:
                        text_file.write("No search history available.\n")
                        
            print(f"TXT export successful: {filename}")
            return True
        except Exception as e:
            print(f"TXT export error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _export_html(self, data_type, filename, options):
        """Export as HTML"""
        try:
            print(f"Exporting HTML: {data_type} to {filename}")
            
            with open(filename, 'w', encoding='utf-8') as html_file:
                html_file.write("<!DOCTYPE html>\n<html>\n<head>\n")
                html_file.write("<meta charset='UTF-8'>\n")
                html_file.write(f"<title>Khmer-English Dictionary - {data_type.title()}</title>\n")
                html_file.write("<style>\n")
                html_file.write("body { font-family: Arial, sans-serif; margin: 20px; }\n")
                html_file.write("table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }\n")
                html_file.write("th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }\n")
                html_file.write("th { background-color: #f2f2f2; }\n")
                html_file.write("h1 { color: #2e7d32; }\n")
                html_file.write("h2 { color: #1976d2; }\n")
                html_file.write("div.word-entry { margin-bottom: 15px; padding: 10px; border: 1px solid #e0e0e0; border-radius: 5px; }\n")
                html_file.write("</style>\n</head>\n<body>\n")
                
                html_file.write(f"<h1>Khmer-English Dictionary Export</h1>\n")
                html_file.write(f"<h2>Data Type: {data_type.title()}</h2>\n")
                if options.get("include_timestamps"):
                    html_file.write(f"<p><strong>Exported:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>\n")
                
                if data_type == "dictionary":
                    words = self.db.read_all_words()
                    for word in words:
                        html_file.write("<div class='word-entry'>\n")
                        html_file.write(f"<h3>{word[1]} ↔ {word[2]}</h3>\n")
                        html_file.write(f"<p><strong>Type:</strong> {word[3]}</p>\n")
                        if word[4]:
                            html_file.write(f"<p><strong>Definition:</strong> {word[4]}</p>\n")
                        if word[5]:
                            html_file.write(f"<p><strong>Example:</strong> <em>{word[5]}</em></p>\n")
                        html_file.write("</div>\n")
                        
                elif data_type == "analytics":
                    words = self.db.read_all_words()
                    user_facts = self.user_profile.get_user_facts()
                    html_file.write("<h3>Statistics Summary</h3>\n")
                    html_file.write(f"<p><strong>Total Words:</strong> {len(words)}</p>\n")
                    html_file.write(f"<p><strong>User Level:</strong> {user_facts.get('user_level', 'unknown')}</p>\n")
                    html_file.write(f"<p><strong>Total Searches:</strong> {user_facts.get('search_count', 0)}</p>\n")
                    
                html_file.write("</body>\n</html>\n")
                
            print(f"HTML export successful: {filename}")
            return True
        except Exception as e:
            print(f"HTML export error: {e}")
            import traceback
            traceback.print_exc()
            return False

# Voice search Component
class VoiceSearchThread(QThread):
    """Thread for handling voice recognition without blocking UI"""
    speech_recognized = pyqtSignal(str)
    speech_error = pyqtSignal(str)
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.recognizer = None
        self.microphone = None
        self.is_listening = False
        
        if SPEECH_RECOGNITION_AVAILABLE:
            try:
                self.recognizer = sr.Recognizer()
                self.microphone = sr.Microphone()
                # Adjust for ambient noise
                with self.microphone as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            except Exception as e:
                print(f"Voice recognition setup error: {e}")
                
    def run(self):
        """Run voice recognition in background thread"""
        if not SPEECH_RECOGNITION_AVAILABLE or not self.recognizer or not self.microphone:
            self.speech_error.emit("Speech recognition not available")
            return
        
        try:
            self.recording_started.emit()
            self.is_listening = True
            
            with self.microphone as source:
                # Listen for audio with timeout
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                
            self.recording_stopped.emit()
            self.is_listening = False
            
            # Try different recognition services
            try:
                # Try Google first (requires internet)
                text = self.recognizer.recognize_google(audio)
                self.speech_recognized.emit(text)
            except sr.RequestError:
                try:
                    # Fallback to offline recognition (if available)
                    text = self.recognizer.recognize_sphinx(audio)
                    self.speech_recognized.emit(text)
                except:
                    self.speech_error.emit("Could not recognize speech. Check internet connection")
            except sr.UnknownValueError:
                self.speech_error.emit("Could not understand audio. Please speak clearly.")
        except sr.WaitTimeoutError:
            self.recording_stopped.emit()
            self.speech_error.emit("Listening timeout. No speech detected.")
        except Exception as e:
            self.recording_stopped.emit()
            self.speech_error.emit(f"Voice recognition error: {str(e)}")
    
    def stop_listening(self):
        """Stop the listening process"""
        self.is_listening = False
        self.quit()

# Expert System Component
class Rule:
    """Individual rule in the expert system"""
    def __init__(self, name: str, conditions: List[str], actions: List[str], confidence: float = 1.0):
        self.name = name
        self.conditions = conditions
        self.actions = actions
        self.confidence = confidence
        self.fired_count = 0
    
    def evaluate(self, facts: Dict) -> bool:
        """Evaluate if all conditions are met"""
        for condition in self.conditions:
            if not self._evaluate_condition(condition, facts):
                return False
        return True
    
    def _evaluate_condition(self, condition: str, facts: Dict) -> bool:
        """Evaluate a single condition"""
        try:
            # Simple condition evaluation
            # Format: "word_type == 'noun'" or "search_count > 5"
            for key, value in facts.items():
                condition = condition.replace(key, f"'{value}'" if isinstance(value, str) else str(value))
            return eval(condition)
        except:
            return False
    
    def fire(self, facts: Dict) -> List[str]:
        """Execute rule actions"""
        self.fired_count += 1
        suggestions = []
        for action in self.actions:
            suggestion = self._execute_action(action, facts)
            if suggestion:
                suggestions.append(suggestion)
        return suggestions
    
    def _execute_action(self, action: str, facts: Dict) -> str:
        """Execute a single action"""
        # Replace placeholders in actions
        for key, value in facts.items():
            action = action.replace(f"{{{key}}}", str(value))
        return action

class ExpertSystemEngine:
    """Core expert system reasoning engine"""
    def __init__(self):
        self.rules = []
        self.facts = {}
        self.inference_chain = []
        self.initialize_rules()
    
    def initialize_rules(self):
        """Initialize the rule base"""
        # Word type suggestion rules
        self.add_rule(Rule(
            "noun_suggestions",
            ["word_type == 'noun'", "not_found == True"],
            ["Try searching for related objects, places, or things",
             "Consider checking spelling or trying synonyms"]
        ))
        
        self.add_rule(Rule(
            "verb_suggestions",
            ["word_type == 'verb'", "not_found == True"],
            ["Try searching for active words, infinitive forms",
             "Check for irregular verb forms"]
        ))
    
        # User behavior rules
        self.add_rule(Rule(
            "frequent_searcher",
            ["search_count > 10"],
            ["You're an active learner! Try exploring word categories",
             "Consider using the advanced features in Dictionary Manager"]
        ))
    
        self.add_rule(Rule(
            "khmer_learner",
            ["khmer_searches > english_searches", "session_time > 300"],
            ["Focus on Khmer script recognition",
             "Try using example sentences for better context"]
        ))
        
        # Difficulty adaptation rules
        self.add_rule(Rule(
            "beginner_user",
            ["avg_word_length < 5", "search_count < 5"],
            ["Start with basic vocabulary",
             "Use simple example sentences"]
        ))
        
        self.add_rule(Rule(
            "advanced_user",
            ["avg_word_length > 8", "search_count > 20"],
            ["Explore complex grammar patterns",
             "Try advanced word types and idioms"]
        ))
    
        # Context-based rules
        self.add_rule(Rule(
            "grammar_help",
            ["word_type == 'adjective'", "user_level == 'beginner'"],
            ["Adjectives in Khmer often follow nouns",
             "Practice with simple descriptive phrases"]
        ))
    
        self.add_rule(Rule(
            "cultural_context",
            ["contains_honorific == True"],
            ["This word shows respect in Khmer culture",
             "Usage depends on social context and age"]
        ))
    
    def add_rule(self, rule: Rule):
        """Add a new rule to the system"""
        self.rules.append(rule)
        
    def add_fact(self, key: str, value):
        """Add a fact to the knowledge base"""
        self.facts[key] = value
    
    def infer(self) -> List[str]:
        """Rule inference engine and return suggestions"""
        suggestions = []
        self.inference_chain = []
        for rule in self.rules:
            if rule.evaluate(self.facts):
                rule_suggestions = rule.fire(self.facts)
                suggestions.extend(rule_suggestions)
                self.inference_chain.append(f"Fired rule: '{rule.name}'")
        return suggestions
    
    def get_explanation(self) -> str:
        """Get explanation of inference process"""
        return "\n".join(self.inference_chain)

class SimpleWordEmbeddings:
    """Lightweight word embeddings similarity search"""
    def __init__(self):
        self.embeddings = {}
        self.vocabulary = set()
        self.similarity_cache = {}
    
    def add_word(self, word: str, context: str = ""):
        """Add word to vocabulary with simple feature extraction"""
        word = word.lower().strip()
        self.vocabulary.add(word)
        # Simple features vector based on character n-grams and length
        features = self._extract_features(word, context)
        self.embeddings[word] = features
    
    def _extract_features(self, word: str, context: str = "") -> List[float]:
        """Extract simple features for word similarity"""
        features = []
        # Length feature
        features.append(len(word) / 20.0) # Normalized length
        
        # Character frequency features
        char_counts = Counter(word.lower())
        common_chars = 'aeioutrnslh'
        for char in common_chars:
            features.append(char_counts.get(char, 0) / len(word))
            
        # N-gram features (bigram)
        bigrams = [word[i:i+2] for i in range(len(word) - 1)]
        common_bigrams = ['th', 'er', 'on', 'an', 're', 'he', 'in', 'ed', 'nd', 'ha']
        for bigram in common_bigrams:
            features.append(1.0 if bigram in bigrams else 0.0)
            
        # Context features
        if context:
            features.append(1.0 if 'example' in context.lower() else 0.0)
            features.append(1.0 if any(word in context.lower() for word in ['formal', 'respect', 'polite']) else 0.0)
            
        return features
    
    def find_similar(self, word: str, n: int = 5) -> List[Tuple[str, float]]:
        """Find n most similar words"""
        word = word.lower().strip()
        if word not in self.embeddings:
            return []
            
        similarities = []
        target_features = self.embeddings[word]
        for other_word, other_features in self.embeddings.items():
            if other_word != word:
                similarity = self._cosine_similarity(target_features, other_features)
                similarities.append((other_word, similarity))
                
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:n]
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate similarity between two vectors"""
        if len(vec1) != len(vec2):
            return 0.0
            
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(a * a for a in vec2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
            
        return dot_product / (magnitude1 * magnitude2)

class UserProfileManager:
    """Track and model user behaviors"""
    def __init__(self, profile_file: str = "user_profile.json"):
        self.profile_file = profile_file
        self.profile = self._load_profile()
        self.session_start = datetime.now()
        # Ensure defaultdicts are properly set up
        if not isinstance(self.profile.get("word_preferences"), defaultdict):
            self.profile["word_preferences"] = defaultdict(int, self.profile.get("word_preferences", {}))
        if not isinstance(self.profile.get("favorite_word_types"), defaultdict):
            self.profile["favorite_word_types"] = defaultdict(int, self.profile.get("favorite_word_types", {}))
    
    def _load_profile(self) -> Dict:
        """Load user profile from file"""
        default_profile = {
            "search_history": [],
            "word_preferences": defaultdict(int),
            "language_preference": "english",
            "difficulty_level": "beginner",
            "search_count": 0,
            "session_time": 0,
            "favorite_word_types": defaultdict(int),
            "error_patterns": [],
            "learning_progress": {"beginner": 0, "intermediate": 0, "advanced": 0},
            "last_active": datetime.now().isoformat()
        }
        
        try:
            if os.path.exists(self.profile_file):
                with open(self.profile_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    # Merge with defaults to handle new fields
                    for key, value in default_profile.items():
                        if key not in loaded:
                            loaded[key] = value
                    
                    # Convert regular dicts back to defaultdicts
                    if 'word_preferences' in loaded and not isinstance(loaded['word_preferences'], defaultdict):
                        loaded['word_preferences'] = defaultdict(int, loaded['word_preferences'])
                    if 'favorite_word_types' in loaded and not isinstance(loaded['favorite_word_types'], defaultdict):
                        loaded['favorite_word_types'] = defaultdict(int, loaded['favorite_word_types'])
                    return loaded
        except Exception as e:
            print(f"Error loading profile: {e}")
            
        return default_profile
    
    def save_profile(self):
        """Save user profile to file"""
        try:
            # Update session time
            self.profile["session_time"] = (datetime.now() - self.session_start).seconds
            self.profile["last_active"] = datetime.now().isoformat()
            
            # Convert defaultdict to regular dicts for JSON serialization
            profile_to_save = dict(self.profile)
            for key, value in profile_to_save.items():
                if isinstance(value, defaultdict):
                    profile_to_save[key] = dict(value)
                    
            with open(self.profile_file, 'w', encoding='utf-8') as f:
                json.dump(profile_to_save, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving profile: {e}")
    
    def record_search(self, term: str, search_type: str, found: bool):
        """Record a search action"""
        search_record = {
            "term": term,
            "type": search_type,
            "found": found,
            "timestamp": datetime.now().isoformat()
        }
        
        self.profile["search_history"].append(search_record)
        self.profile["search_count"] += 1
        
        # Keep only last 1000 searches
        if len(self.profile["search_history"]) > 1000:
            self.profile["search_history"] = self.profile["search_history"][-1000:]
            
        # Update preferences - ensure it's a defaultdict
        if not isinstance(self.profile["word_preferences"], defaultdict):
            self.profile["word_preferences"] = defaultdict(int, self.profile["word_preferences"])
        if found:
            self.profile["word_preferences"][term] += 1
    
    def record_word_interaction(self, word_type: str, difficulty: str = "medium"):
        """Record interaction with specific word type"""
        # Ensure it's a defaultdict
        if not isinstance(self.profile["favorite_word_types"], defaultdict):
            self.profile["favorite_word_types"] = defaultdict(int, self.profile["favorite_word_types"])
        
        self.profile["favorite_word_types"][word_type] += 1
        
        # Update difficulty level based on usage patterns
        if difficulty == "hard" and self.profile["difficulty_level"] == "beginner":
            self.profile["learning_progress"]["intermediate"] += 1
            if self.profile["learning_progress"]["intermediate"] > 20:
                self.profile["difficulty_level"] = "intermediate"
    
    def get_recommendation(self) -> List[str]:
        """Get personalized recommendations"""
        recommendations = []
        
        # Analyze search patterns
        recent_searches = self.profile["search_history"][-20:] if self.profile["search_history"] else []
        if len(recent_searches) > 5:
            # Find most searched word types
            type_counts = defaultdict(int)
            for search in recent_searches:
                # Simple word type detection (would be enhanced with actual word type data)
                if len(search["term"]) > 8:
                    type_counts["complex"] += 1
                elif search["type"] == "khmer":
                    type_counts["khmer_focus"] += 1
                    
            if type_counts["complex"] > 3:
                recommendations.append("You're exploring advanced vocabulary! Try the word type filters.")
            if type_counts["khmer_focus"] > 3:
                recommendations.append("Great Khmer practice! Consider learning about Khmer grammar patterns.")
                
        # Difficulty-based recommendations
        if self.profile["difficulty_level"] == "beginner" and self.profile["search_count"] > 10:
            recommendations.append("Ready for intermediate words? Try exploring different word types.")
            
        return recommendations
    
    def get_user_facts(self) -> Dict:
        """Get user facts for expert system"""
        session_time = (datetime.now() - self.session_start).seconds
        recent_searches = self.profile["search_history"][-10:] if self.profile["search_history"] else []
        khmer_searches = sum(1 for s in recent_searches if s["type"] == "khmer")
        english_searches = sum(1 for s in recent_searches if s["type"] == "english")
        avg_word_length = 0
        if recent_searches:
            avg_word_length = sum(len(s["term"]) for s in recent_searches) / len(recent_searches)
            
        return {
            "search_count": self.profile["search_count"],
            "session_time": session_time,
            "khmer_searches": khmer_searches,
            "english_searches": english_searches,
            "avg_word_length": avg_word_length,
            "user_level": self.profile["difficulty_level"],
            "favorite_types": list(self.profile["favorite_word_types"].keys())
        }

class AIExplanationGenerator:
    """Generate context explanations and grammar help"""
    def __init__(self):
        self.grammar_rules = self._load_grammar_rules()
        self.cultural_context = self._load_cultural_context()
    
    def _load_grammar_rules(self) -> Dict:
        """Load Khmer grammar rules"""
        return {
            "noun": {
                "structure": "Khmer nouns don't change for singular/plural",
                "usage": "Often combined with classifiers when counting",
                "example": "សៀវភៅ (book) + មួយ (one) + ក្បាល (classifier)"
            },
            "verb": {
                "structure": "Verbs don't conjugate for tenses like English",
                "usage": "Time indicators show when action occurs",
                "example": "ហូប (eat) + ហើយ (already) = ate"
            },
            "adjective": {
                "structure": "Usually follows the noun it describes",
                "usage": "Can be intensified with particles",
                "example": "ផ្ទះ (house) + ធំ (big) = big house"
            },
            "greeting": {
                "structure": "Varies by time of day and formality",
                "usage": "Shows respect and social awareness",
                "example": "សួស្ដី for casual, ជំរាបសួរ for formal"
            }
        }
    
    def _load_cultural_context(self) -> Dict:
        """Load cultural context information"""
        return {
            "honorifics": "Khmer uses different vocabulary levels to show respect",
            "family_terms": "Family relationships are very specific in Khmer",
            "religion_terms": "Buddhism influences many expressions",
            "formal_speech": "Used with elders, authorities, and strangers",
            "age_hierarchy": "Language changes based on relative age",
        }
    
    def generate_explanation(self, word_data: Tuple, context: str = "") -> str:
        """Generate detailed explanations for a word"""
        if not word_data:
            return "No explanation available"
            
        word_id, english, khmer, word_type, definition, example = word_data[:6]
        explanation = f"<h3>Expert Analysis: {english} → {khmer}</h3>"
        
        # Grammar explanation
        if word_type in self.grammar_rules:
            rule = self.grammar_rules[word_type]
            explanation += f"""
            <h4>Grammar Structure:</h4>
            <p><strong>Rule:</strong> {rule['structure']}</p>
            <p><strong>Usage:</strong> {rule['usage']}</p>
            <p><strong>Example:</strong> {rule['example']}</p>
            """
            
        # Word analysis
        explanation += f"""
        <h4>Word Analysis:</h4>
        <ul>
            <li><strong>Type:</strong> {word_type.title()}</li>
            <li><strong>Length:</strong> {len(khmer)} Khmer characters</li>
            <li><strong>Complexity:</strong> {'Advanced' if len(english) > 8 else 'Basic'}</li>
        </ul>
        """
        
        # Cultural context
        cultural_notes = self._get_cultural_notes(english, khmer, word_type)
        if cultural_notes:
            explanation += f"""
            <h4>Cultural Context:</h4>
            <p>{cultural_notes}</p>
            """
            
        # Usage tips
        tips = self._generate_usage_tips(english, khmer, word_type)
        explanation += f"""
        <h4>Usage Tips:</h4>
        <ul>
        """
        for tip in tips:
            explanation += f"<li>{tip}</li>"
        explanation += "</ul>"
        
        # Related concepts
        explanation += f"""
        <h4>Learning Connections:</h4>
        <p>This word connects to: {word_type} vocabulary, Khmer script practice,
        {'formal speech patterns' if len(english) > 6 else 'basic conversation'}</p>
        """
        
        return explanation
    
    def _get_cultural_notes(self, english: str, khmer: str, word_type: str) -> str:
        """Get cultural context for the word"""
        cultural_keywords = {
            "family": ["mother", "father", "uncle", "aunt", "grandparent"],
            "respect": ["please", "thank", "sorry", "excuse"],
            "religion": ["temple", "monk", "pray", "festival"],
            "food": ["rice", "fish", "soup", "curry"],
        }
        
        for category, keywords in cultural_keywords.items():
            if any(keyword in english.lower() for keyword in keywords):
                if category == "family":
                    return "Family terms in Khmer are very specific about relationships and age."
                elif category == "respect":
                    return "This word is important for polite communication in Khmer culture."
                elif category == "religion":
                    return "This term reflects Buddhist influence in Cambodian culture."
                elif category == "food":
                    return "Food vocabulary is central to Cambodian social interactions."
        
        return ""
    
    def _generate_usage_tips(self, english: str, khmer: str, word_type: str) -> List[str]:
        """Generate practical usage tips"""
        tips = []
        
        if word_type == "noun":
            tips.append("Remember: Khmer nouns don't change for plural forms")
            tips.append("Use classifiers when counting specific quantities")
        elif word_type == "verb":
            tips.append("Add time markers (ហើយ, នឹង) to indicate tenses")
            tips.append("Verb order: Subject + Verb + Object")
        elif word_type == "adjective":
            tips.append("Place after the noun: [noun] + [adjective]")
            tips.append("Can intensify with 'ណាស់' (Very)")
        elif word_type == "greeting":
            tips.append("Choose formality level based on the situation")
            tips.append("Time of day affects which greeting to use")
            
        # Length based-tips
        if len(khmer) > 6:
            tips.append("Complex word - practice writing the script slowly")
        else:
            tips.append("Short word - good for memorization practice")
            
        # Frequency
        if english.lower() in ["hello", "thank", "please", "water", "food"]:
            tips.append("High-frequency word - essential for daily conversation")
            
        return tips

# Enhanced Database with Expert System Features
class DictionaryDatabase:
    """Enhanced database with expert system features"""
    def __init__(self, db_path="expert_khmer_dictionary.db"):
        self.db_path = db_path
        self.embeddings = SimpleWordEmbeddings()
        self.init_database()
        self.build_embeddings()
    
    def init_database(self):
        """Initialize the SQLite database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Main dictionary table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dictionary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                english_word TEXT NOT NULL UNIQUE,
                khmer_word TEXT NOT NULL,
                word_type TEXT DEFAULT 'noun',
                definition TEXT,
                example_sentence TEXT,
                difficulty_level TEXT DEFAULT 'beginner',
                frequency_score INTEGER DEFAULT 1,
                cultural_tags TEXT,
                grammar_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # User interactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word_id INTEGER,
                interaction_type TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_rating INTEGER,
                FOREIGN KEY (word_id) REFERENCES dictionary (id)
            )               
        ''')
        
        # Check if we need to populate with sample data
        cursor.execute("SELECT COUNT(*) FROM dictionary")
        if cursor.fetchone()[0] == 0:
            self._insert_enhanced_sample_data(cursor)
            
        conn.commit()
        conn.close()
        
    def _insert_enhanced_sample_data(self, cursor):
        """Insert enhanced sample data with expert system features"""
        enhanced_sample = [
            ("hello", "សួស្ដី", "greeting", "A common greeting", "Hello, how are you?", "beginner", 10, "social,polite", "Used as casual greeting"),
            ("goodbye", "លាហើយ", "greeting", "Farewell expression", "Goodbye, see you tomorrow!", "beginner", 8, "social,departure", "Casual farewell"),
            ("thank you", "អរគុណ", "expression", "Express gratitude", "Thank you for your help", "beginner", 9, "polite,respect", "Shows appreciation"),
            ("please", "សូម", "adverb", "Polite request", "Please help me", "beginner", 9, "polite,formal", "Makes requests polite"),
            ("yes", "បាទ/ចាស", "response", "Affirmative", "Yes, I agree", "beginner", 10, "response,agreement", "បាទ for males, ចាស for females"),
            ("no", "ទេ", "response", "Negative response", "No, I don't want", "beginner", 8, "response,disagreement", "Simple negative"),
            ("water", "ទឹក", "noun", "Essential liquid", "I need water", "beginner", 9, "daily,essential", "Essential for life"),
            ("food", "អាហារ", "noun", "Nutrition", "The food is delicious", "beginner", 8, "daily,culture", "Central to culture"),
            ("house", "ផ្ទះ", "noun", "Living building", "This is my house", "beginner", 7, "home,family", "Place of residence"),
            ("school", "សាលា", "noun", "Education institution", "I go to school every day", "beginner", 6, "education,children", "Learning place"),
            ("book", "សៀវភៅ", "noun", "Written words", "I'm reading a book now", "intermediate", 5, "education,knowledge", "Knowledge container"),
            ("student", "សិស្ស", "noun", "Learning person", "She is a good student", "intermediate", 6, "education,youth", "Knowledge seeker"),
            ("teacher", "គ្រូ", "noun", "Education provider", "The teacher explains well", "intermediate", 5, "education,respect", "Highly respected profession"),
            ("mother", "ម្ដាយ", "noun", "Female parent", "I love my mother", "beginner", 8, "family,respect", "Very important family role"),
            ("father", "ឪពុក", "noun", "Male parent", "My father works hard", "beginner", 8, "family,respect", "Family head traditionally"),
            ("beautiful", "ស្អាត", "adjective", "Pleasing appearance", "She is beautiful", "intermediate", 6, "description,appearance", "Common compliment"),
            ("big", "ធំ", "adjective", "Large size", "This is a big house", "beginner", 7, "size,description", "Basic size descriptor"),
            ("small", "តូច", "adjective", "Little size", "I have a small car", "beginner", 7, "size,description", "Basic size descriptor"),
            ("eat", "ញ៉ាំ", "verb", "Consume food", "Let's eat together", "beginner", 9, "action,daily", "Essential verb"),
            ("go", "ទៅ", "verb", "Move to place", "I go to work", "beginner", 9, "action,movement", "Basic movement verb"),
        ]
           
        cursor.executemany('''
            INSERT INTO dictionary (english_word, khmer_word, word_type, definition, 
                                    example_sentence, difficulty_level, frequency_score,
                                    cultural_tags, grammar_notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', enhanced_sample)
    
    def build_embeddings(self):
        """Build word embeddings for similarity search"""
        words = self.read_all_words()
        for word in words:
            english, khmer, definition = word[1], word[2], word[4] or ""
            context = f"{definition} {word[8] or ''} {word[9] or ''}" # Including cultural tags and grammar notes
            self.embeddings.add_word(english, context)
            self.embeddings.add_word(khmer, context)
    
    def find_similar_words(self, word: str, n: int = 5) -> List[Tuple[str, float]]:
        """Find similar words using embeddings"""
        return self.embeddings.find_similar(word, n)
    
    def get_smart_suggestions(self, search_term: str, search_type: str) -> List[Tuple]:
        """Get AI-powered suggestions for failed searches"""
        similar_words = self.find_similar_words(search_term, 3)
        suggestions = []
        for similar_word, similarity in similar_words:
            if similarity > 0.3: # Threshold
                results = self.read_word(similar_word, "english")
                if not results:
                    results = self.read_word(similar_word, "khmer")
                suggestions.extend(results)
        return suggestions[:5] # Return top 5 suggestions
        
    def create_word(self, english_word, khmer_word, word_type="noun", definition="", example="",
                    difficulty="beginner", cultural_tags="", grammar_notes=""):
        """CREATE operation - Add new word to dictionary"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO dictionary (english_word, khmer_word, word_type, definition,
                example_sentence, difficulty_level, cultural_tags, grammar_notes)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?)
            ''', (english_word.lower().strip(), khmer_word.strip(), word_type, 
                definition, example, difficulty, cultural_tags, grammar_notes))
            conn.commit()
            word_id = cursor.lastrowid
            conn.close()
            
            # Update embeddings
            context = f"{definition} {cultural_tags} {grammar_notes}"
            self.embeddings.add_word(english_word, context)
            self.embeddings.add_word(khmer_word, context)
            
            return word_id
        except sqlite3.IntegrityError:
            raise ValueError(f"Word '{english_word}' already exists in dictionary")
        except Exception as e:
            raise ValueError(f"Database error: {str(e)}")
    
    def read_word(self, search_term, search_type="english"):
        """READ operation - Search for words"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            if search_type == "english":
                cursor.execute('''
                    SELECT * FROM dictionary
                    WHERE english_word LIKE ? OR english_word = ?               
                    ORDER BY frequency_score DESC, english_word
                ''', (f"%{search_term.lower()}%", search_term.lower()))
            else:
                cursor.execute('''
                    SELECT * FROM dictionary
                    WHERE khmer_word LIKE ?
                    ORDER BY frequency_score DESC, khmer_word
                ''', (f"%{search_term}%",))
            results = cursor.fetchall()
            conn.close()
            return results
        except Exception as e:
            conn.close()
            return []
    
    def read_all_words(self):
        """Enhanced READ ALL operation"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM dictionary ORDER BY frequency_score DESC, english_word")
            results = cursor.fetchall()
            conn.close()
            return results
        except Exception as e:
            conn.close()
            return []
        
    def update_word(self, word_id, english_word=None, khmer_word=None, word_type=None, 
                    definition=None, example=None, difficulty=None, cultural_tags=None, grammar_notes=None):
        """Enhanced UPDATE operation"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            updates = []
            params = []
            if english_word is not None:
                updates.append("english_word = ?")
                params.append(english_word.lower().strip())
            if khmer_word is not None:
                updates.append("khmer_word = ?")
                params.append(khmer_word.strip())
            if word_type is not None:
                updates.append("word_type = ?")
                params.append(word_type)
            if definition is not None:
                updates.append("definition = ?")
                params.append(definition)
            if example is not None:
                updates.append("example_sentence = ?")
                params.append(example)
            if difficulty is not None:
                updates.append("difficulty_level = ?")
                params.append(difficulty)
            if cultural_tags is not None:
                updates.append("cultural_tags = ?")
                params.append(cultural_tags)
            if grammar_notes is not None:
                updates.append("grammar_notes = ?")
                params.append(grammar_notes)
            
            params.append(word_id)
            
            if updates:
                query = f"UPDATE dictionary SET {', '.join(updates)} WHERE id = ?"
                cursor.execute(query, params)
                conn.commit()
                
            conn.close()
        except Exception as e:
            conn.close()
            raise ValueError(f"Update error: {str(e)}")
    
    def delete_word(self, word_id):
        """Enhanced DELETE operation"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM dictionary WHERE id = ?", (word_id,))
            conn.commit()
            deleted_count = cursor.rowcount
            conn.close()
            return deleted_count > 0
        except Exception as e:
            conn.close()
            raise ValueError(f"Delete error: {str(e)}")
    
    def get_random_words(self, limit=5):
        """Get random words for display"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM dictionary ORDER BY RANDOM() LIMIT ?", (limit,))
            results = cursor.fetchall()
            conn.close()
            return results
        except Exception as e:
            conn.close()
            return []

class FontManager:
    """Manage Khmer OS Siemreap font for the application - Single font size 11"""
    
    def __init__(self):
        self.khmer_font = None
        self.font_size = 11 # Single font size for entire application
        self.init_fonts()
    
    def init_fonts(self):
        """Initialize and load Khmer OS Siemreap font"""
        preferred_fonts = [
            "Khmer OS Siemreap",
            "Khmer OS",
            "Noto Sans Khmer",
            "Arial Unicode MS"
        ]
        
        try:
            available_families = QFontDatabase.families()
        except:
            available_families = []
        
        for font_name in preferred_fonts:
            if font_name in available_families:
                self.khmer_font = QFont(font_name, self.font_size)
                break
        
        if self.khmer_font is None:
            self.khmer_font = QFont("Arial", self.font_size)
            
        # Configure font properties for optimal Khmer rendering
        self.khmer_font.setStyleHint(QFont.StyleHint.SansSerif)
        self.khmer_font.setWeight(QFont.Weight.Normal)
        # Fixed: Use QFont.StyleStrategy instead of QFont.StyleFlag
        self.khmer_font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias | QFont.StyleStrategy.PreferQuality)
        self.khmer_font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
    
    def get_font(self, size=None, bold=False):
        """Get the standard font with specified size and weight"""
        if size is None:
            size = self.font_size
        font = QFont(self.khmer_font)
        font.setPointSize(size)
        if bold:
            font.setWeight(QFont.Weight.Bold)
        return font
    
    def get_font_family(self):
        """Get the font family name"""
        return self.khmer_font.family()
    
    def apply_font(self, widget, size=None, bold=False):
        """Apply font to any widget recursively"""
        if size is None:
            size = self.font_size
        try:
            font = self.get_font(size, bold)
            widget.setFont(font)
            # Apply to all child widgets recursively
            for child in widget.findChildren(QWidget):
                if hasattr(child, 'setFont'):
                    child.setFont(font)
        except Exception as e:
            print(f"Font application error: {e}")
    
    def create_message_box(self, parent, icon, title, text, buttons=None):
        """Create a message box with proper Khmer font"""
        msg_box = QMessageBox(parent)
        msg_box.setIcon(icon)
        msg_box.setWindowTitle(title)
        msg_box.setText(text)
        # Apply font to message box and all children
        self.apply_font(msg_box, self.font_size)
        if buttons:
            msg_box.setStandardButtons(buttons)
        
        return msg_box

class DictionaryTableModel(QAbstractTableModel):
    """Table model for dictionary entries with full CRUD support"""
    def __init__(self, data=None):
        super().__init__()
        self.headers = ["ID", "English", "Khmer", "Type", "Definition", "Example"]
        self._data = data or []
        
    def rowCount(self, parent=QModelIndex()):
        return len(self._data)
    
    def columnCount(self, parent=QModelIndex()):
        return len(self.headers)
    
    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return QVariant()
        if role == Qt.ItemDataRole.DisplayRole:
            row = index.row()
            col = index.column()
            if row < len(self._data):
                # Return data excluding created_at and updated_at columns
                data_item = self._data[row]
                if col < len(self.headers): # only first 6 columns
                    filter_mapping = [0, 1, 2, 3, 4, 5]
                    if col < len(filter_mapping) and filter_mapping[col] < len(data_item):
                        value = data_item[filter_mapping[col]]
                        return str(value) if value is not None else ""
        return QVariant()
    
    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            if section < len(self.headers):
                return self.headers[section]
        return QVariant()
    
    def update_data(self, new_data):
        """Update the model with new data"""
        self.beginResetModel()
        self._data = new_data or []
        self.endResetModel()
    
    def get_row_data(self, row):
        """Get complete data for a specific row"""
        if 0 <= row < len(self._data):
            return self._data[row]
        return None
    
    def add_row(self, row_data):
        """Add a new row to the model"""
        self.beginInsertRows(QModelIndex(), len(self._data), len(self._data))
        self._data.append(row_data)
        self.endInsertRows()
    
    def remove_row(self, row):
        """Remove a row from the model"""
        if 0 <= row < len(self._data):
            self.beginRemoveRows(QModelIndex(), row, row)
            del self._data[row]
            self.endRemoveRows()
            return True
        return False

class WordDetailsDialog(QDialog):
    """Dialog for viewing detailed word information"""
    def __init__(self, word_data, font_manager, ai_generator, parent=None):
        super().__init__(parent)
        self.font_manager = font_manager
        self.word_data = word_data
        self.ai_generator = ai_generator
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("Word Details with AI Analysis")
        self.setModal(True)
        self.resize(700, 550)
        
        # Set window icon
        self.setWindowIcon(get_icon("view"))
        
        # Apply font to dialog
        self.font_manager.apply_font(self)
        layout = QVBoxLayout()
        
        if self.word_data:
            # Create scrollable content area
            scroll = QScrollArea()
            scroll_widget = QWidget()
            scroll_layout = QVBoxLayout()
            
            word_id, english, khmer, word_type = self.word_data[0], self.word_data[1], self.word_data[2], self.word_data[3]
            definition, example = self.word_data[4], self.word_data[5]
            
            # Basic info
            basic_info = QTextBrowser()
            self.font_manager.apply_font(basic_info)
            basic_info.setMaximumHeight(150)
            
            # Display word information
            basic_content = f"""
                <h2 style='color: #2E7D32;'>{english.title()} ↔ {khmer}</h2>
                <p><strong>Word ID:</strong> {word_id}</p>
                <p><strong>Word Type:</strong> {word_type.title()}</p>
                <p><strong>Definition:</strong> {definition or 'No definition provided'}</p>
                <p><strong>Example:</strong> {example or 'No example provided'}</p>
            """
            
            # AI explanation
            ai_info = QTextBrowser()
            self.font_manager.apply_font(ai_info)
            ai_explanation = self.ai_generator.generate_explanation(self.word_data)
            ai_info.setHtml(ai_explanation)
            
            scroll_layout.addWidget(basic_info)
            scroll_layout.addWidget(ai_info)
            scroll_widget.setLayout(scroll_layout)
            scroll.setWidget(scroll_widget)
            scroll.setWidgetResizable(True)
            layout.addWidget(scroll)
            
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        self.font_manager.apply_font(button_box)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)
        self.setLayout(layout)

class TranslatorWidget(QWidget):
    word_searched = pyqtSignal(str, str, bool)
    
    def __init__(self, db, font_manager, expert_engine, user_profile, ai_generator):
        super().__init__()
        self.db = db
        self.font_manager = font_manager
        self.expert_engine = expert_engine
        self.user_profile = user_profile
        self.ai_generator = ai_generator
        self.init_ui()
    
    def init_ui(self):
        # Apply font to entire widget
        self.font_manager.apply_font(self)
        layout = QVBoxLayout()
        
        # Title section
        title_frame = QFrame()
        title_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        title_layout = QVBoxLayout()
        
        title = QLabel("Khmer-English Dictionary (AI-Enhanced)")
        self.font_manager.apply_font(title, bold=True)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        subtitle = QLabel("វចនានុក្រមអង់គ្លេស-ខ្មែរ (ដាក់បញ្ចូលបញ្ញាសប្បនិម្មិត)")
        self.font_manager.apply_font(subtitle)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        title_frame.setLayout(title_layout)
        layout.addWidget(title_frame)
        
        # Expert suggestions section (scrollable)
        suggestion_group = QGroupBox("Expert System Recommendations")
        self.font_manager.apply_font(suggestion_group)
        suggestion_group.setFixedHeight(80)
        suggestion_layout = QVBoxLayout()
        
        self.suggestion_scroll = QScrollArea()
        self.suggestion_display = QLabel("Welcome! Start searching to get personalized recommendations.")
        self.suggestion_display.setWordWrap(True)
        self.font_manager.apply_font(self.suggestion_display)
        
        self.suggestion_scroll.setWidget(self.suggestion_display)
        self.suggestion_scroll.setWidgetResizable(True)
        self.suggestion_scroll.setMaximumHeight(60)
        
        suggestion_layout.addWidget(self.suggestion_scroll)
        suggestion_group.setLayout(suggestion_layout)
        layout.addWidget(suggestion_group)
        
        # Search section with scroll area
        search_group = QGroupBox("Search Translation")
        search_group.setFixedHeight(480)
        self.font_manager.apply_font(search_group, bold=True)
        search_layout = QVBoxLayout()
        
        # Search control with voice search button integrated
        controls_layout = QHBoxLayout()
        
        direction_label = QLabel("Direction:")
        self.font_manager.apply_font(direction_label)
        
        self.search_combo = QComboBox()
        self.search_combo.addItems(["English -> Khmer", "Khmer -> English", "Smart Search"])
        self.font_manager.apply_font(self.search_combo)
        
        word_label = QLabel("Word:")
        self.font_manager.apply_font(word_label)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Type word to translate...")
        self.font_manager.apply_font(self.search_input)
        self.search_input.returnPressed.connect(self.search_word)
        
        # Voice search button (between input and search button)
        self.voice_button = QPushButton()
        self.voice_button.setIcon(get_icon("voice"))
        self.voice_button.setToolTip("Click and speak your search term")
        self.voice_button.setFixedSize(40, 40)
        self.voice_button.clicked.connect(self.start_voice_search)
        
        self.search_button = QPushButton("Search")
        self.search_button.setIcon(get_icon("search"))
        self.font_manager.apply_font(self.search_button)
        self.search_button.clicked.connect(self.search_word)
        self.search_button.setDefault(True)
        
        controls_layout.addWidget(direction_label)
        controls_layout.addWidget(self.search_combo)
        controls_layout.addWidget(word_label)
        controls_layout.addWidget(self.search_input)
        controls_layout.addWidget(self.voice_button)
        controls_layout.addWidget(self.search_button)
        search_layout.addLayout(controls_layout)
        
        # Voice search status (separate line)
        self.voice_status_label = QLabel("Ready for voice search")
        self.font_manager.apply_font(self.voice_status_label)
        self.voice_status_label.setStyleSheet("color: #666; font-style: italic; margin-left: 5px")
        search_layout.addWidget(self.voice_status_label)
        
        # Results display with Scroll
        results_label = QLabel("Results:")
        self.font_manager.apply_font(results_label)
        
        self.results_scroll = QScrollArea()
        self.results_display = QTextBrowser()
        self.font_manager.apply_font(self.results_display)
        
        self.results_scroll.setWidget(self.results_display)
        self.results_scroll.setWidgetResizable(True)
        self.results_scroll.setMaximumHeight(380)
        
        search_layout.addWidget(results_label)
        search_layout.addWidget(self.results_scroll)
        search_group.setLayout(search_layout)
        layout.addWidget(search_group)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.clear_button = QPushButton("Clear")
        self.clear_button.setIcon(get_icon("clear"))
        self.font_manager.apply_font(self.clear_button)
        self.clear_button.clicked.connect(self.clear_search)
        
        self.random_button = QPushButton("Random Word")
        self.random_button.setIcon(get_icon("random"))
        self.font_manager.apply_font(self.random_button)
        self.random_button.clicked.connect(self.show_smart_random_word)
        
        self.similar_button = QPushButton("Find Similar")
        self.similar_button.setIcon(get_icon("similar"))
        self.font_manager.apply_font(self.similar_button)
        self.similar_button.clicked.connect(self.find_similar_words)
        
        button_layout.addWidget(self.clear_button)
        button_layout.addWidget(self.random_button)
        button_layout.addWidget(self.similar_button)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        layout.addStretch()
        self.setLayout(layout)
        
        # Initialize voice search component
        self.voice_thread = None
        self.init_voice_search()
        
        # Update expert suggestions on startup
        self.update_expert_suggestions()
        
    def init_voice_search(self):
        """Initialize voice search functionality"""
        # Check if voice recognition is available
        if not SPEECH_RECOGNITION_AVAILABLE:
            self.voice_button.setEnabled(False)
            self.voice_button.setToolTip("Install speech recognition: pip install SpeechRecognition")
            self.voice_status_label.setText("Voice search requires: pip install SpeechRecognition pyaudio")
            self.voice_status_label.setStyleSheet("color: #f44336")
        else:
            self.voice_button.setEnabled(True)
            self.voice_button.setToolTip("Click and speak your search term")
            self.voice_status_label.setText("Ready for voice search")
            self.voice_status_label.setStyleSheet("color: #666; font-style: italic;")
    
    def start_voice_search(self):
        """Start voice recognition"""
        if not SPEECH_RECOGNITION_AVAILABLE:
            msg = self.font_manager.create_message_box(
                self, QMessageBox.Icon.Warning,
                "Voice Search Not Available",
                "Voice search requires additional packages\n\npip install SpeechRecognition pyaudio"
            )
            msg.exec()
            return
        
        if self.voice_thread and self.voice_thread.isRunning():
            self.stop_voice_search()
            return
        
        try:
            self.voice_thread = VoiceSearchThread()
            self.voice_thread.speech_recognized.connect(self.on_voice_search_completed)
            self.voice_thread.speech_error.connect(self.on_voice_search_error)
            self.voice_thread.recording_started.connect(self.on_voice_recording_started)
            self.voice_thread.recording_stopped.connect(self.on_voice_recording_stopped)
            self.voice_thread.start()
        except Exception as e:
            self.on_voice_search_error(f"Failed to start voice recognition: {str(e)}")
    
    def stop_voice_search(self):
        """Stop voice recognition"""
        if self.voice_thread:
            self.voice_thread.stop_listening()
            self.voice_thread.wait(1000) # Wait up to 1 second
            if self.voice_thread.isRunning():
                self.voice_thread.terminate()
        self.on_voice_recording_stopped()
    
    def on_voice_recording_started(self):
        """Handle recording start"""
        self.voice_button.setIcon(get_icon("close"))
        self.voice_button.setStyleSheet("background-color: #ffebee; color: #f44336")
        self.voice_status_label.setText("🎤 Listening... Speak now!")
        self.voice_status_label.setStyleSheet("color: #f44336; font-weight: bold;")
    
    def on_voice_recording_stopped(self):
        """Handle recording stop"""
        self.voice_button.setIcon(get_icon("voice"))
        self.voice_button.setStyleSheet("")
        self.voice_status_label.setText("Processing speech...")
        self.voice_status_label.setStyleSheet("color: #ff9800; font-style: italic;")
        
    def on_voice_search_error(self, error_message):
        """Handle speech recognition error"""
        self.voice_status_label.setText(f"❌ {error_message}")
        self.voice_status_label.setStyleSheet("color: #f44336")
        
        # Reset status after 5 seconds
        QTimer.singleShot(5000, self.reset_voice_status)
    
    def reset_voice_status(self):
        """Reset voice status to default"""
        self.voice_status_label.setText("Ready for voice search")
        self.voice_status_label.setStyleSheet("color: #666; font-style: italic;")
    
    def on_voice_search_completed(self, recognized_text):
        """Handle completed voice search"""
        # Clean up the recognized text
        cleaned_text = recognized_text.strip().lower()
        
        # Set the text in search input
        self.search_input.setText(cleaned_text)
    
        # Update status
        self.voice_status_label.setText(f"✓ Recognized: '{recognized_text}'")
        self.voice_status_label.setStyleSheet("color: #4caf50; font-weight: bold")
        
        # Automatically perform the search
        self.search_word()
        
        # Reset status after 3 seconds
        QTimer.singleShot(3000, self.reset_voice_status)
    
    def search_word(self):
        search_term = self.search_input.text().strip()
        if not search_term:
            msg = self.font_manager.create_message_box(
                self, QMessageBox.Icon.Warning,
                "Input Error",
                "Please enter a word to search!"
            )
            msg.exec()
            return 
        
        search_direction = self.search_combo.currentText()
        
        # Determine search type
        if search_direction.startswith("English"):
            search_type = "english"
        elif search_direction.startswith("Khmer"):
            search_type = "khmer"
        else: # Smart search
            search_type = "smart"
            
        # Perform search
        results = []
        if search_type == "smart":
            # Try both English and Khmer
            results = self.db.read_word(search_term, "english")
            if not results:
                results = self.db.read_word(search_term, "khmer")
        else:
            results = self.db.read_word(search_term, search_type)
            
        # Record search in user profile
        found = len(results) > 0
        self.user_profile.record_search(search_term, search_type, found)
        
        # Update expert system with search context
        self.expert_engine.add_fact("search_term", search_term)
        self.expert_engine.add_fact("search_type", search_type)
        self.expert_engine.add_fact("not_found", not found)
        self.expert_engine.add_fact("word_length", len(search_term))
        
        # Add user profile facts
        user_facts = self.user_profile.get_user_facts()
        for key, value in user_facts.items():
            self.expert_engine.add_fact(key, value)
            
        if results:
            self.display_results(results)
            # Record word type for user modeling
            if results:
                word_type = results[0][3]
                self.user_profile.record_word_interaction(word_type)
        else:
            # Get AI powered suggestions
            suggestions = self.db.get_smart_suggestions(search_term, search_type)
            self.display_no_results_with_suggestions(search_term, search_direction, suggestions)
            
        # Get expert system recommendations
        expert_suggestions = self.expert_engine.infer()
        self.display_expert_suggestions(expert_suggestions)
        
        # Emit signal
        self.word_searched.emit(search_term, search_type, found)
    
    def display_results(self, results):
        html_content = "<h3>Translation Results:</h3>"
        for result in results:
            word_id, english, khmer, word_type = result[0], result[1], result[2], result[3]
            definition, example = result[4], result[5]
            
            html_content += f"""
               <div style="border: 1px solid #ccc; margin: 10px 0; padding: 10px; background-color: #ffffff;">
               <h4>{english.title()} <--> {khmer}</h4>
               <p><strong>Type:</strong> {word_type.title()} | <strong>ID:</strong> {word_id}</p>
               {f"<p><strong>Definition:</strong> {definition}</p>" if definition else ""}
               {f"<p><strong>Example:</strong> <em>{example}</em></p>" if example else ""}
               <p><small><em>Click 'View Details' in Dictionary Manager for AI analysis</em></small></p>
               </div>
            """
        self.results_display.setHtml(html_content)
        
    def display_no_results_with_suggestions(self, search_term, search_direction, suggestions):
        html_content = f"""
        <h3>No results found for '{search_term}'</h3>
        <p><strong>Search Details:</strong></p>
        <ul>
            <li>Search Direction: {search_direction}</li>
            <li>Search Term: {search_term}</li>
        </ul>
        """
        
        if suggestions:
            html_content += "<h4>AI Suggestions:</h4>"
            for suggestion in suggestions:
                word_id, english, khmer, word_type = suggestion[0], suggestion[1], suggestion[2], suggestion[3]
                definition = suggestion[4]
                
                html_content += f"""
                <div style="border-left: 3px solid #4caf50; padding-left: 10px; margin: 8px 0;">
                    <strong>{english} -> {khmer}</strong> ({word_type})
                    {f"<br><small>{definition}</small>" if definition else ""}
                </div>
                """
                
        html_content += """
        <p><strong>Suggestions:</strong></p>
        <ul>
            <li>Check spelling</li>
            <li>Try simpler words</li>
            <li>Try 'Find Similar' button</li>
        </ul>
        """
        
        self.results_display.setHtml(html_content)
    
    def display_expert_suggestions(self, suggestions):
        """Display expert system suggestions"""
        if not suggestions:
            return
        
        suggestion_text = " | ".join(suggestions[:2]) # Show first 2 suggestions
        self.suggestion_display.setText(f"Expert Advice: {suggestion_text}")
    
    def update_expert_suggestions(self):
        """Update expert system suggestions based on user profile"""
        user_recommendations = self.user_profile.get_recommendation()
        if user_recommendations:
            self.suggestion_display.setText(f"Personal: {' | '.join(user_recommendations[:2])}")
    
    def find_similar_words(self):
        """Find words similar to current input"""
        search_term = self.search_input.text().strip()
        if not search_term:
            msg = self.font_manager.create_message_box(
                self, QMessageBox.Icon.Warning,
                "Input Required",
                "Please enter a word to find similar words!"
            )
            msg.exec()
            return
            
        similar_words = self.db.find_similar_words(search_term, 5)
        if similar_words:
            html_content = f"<h3>Words similar to '{search_term}':</h3>"
            for word, similarity in similar_words:
                # Try to get full word data
                word_results = self.db.read_word(word, "english")
                if not word_results:
                    word_results = self.db.read_word(word, "khmer")
                    
                if word_results:
                    result = word_results[0]
                    english, khmer, word_type = result[1], result[2], result[3]
                    similarity_percent = int(similarity * 100)
                    
                    html_content += f"""
                    <div style="border: 1px solid #ddd; margin: 8px 0; padding: 10px;
                                background-color: #f9f9f9; border-radius: 5px">
                        <strong>{english} -> {khmer}</strong> ({word_type})
                        <br><small>Similarity: {similarity_percent}%</small>
                    </div>
                    """
            self.results_display.setHtml(html_content)
        else:
            self.results_display.setHtml(f"<h3>No similar words found for '{search_term}'</h3>")
    
    def show_smart_random_word(self):
        """Show random word adapted to user level"""
        user_facts = self.user_profile.get_user_facts()
        difficulty_preference = user_facts.get("user_level", "beginner")
        
        # Get random words and filter by difficulty if possible
        random_words = self.db.get_random_words(10)
        
        # Simple filtering based on word length as proxy for difficulty
        if difficulty_preference == "beginner":
            filtered_words = [w for w in random_words if len(w[1]) < 7] # Short English words
        elif difficulty_preference == "advanced":
            filtered_words = [w for w in random_words if len(w[1]) > 8] # Long English words
        else:
            filtered_words = random_words
            
        if not filtered_words:
            filtered_words = random_words
            
        if filtered_words:
            selected_word = filtered_words[0]
            self.display_results([selected_word])
            self.search_input.setText(selected_word[1]) # Set English word in input
    
    def clear_search(self):
        self.search_input.clear()
        self.results_display.clear()
        self.search_input.setFocus()
        self.update_expert_suggestions()

class DictionaryManageWidget(QWidget):
    word_added = pyqtSignal(str)
    word_updated = pyqtSignal(int)
    word_deleted = pyqtSignal(int)
    
    def __init__(self, db, font_manager, ai_generator):
        super().__init__()
        self.db = db
        self.font_manager = font_manager
        self.ai_generator = ai_generator
        self.current_edit_id = None
        self.table_model = DictionaryTableModel()
        self.init_ui()
        self.refresh_dictionary()
    
    def init_ui(self):
        # Apply font to entire widget
        self.font_manager.apply_font(self)
        layout = QVBoxLayout()
        
        # Create splitter for form and table
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Form section with QHBoxLayout
        form_widget = QWidget()
        form_layout = QVBoxLayout()
        
        form_group = QGroupBox("Add/Edit Dictionary Entry (AI-Enhanced)")
        self.font_manager.apply_font(form_group, bold=True)
        form_group.setFixedHeight(170)
        form_group_layout = QVBoxLayout()
        
        # CREATE form input using QHBoxLayout (original style)
        inputs_layout = QHBoxLayout()
        
        # English Word
        english_layout = QVBoxLayout()
        english_label = QLabel("English Word:")
        self.font_manager.apply_font(english_label)
        self.english_input = QLineEdit()
        self.english_input.setPlaceholderText("e.g., computer")
        self.font_manager.apply_font(self.english_input)
        english_layout.addWidget(english_label)
        english_layout.addWidget(self.english_input)
        
        # Khmer word
        khmer_layout = QVBoxLayout()
        khmer_label = QLabel("Khmer Word:")
        self.font_manager.apply_font(khmer_label)
        self.khmer_input = QLineEdit()
        self.khmer_input.setPlaceholderText("e.g., កំព្យូទ័រ")
        self.font_manager.apply_font(self.khmer_input)
        khmer_layout.addWidget(khmer_label)
        khmer_layout.addWidget(self.khmer_input)
        
        # Word type
        type_layout = QVBoxLayout()
        type_label = QLabel("Word Type:")
        self.font_manager.apply_font(type_label)
        self.type_combo = QComboBox()
        self.type_combo.addItems(["noun", "verb", "adjective", "adverb", "greeting", "expression", "response"])
        self.font_manager.apply_font(self.type_combo)
        type_layout.addWidget(type_label)
        type_layout.addWidget(self.type_combo)
        
        # Definition
        definition_layout = QVBoxLayout()
        definition_label = QLabel("Definition:")
        self.font_manager.apply_font(definition_label)
        self.definition_input = QLineEdit()
        self.definition_input.setPlaceholderText("Brief definition...")
        self.font_manager.apply_font(self.definition_input)
        definition_layout.addWidget(definition_label)
        definition_layout.addWidget(self.definition_input)
        
        # Example
        example_layout = QVBoxLayout()
        example_label = QLabel("Example:")
        self.font_manager.apply_font(example_label)
        self.example_input = QLineEdit()
        self.example_input.setPlaceholderText("Example sentence...")
        self.font_manager.apply_font(self.example_input)
        example_layout.addWidget(example_label)
        example_layout.addWidget(self.example_input)
        
        # Add all input groups to horizontal layout
        inputs_layout.addLayout(english_layout)
        inputs_layout.addLayout(khmer_layout)
        inputs_layout.addLayout(type_layout)
        inputs_layout.addLayout(definition_layout)
        inputs_layout.addLayout(example_layout)
        
        # CRUD operation buttons
        button_layout = QHBoxLayout()
        
        # Create button
        self.add_button = QPushButton("Create Word")
        self.add_button.setIcon(get_icon("add"))
        self.font_manager.apply_font(self.add_button)
        self.add_button.clicked.connect(self.create_word)
        self.add_button.setDefault(True)
        
        # Update button
        self.update_button = QPushButton("Update Word")
        self.update_button.setIcon(get_icon("update"))
        self.font_manager.apply_font(self.update_button)
        self.update_button.clicked.connect(self.update_word)
        self.update_button.setVisible(False)
        
        self.cancel_button = QPushButton("Cancel Edit")
        self.cancel_button.setIcon(get_icon("cancel"))
        self.font_manager.apply_font(self.cancel_button)
        self.cancel_button.clicked.connect(self.cancel_edit)
        self.cancel_button.setVisible(False)
        
        self.clear_button = QPushButton("Clear Form")
        self.clear_button.setIcon(get_icon("clear"))
        self.font_manager.apply_font(self.clear_button)
        self.clear_button.clicked.connect(self.clear_form)
        
        self.ai_assist_button = QPushButton("AI Assist")
        self.ai_assist_button.setIcon(get_icon("ai"))
        self.font_manager.apply_font(self.ai_assist_button)
        self.ai_assist_button.clicked.connect(self.ai_assist)
        
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.update_button)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addWidget(self.ai_assist_button)
        button_layout.addStretch()
        
        form_group_layout.addLayout(inputs_layout)
        form_group_layout.addLayout(button_layout)
        form_group.setLayout(form_group_layout)
        form_layout.addWidget(form_group)
        form_widget.setLayout(form_layout)
        
        # Table section for READ/UPDATE/DELETE operation
        table_widget = QWidget()
        table_layout = QVBoxLayout()
        
        table_group = QGroupBox("Dictionary Entries")
        self.font_manager.apply_font(table_group, bold=True)
        table_group_layout = QVBoxLayout()
        
        # Filter for READ operations
        filter_layout = QHBoxLayout()
        filter_label = QLabel("Filter:")
        self.font_manager.apply_font(filter_label)
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Filter entries...")
        self.font_manager.apply_font(self.filter_input)
        self.filter_input.textChanged.connect(self.filter_dictionary)
        
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setIcon(get_icon("refresh"))
        self.font_manager.apply_font(self.refresh_button)
        self.refresh_button.clicked.connect(self.refresh_dictionary)
        
        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.filter_input)
        filter_layout.addWidget(self.refresh_button)
        
        # Table view for displaying data
        self.table_view = QTableView()
        self.font_manager.apply_font(self.table_view)
        self.table_view.setModel(self.table_model)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_view.setAlternatingRowColors(True)
        
        # Configure headers
        header = self.table_view.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.font_manager.apply_font(header, bold=True)
        
        # CRUD action buttons
        table_button_layout = QHBoxLayout()
        
        # READ operation - View detail
        self.view_button = QPushButton("View Details")
        self.view_button.setIcon(get_icon("view"))
        self.font_manager.apply_font(self.view_button)
        self.view_button.clicked.connect(self.view_selected_word)
        
        # UPDATE operation - Edit
        self.edit_button = QPushButton("Edit Selected")
        self.edit_button.setIcon(get_icon("edit"))
        self.font_manager.apply_font(self.edit_button)
        self.edit_button.clicked.connect(self.edit_selected_word)
        
        # DELETE operation - Delete
        self.delete_button = QPushButton("Delete Selected")
        self.delete_button.setIcon(get_icon("delete"))
        self.font_manager.apply_font(self.delete_button)
        self.delete_button.clicked.connect(self.delete_selected_word)
        
        self.stats_label = QLabel()
        self.font_manager.apply_font(self.stats_label)
        
        table_button_layout.addWidget(self.view_button)
        table_button_layout.addWidget(self.edit_button)
        table_button_layout.addWidget(self.delete_button)
        table_button_layout.addStretch()
        table_button_layout.addWidget(self.stats_label)
        
        table_group_layout.addLayout(filter_layout)
        table_group_layout.addWidget(self.table_view)
        table_group_layout.addLayout(table_button_layout)
        table_group.setLayout(table_group_layout)
        table_layout.addWidget(table_group)
        table_widget.setLayout(table_layout)
        
        # Add to splitter
        splitter.addWidget(form_widget)
        splitter.addWidget(table_widget)
        splitter.setSizes([300, 500])
        layout.addWidget(splitter)
        self.setLayout(layout)
        
    def ai_assist(self):
        """AI assistance for filling form fields"""
        english_word = self.english_input.text().strip()
        if not english_word:
            msg = self.font_manager.create_message_box(
                self, QMessageBox.Icon.Information,
                "AI Assistant",
                "AI Tips for creating dictionary entries:\n\n" +
                "• Use clear, simple definitions\n" +
                "• Include cultural context when relevant\n" +
                "• Choose appropriate word type\n" +
                "• Use descriptive examples\n\n" +
                "Enter an English word first to get specific suggestions!"
            )
            msg.exec()
            return
        
        # Simple AI assistance based on word patterns
        suggestions = []
        
        # Word type suggestions
        if english_word.endswith('ing'):
            suggestions.append("Consider 'verb' as word type")
            self.type_combo.setCurrentText("verb")
        elif english_word.endswith('ly'):
            suggestions.append("Consider 'adverb' as word type")
            self.type_combo.setCurrentText("adverb")
        elif english_word in ['hello', 'goodbye', 'hi', 'bye']:
            suggestions.append("Consider 'greeting' as word type")
            self.type_combo.setCurrentText("greeting")
            
        if suggestions:
            suggestion_text = "\n• ".join(suggestions)
            msg = self.font_manager.create_message_box(
                self, QMessageBox.Icon.Information,
                "AI Suggestions Applied",
                f"AI has analyzed '{english_word}' and suggests:\n\n• {suggestion_text}\n\n" +
                "Review and modify as needed!"
            )
            msg.exec()
        else:
            msg = self.font_manager.create_message_box(
                self, QMessageBox.Icon.Information,
                "AI Assistant",
                f"No specific suggestions for '{english_word}', but here are general tips:\n" +
                "• Check word type carefully\n" +
                "• Consider cultural context\n" +
                "• Add helpful examples\n" +
                "• Use appropriate difficulty level"
            )
            msg.exec()
        
    def create_word(self):
        """CREATE operation - Add new word to dictionary"""
        english = self.english_input.text().strip()
        khmer = self.khmer_input.text().strip()
        word_type = self.type_combo.currentText()
        definition = self.definition_input.text().strip()
        example = self.example_input.text().strip()
        
        if not english or not khmer:
            msg = self.font_manager.create_message_box(
                self, QMessageBox.Icon.Warning,
                "Input Error",
                "Please enter both English and Khmer words!"
            )
            msg.exec()
            return 
            
        try:
            word_id = self.db.create_word(english, khmer, word_type, definition, example)
            self.clear_form()
            self.refresh_dictionary()
            self.word_added.emit(english)
            
            msg = self.font_manager.create_message_box(
                self, QMessageBox.Icon.Information,
                "Success",
                f"Word '{english}' ➡ '{khmer}' created successfully!\nWord ID: {word_id}"
            )
            msg.exec()
            
        except ValueError as e:
            msg = self.font_manager.create_message_box(
                self, QMessageBox.Icon.Warning,
                "Error",
                str(e)
            )
            msg.exec()
    
    def view_selected_word(self):
        """READ operation - View detailed information about selected word"""
        selection = self.table_view.selectionModel().selectedRows()
        if not selection:
            msg = self.font_manager.create_message_box(
                self, QMessageBox.Icon.Warning,
                "No Selection",
                "Please select a word to view details!"
            )
            msg.exec()
            return
            
        row = selection[0].row()
        word_data = self.table_model.get_row_data(row)
        if word_data:
            dialog = WordDetailsDialog(word_data, self.font_manager, self.ai_generator, self)
            dialog.exec()
    
    def update_word(self):
        """UPDATE operation - Modify existing word"""
        if self.current_edit_id is None:
            return

    # Get inputs
        english = self.english_input.text().strip()
        khmer = self.khmer_input.text().strip()
        word_type = self.type_combo.currentText().strip()
        definition = self.definition_input.text().strip()
        example = self.example_input.text().strip()

        # Validation
        if not english or not khmer:
            msg = self.font_manager.create_message_box(
                self, QMessageBox.Icon.Warning,
                "Input Error",
                "Please enter both English and Khmer words!"
            )
            msg.exec()
            return

        try:
            # Update DB
            self.db.update_word(
                self.current_edit_id,
                english,
                khmer,
                word_type,
                definition,
                example
            )

            # Refresh UI
            self.cancel_edit()
            self.refresh_dictionary()
            self.word_updated.emit(self.current_edit_id)

            # Success message
            msg = self.font_manager.create_message_box(
                self, QMessageBox.Icon.Information,
                "Success",
                f"Word updated successfully!\nNew values:\nEnglish: {english}\nKhmer: {khmer}"
            )
            msg.exec()

        except Exception as e:  # catch all DB-related errors
            msg = self.font_manager.create_message_box(
                self, QMessageBox.Icon.Critical,
                "Update Error",
                f"Failed to update word.\nError: {str(e)}"
            )
            msg.exec()

    
    def edit_selected_word(self):
        """Prepare UPDATE operation - Load selected word into form for editing"""
        selection = self.table_view.selectionModel().selectedRows()
        if not selection:
            msg = self.font_manager.create_message_box(
                self, QMessageBox.Icon.Warning,
                "No Selection",
                "Please select a word to edit!"
            )
            msg.exec()
            return
            
        row = selection[0].row()
        word_data = self.table_model.get_row_data(row)
        if word_data:
            word_id, english, khmer, word_type, definition, example = word_data[:6]
            self.current_edit_id = word_id
            self.english_input.setText(english)
            self.khmer_input.setText(khmer)
            self.type_combo.setCurrentText(word_type)
            self.definition_input.setText(definition or "")
            self.example_input.setText(example or "")
            
            # Switch to update mode
            self.add_button.setVisible(False)
            self.update_button.setVisible(True)
            self.cancel_button.setVisible(True)
            
            # Focus on first input
            self.english_input.setFocus()
    
    def delete_selected_word(self):
        """DELETE operation - Remove selected word from dictionary"""
        selection = self.table_view.selectionModel().selectedRows()
        if not selection:
            msg = self.font_manager.create_message_box(
                self, QMessageBox.Icon.Warning,
                "No Selection",
                "Please select a word to delete"
            )
            msg.exec()
            return
            
        row = selection[0].row()
        word_data = self.table_model.get_row_data(row)
        if word_data:
            word_id, english, khmer = word_data[0], word_data[1], word_data[2]
            
            msg = self.font_manager.create_message_box(
                self, QMessageBox.Icon.Warning,
                "Confirm Delete",
                f"Are you sure you want to delete this word?\n\n'{english}' ➡ '{khmer}'\n\nThis action cannot be undone",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if msg.exec() == QMessageBox.StandardButton.Yes:
                try:
                    if self.db.delete_word(word_id):
                        self.refresh_dictionary()
                        self.word_deleted.emit(word_id)
                        
                        success_msg = self.font_manager.create_message_box(
                            self, QMessageBox.Icon.Information,
                            "Deleted",
                            f"Word '{english} ➡ {khmer}' deleted successfully!"
                        )
                        success_msg.exec()
                    else:
                        error_msg = self.font_manager.create_message_box(
                            self, QMessageBox.Icon.Warning,
                            "Delete Failed",
                            f"Failed to delete word '{english} ➡ {khmer}'"
                        )
                        error_msg.exec()
                except ValueError as e:
                    error_msg = self.font_manager.create_message_box(
                        self, QMessageBox.Icon.Critical,
                        "Delete Error",
                        str(e)
                    )
                    error_msg.exec()
    
    def refresh_dictionary(self):
        """Refresh the table view with current database data"""
        words = self.db.read_all_words()
        self.table_model.update_data(words)
        self.stats_label.setText(f"Total entries: {len(words)}")
    
    def filter_dictionary(self):
        """Filter dictionary entries based on search text"""
        filter_text = self.filter_input.text().strip().lower()

        if not filter_text:
            self.refresh_dictionary()
            return

        words = self.db.read_all_words()
        filtered_words = []
        for word in words:
            word_id, english, khmer, word_type, definition, example = word[:6]

            if (filter_text in english.lower() or 
                filter_text in khmer or
                filter_text in word_type.lower() or 
                filter_text in (definition or "").lower()):
                filtered_words.append(word)

        self.table_model.update_data(filtered_words)
        self.stats_label.setText(f"Showing {len(filtered_words)} of {len(words)} entries")
    
    def cancel_edit(self):
        """Cancel edit mode and return to create mode"""
        self.current_edit_id = None
        self.clear_form()
        # Switch back to creation
        self.add_button.setVisible(True)
        self.update_button.setVisible(False)
        self.cancel_button.setVisible(False)
    
    def clear_form(self):
        """Clear all form inputs"""
        self.english_input.clear()
        self.khmer_input.clear()
        self.type_combo.setCurrentIndex(0)
        self.definition_input.clear()
        self.example_input.clear()
        self.english_input.setFocus()

class StatisticsWidget(QWidget):
    def __init__(self, db, font_manager, user_profile):
        super().__init__()
        self.db = db
        self.font_manager = font_manager
        self.user_profile = user_profile
        self.search_count = 0
        self.init_ui()
        self.update_stats()
        
    def init_ui(self):
        # Apply font to entire widget
        self.font_manager.apply_font(self)
        layout = QVBoxLayout()
        
        # Statistics section with scroll
        stats_group = QGroupBox("Dictionary Statistics (AI-Enhanced)")
        self.font_manager.apply_font(stats_group, bold=True)
        stats_layout = QVBoxLayout()
        
        stats_scroll = QScrollArea()
        stats_content = QWidget()
        stats_content_layout = QVBoxLayout()
        
        self.total_words_label = QLabel()
        self.font_manager.apply_font(self.total_words_label)
        
        self.word_types_label = QLabel()
        self.font_manager.apply_font(self.word_types_label)
        self.word_types_label.setWordWrap(True)
        
        self.user_stats_label = QLabel()
        self.font_manager.apply_font(self.user_stats_label)
        self.user_stats_label.setWordWrap(True)
        
        self.searches_label = QLabel()
        self.font_manager.apply_font(self.searches_label)
        
        stats_content_layout.addWidget(self.total_words_label)
        stats_content_layout.addWidget(self.word_types_label)
        stats_content_layout.addWidget(self.user_stats_label)
        stats_content_layout.addWidget(self.searches_label)
        
        stats_content.setLayout(stats_content_layout)
        stats_scroll.setWidget(stats_content)
        stats_scroll.setWidgetResizable(True)
        stats_scroll.setMaximumHeight(150)
        stats_layout.addWidget(stats_scroll)
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        # AI insights section with scroll
        insight_group = QGroupBox("AI Learning Insights")
        insight_group.setFixedHeight(180)
        self.font_manager.apply_font(insight_group, bold=True)
        insight_layout = QVBoxLayout()
        
        insight_scroll = QScrollArea()
        self.insights_display = QTextBrowser()
        self.font_manager.apply_font(self.insights_display)
        
        insight_scroll.setWidget(self.insights_display)
        insight_scroll.setWidgetResizable(True)
        insight_layout.addWidget(insight_scroll)
        insight_group.setLayout(insight_layout)
        layout.addWidget(insight_group)
        
        # Sample words with Scroll
        sample_group = QGroupBox("Sample Khmer Words")
        sample_group.setFixedHeight(280)
        self.font_manager.apply_font(sample_group, bold=True)
        sample_layout = QVBoxLayout()
        
        sample_scroll = QScrollArea()
        self.sample_display = QTextBrowser()
        self.font_manager.apply_font(self.sample_display)
        
        sample_scroll.setWidget(self.sample_display)
        sample_scroll.setWidgetResizable(True)
        sample_layout.addWidget(sample_scroll)
        sample_group.setLayout(sample_layout)
        layout.addWidget(sample_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        update_btn = QPushButton("Update Statistics")
        update_btn.setIcon(get_icon("refresh"))
        self.font_manager.apply_font(update_btn)
        update_btn.clicked.connect(self.update_stats)
        
        export_btn = QPushButton("Export Data")
        export_btn.setIcon(get_icon("export"))
        self.font_manager.apply_font(export_btn)
        export_btn.clicked.connect(self.export_data)
        export_btn.setToolTip("Export dictionary data, analytics, and user profile in multiple formats (CSV, JSON, TXT, HTML)")
        
        reset_btn = QPushButton("Reset Profile")
        reset_btn.setIcon(get_icon("reset"))
        self.font_manager.apply_font(reset_btn)
        reset_btn.clicked.connect(self.reset_profile)
        
        button_layout.addWidget(update_btn)
        button_layout.addWidget(export_btn)
        button_layout.addWidget(reset_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        layout.addStretch()
        self.setLayout(layout)
    
    def update_stats(self):
        """Update enhanced statistics with AI insights"""
        words = self.db.read_all_words()
        
        # Basic statistics
        total_words = len(words)
        self.total_words_label.setText(f"Total Dictionary Entries: {total_words}")
        
        # Word type analysis
        type_counts = {}
        for word in words:
            word_type = word[3]
            type_counts[word_type] = type_counts.get(word_type, 0) + 1
        type_text = "Word Types: " + ", ".join([f"{t}: {c}" for t, c in type_counts.items()])
        self.word_types_label.setText(type_text)
        
        # User profile statistics
        user_facts = self.user_profile.get_user_facts()
        user_text = (f"Your Profile: Level: {user_facts.get('user_level', 'Unknown').title()}, "
                     f"Searches: {user_facts.get('search_count', 0)}, "
                     f"Session Time: {user_facts.get('session_time', 0)}s")
        self.user_stats_label.setText(user_text)
        self.searches_label.setText(f"Searches This Session: {self.search_count}")
        
        # Generate AI insights
        self.generate_ai_insights(words, user_facts)
        
        # Display sample words with khmer font
        self.display_samples(words)
    
    def generate_ai_insights(self, words, user_facts):
        """Generate AI-powered learning insights"""
        insights = []
        
        # Analyze user progress
        user_level = user_facts.get('user_level', 'beginner')
        search_count = user_facts.get('search_count', 0)
        
        if search_count < 5:
            insights.append("<strong>Getting Started:</strong> You're beginning your Khmer learning journey! Focus on basic vocabulary first.")
        elif search_count < 20:
            insights.append("<strong>Building Momentum:</strong> Good progress! Try exploring different word types to expand your vocabulary.")
        else:
            insights.append("<strong>Advanced Learner:</strong> Excellent dedication! Consider focusing on cultural context and grammar.")
        
        # Learning recommendations
        recommendations = []
        if user_level == "beginner":
            recommendations.append("Focus on daily vocabulary (food, family, greetings)")
            recommendations.append("Practice simple sentence structures")
        elif user_level == "intermediate":
            recommendations.append("Explore word relationships and synonyms")
            recommendations.append("Study cultural context and formal speech")
        else:
            recommendations.append("Master complex grammar patterns")
            recommendations.append("Study literature and advanced expressions")
        
        # Combine insights and recommendations
        html_content = "<h4>Your Learning Insights:</h4><ul>"
        for insight in insights:
            html_content += f"<li>{insight}</li>"
        html_content += "</ul><h4>AI Recommendations:</h4><ul>"
        for rec in recommendations:
            html_content += f"<li>{rec}</li>"
        html_content += "</ul>"
        
        self.insights_display.setHtml(html_content)
        
    def display_samples(self, words):
        """Display sample words"""
        import random
        sample_words = random.sample(words, min(8, len(words)))
        html_content = "<h4>Sample Words:</h4>"
        for word in sample_words:
            english, khmer, word_type = word[1], word[2], word[3]
            html_content += f"<p><strong>{english}</strong> -> {khmer} ({word_type})</p>"
        self.sample_display.setHtml(html_content)
    
    def export_data(self):
        """Export data with comprehensive options"""
        try:
            print("Starting export process...")
            
            # Show export options dialog
            export_dialog = ExpertDialog(self.font_manager, self)
            if export_dialog.exec() != QDialog.DialogCode.Accepted:
                print("Export dialog cancelled by user")
                return
            
            # Get export settings
            formats, data_types, options = export_dialog.get_export_settings()
            print(f"Selected formats: {formats}")
            print(f"Selected data types: {data_types}")
            print(f"Options: {options}")
            
            if not formats or not data_types:
                msg = self.font_manager.create_message_box(
                    self, QMessageBox.Icon.Warning,
                    "Export Error",
                    "Please select at least one format and one data type to export"
                )
                msg.exec()
                return
                
            # Choose save location
            base_filename, _ = QFileDialog.getSaveFileName(
                self,
                "Export Dictionary Data",
                f"khmer_dictionary_export_{datetime.now().strftime('%Y%m%d')}",
                "All Files (*)"
            )
            
            if not base_filename:
                print("No save location selected")
                return
                
            # Remove extension if provided
            base_filename = str(Path(base_filename).with_suffix(''))
            print(f"Base filename: {base_filename}")
            
            # Create exporter and export data
            exporter = DataExporter(self.db, self.user_profile, self.font_manager)
            
            # Show progress dialog
            progress_msg = QMessageBox(self)
            progress_msg.setWindowTitle("Exporting Data")
            progress_msg.setText("Exporting data, please wait...")
            progress_msg.setStandardButtons(QMessageBox.StandardButton.NoButton)
            progress_msg.show()
            QApplication.processEvents()
            
            try:
                # Perform export
                results = exporter.export_data(formats, data_types, options, base_filename)
                progress_msg.close()
                
                print(f"Export results: {results}")
                
                # Show results
                success_files = [filename for filename, success in results if success]
                failed_files = [filename for filename, success in results if not success]
                
                result_text = f"Export completed\n\n"
                if success_files:
                    result_text += f"✅ Successfully exported {len(success_files)} files:\n"
                    for filename in success_files:
                        result_text += f"▪️ {Path(filename).name}\n"
                    result_text += "\n"
                if failed_files:
                    result_text += f"❌ Failed to export {len(failed_files)} files:\n"
                    for filename in failed_files:
                        result_text += f"▪️ {filename}\n"
                    result_text += "\n"
                result_text += f"🗂️ Files saved to: {Path(base_filename).parent}\n\n"
                
                # Add export summary
                result_text += "📊 Export Summary:\n"
                result_text += f"🔹 Formats: {', '.join(formats).upper()}\n"
                result_text += f"🔹 Data Types: {', '.join(data_types).title()}\n"
                result_text += f"🔹 Include Timestamps: {options.get('include_timestamps', False)}\n"
                result_text += f"🔹 Include Metadata: {options.get('include_metadata', False)}\n"
                
                icon = QMessageBox.Icon.Information if success_files else QMessageBox.Icon.Warning
                msg = self.font_manager.create_message_box(
                    self, icon,
                    "Export Complete" if success_files else "Export Failed",
                    result_text
                )
                msg.exec()
                
            except Exception as export_error:
                progress_msg.close()
                print(f"Export error: {str(export_error)}")
                error_msg = self.font_manager.create_message_box(
                    self, QMessageBox.Icon.Critical,
                    "Export Error",
                    f"An error occurred during export:\n\n{str(export_error)}\n\nPlease try again or check file permissions"
                )
                error_msg.exec()
                
        except Exception as e:
            print(f"Fatal error in export_data: {str(e)}")
            import traceback
            traceback.print_exc()
            
            error_msg = self.font_manager.create_message_box(
                self, QMessageBox.Icon.Critical,
                "Export Error",
                f"An error occurred during export:\n\n{str(e)}\n\nPlease try again or check file permissions"
            )
            error_msg.exec()
    
    def reset_profile(self):
        """Reset user profile"""
        msg = self.font_manager.create_message_box(
            self, QMessageBox.Icon.Question,
            "Reset Profile",
            "Reset your learning profile?\n\nThis will clear search history and preferences.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if msg.exec() == QMessageBox.StandardButton.Yes:
            # Reset profile data
            self.user_profile.profile = {
                "search_history": [],
                "word_preferences": defaultdict(int),
                "language_preference": "english",
                "difficulty_level": "beginner",
                "search_count": 0,
                "session_time": 0,
                "favorite_word_types": defaultdict(int),
                "error_patterns": [],
                "learning_progress": {"beginner": 0, "intermediate": 0, "advanced": 0},
                "last_active": datetime.now().isoformat()
            }
            self.user_profile.save_profile()
            self.search_count = 0
            self.update_stats()
    
    def increment_search_count(self):
        self.search_count += 1
        self.searches_label.setText(f"Searches This Session: {self.search_count}")

class KhmerEnglishDictionaryApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = DictionaryDatabase()
        self.font_manager = FontManager()
        self.expert_engine = ExpertSystemEngine()
        self.user_profile = UserProfileManager()
        self.ai_generator = AIExplanationGenerator()
        self.dark_mode = False
        self.init_ui()
        self.connect_signals()
    
    def init_ui(self):
        # Apply font to entire application
        self.font_manager.apply_font(self)
        self.setWindowTitle("Khmer-English Dictionary វចនានុក្រមអង់គ្លេស-ខ្មែរ")
        self.setGeometry(100, 100, 1200, 800)
        
        # Set window icon
        self.setWindowIcon(get_icon("app"))
        
        # Create menu bar
        self.create_menu_bar()
        
        # Use standard Qt styling with Khmer font
        self.setStyleSheet(self.get_light_stylesheet())
        
        centralwidget = QWidget()
        self.font_manager.apply_font(centralwidget)
        self.setCentralWidget(centralwidget)
        layout = QVBoxLayout()
        centralwidget.setLayout(layout)
        
        self.tab_widget = QTabWidget()
        self.font_manager.apply_font(self.tab_widget)
        
        # Create enhanced tabs with expert system features but standard UI
        self.translator_tab = TranslatorWidget(self.db, self.font_manager,
                                               self.expert_engine, self.user_profile,
                                               self.ai_generator)
        self.manager_tab = DictionaryManageWidget(self.db, self.font_manager,
                                                  self.ai_generator)
        self.stats_tab = StatisticsWidget(self.db, self.font_manager,
                                          self.user_profile)
        
        self.tab_widget.addTab(self.translator_tab, "Translator")
        self.tab_widget.addTab(self.manager_tab, "Dictionary Manager")
        self.tab_widget.addTab(self.stats_tab, "Statistics")
        layout.addWidget(self.tab_widget)
    
        # Status bar with khmer font
        status_bar = self.statusBar()
        self.font_manager.apply_font(status_bar)
        status_bar.showMessage("Ready - Expert system + Voice search active - សូមស្វាគមន៍មកកាន់វចនានុក្រម (Welcome to the Dictionary)")
        
        # Focus on the first tab
        self.tab_widget.setCurrentIndex(0)
    
    def create_menu_bar(self):
        """Create the menu bar with theme toggle"""
        menubar = self.menuBar()
        
        # View menu
        view_menu = menubar.addMenu("View")
        
        # Theme toggle action
        self.theme_action = QAction("Toggle Dark Mode", self)
        self.theme_action.setIcon(get_icon("theme"))
        self.theme_action.setCheckable(True)
        self.theme_action.setChecked(False)
        self.theme_action.triggered.connect(self.toggle_dark_mode)
        view_menu.addAction(self.theme_action)
    
    def get_light_stylesheet(self):
        """Get the light mode stylesheet"""
        return f"""
            QMainWindow {{
                background-color: white;
                color: black;
                font-family: '{self.font_manager.get_font_family()}';
                font-size: {self.font_manager.font_size}pt;
            }}
            QTableWidget::pane {{
                border: 1px solid #cccccc;
                background-color: white;
                color: black;
                font-family: '{self.font_manager.get_font_family()}';
                font-size: {self.font_manager.font_size}pt;
            }}
            QTabBar::tab {{
                background-color: #f0f0f0;
                color: black;
                padding: 8px 16px;
                margin-right: 2px;
                font-family: '{self.font_manager.get_font_family()}';
                font-size: {self.font_manager.font_size}pt;
            }}
            QTabBar::tab:selected {{
                background-color: white;
                border-bottom: 2px solid #333333;
                color: black;
            }}
            QGroupBox {{
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 1px;
                padding-top: 10px;
                color: black;
                font-family: '{self.font_manager.get_font_family()}';
                font-size: {self.font_manager.font_size}pt;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: black;
                font-family: '{self.font_manager.get_font_family()}';
                font-size: {self.font_manager.font_size}pt;
            }}
            QLineEdit, QComboBox, QPushButton, QTextEdit, QTextBrowser {{
                font-family: '{self.font_manager.get_font_family()}';
                font-size: {self.font_manager.font_size}pt;
                padding: 5px;
                color: black;
            }}
            QLineEdit, QTextEdit, QTextBrowser {{
                background-color: white;
                border: 1px solid #cccccc;
            }}
            QComboBox {{
                background-color: white;
                border: 1px solid #cccccc;
            }}
            QPushButton {{
                background-color: #1976D2;  /* Blue color for buttons */
                color: white;
                min-width: 100px;
                min-height: 30px;
                border: none;
                border-radius: 3px;
            }}
            QPushButton:hover {{
                background-color: #1565C0;
            }}
            QPushButton:pressed {{
                background-color: #0D47A1;
            }}
            QTableView {{
                font-family: '{self.font_manager.get_font_family()}';
                font-size: {self.font_manager.font_size}pt;
                gridline-color: #e0e0e0;
                background-color: white;
                alternate-background-color: #f9f9f9;
                color: black;
            }}
            QHeaderView::section {{
                background-color: #f0f0f0;
                padding: 8px;
                border: 1px solid #cccccc;
                font-family: '{self.font_manager.get_font_family()}';
                font-size: {self.font_manager.font_size}pt;
                font-weight: bold;
                color: black;
            }}
            QLabel {{
                font-family: '{self.font_manager.get_font_family()}';
                font-size: {self.font_manager.font_size}pt;
                color: black;
            }}
            QScrollArea {{
                border: 1px solid #cccccc;
                border-radius: 3px;
                background-color: white;
            }}
            QCheckBox {{
                color: black;
                font-family: '{self.font_manager.get_font_family()}';
                font-size: {self.font_manager.font_size}pt;
            }}
            QDialogButtonBox QPushButton {{
                min-width: 80px;
            }}
            QMenuBar {{
                background-color: #f0f0f0;
                color: black;
                font-family: '{self.font_manager.get_font_family()}';
                font-size: {self.font_manager.font_size}pt;
            }}
            QMenu {{
                background-color: white;
                color: black;
                font-family: '{self.font_manager.get_font_family()}';
                font-size: {self.font_manager.font_size}pt;
            }}
            QMenu::item:selected {{
                background-color: #1976D2;
                color: white;
            }}
        """
    
    def get_dark_stylesheet(self):
        """Get the dark mode stylesheet"""
        return f"""
            QMainWindow {{
                background-color: #2b2b2b;
                color: #f0f0f0;
                font-family: '{self.font_manager.get_font_family()}';
                font-size: {self.font_manager.font_size}pt;
            }}
            QTableWidget::pane {{
                border: 1px solid #555555;
                background-color: #2b2b2b;
                color: #f0f0f0;
                font-family: '{self.font_manager.get_font_family()}';
                font-size: {self.font_manager.font_size}pt;
            }}
            QTabBar::tab {{
                background-color: #3c3c3c;
                color: #f0f0f0;
                padding: 8px 16px;
                margin-right: 2px;
                font-family: '{self.font_manager.get_font_family()}';
                font-size: {self.font_manager.font_size}pt;
            }}
            QTabBar::tab:selected {{
                background-color: #2b2b2b;
                border-bottom: 2px solid #4fc3f7;
                color: #f0f0f0;
            }}
            QGroupBox {{
                font-weight: bold;
                border: 2px solid #555555;
                border-radius: 5px;
                margin-top: 1px;
                padding-top: 10px;
                color: #e65b25;
                font-family: '{self.font_manager.get_font_family()}';
                font-size: {self.font_manager.font_size}pt;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #f0f0f0;
                font-family: '{self.font_manager.get_font_family()}';
                font-size: {self.font_manager.font_size}pt;
            }}
            QLineEdit, QComboBox, QPushButton, QTextEdit, QTextBrowser {{
                font-family: '{self.font_manager.get_font_family()}';
                font-size: {self.font_manager.font_size}pt;
                padding: 5px;
                color: #e65b25;
            }}
            QLineEdit, QTextEdit, QTextBrowser {{
                background-color: #3c3c3c;
                border: 1px solid #555555;
            }}
            QComboBox {{
                background-color: #3c3c3c;
                border: 1px solid #555555;
            }}
            QPushButton {{
                background-color: #1976D2;  /* Blue color for buttons */
                color: white;
                min-width: 100px;
                min-height: 30px;
                border: none;
                border-radius: 3px;
            }}
            QPushButton:hover {{
                background-color: #1565C0;
            }}
            QPushButton:pressed {{
                background-color: #0D47A1;
            }}
            QTableView {{
                font-family: '{self.font_manager.get_font_family()}';
                font-size: {self.font_manager.font_size}pt;
                gridline-color: #555555;
                background-color: #e65b25;
                alternate-background-color: #333333;
                color: #f0f0f0;
            }}
            QHeaderView::section {{
                background-color: #3c3c3c;
                padding: 8px;
                border: 1px solid #555555;
                font-family: '{self.font_manager.get_font_family()}';
                font-size: {self.font_manager.font_size}pt;
                font-weight: bold;
                color: #f0f0f0;
            }}
            QLabel {{
                font-family: '{self.font_manager.get_font_family()}';
                font-size: {self.font_manager.font_size}pt;
                color: #f0f0f0;
            }}
            QScrollArea {{
                border: 1px solid #555555;
                border-radius: 3px;
                background-color: #2b2b2b;
            }}
            QCheckBox {{
                color: #f0f0f0;
                font-family: '{self.font_manager.get_font_family()}';
                font-size: {self.font_manager.font_size}pt;
            }}
            QDialogButtonBox QPushButton {{
                min-width: 80px;
            }}
            QMenuBar {{
                background-color: #3c3c3c;
                color: #f0f0f0;
                font-family: '{self.font_manager.get_font_family()}';
                font-size: {self.font_manager.font_size}pt;
            }}
            QMenu {{
                background-color: #3c3c3c;
                color: #f0f0f0;
                font-family: '{self.font_manager.get_font_family()}';
                font-size: {self.font_manager.font_size}pt;
            }}
            QMenu::item:selected {{
                background-color: #1976D2;
                color: white;
            }}
        """
    
    def toggle_dark_mode(self):
        """Toggle between light and dark mode"""
        self.dark_mode = not self.dark_mode
        self.theme_action.setChecked(self.dark_mode)
        
        if self.dark_mode:
            self.setStyleSheet(self.get_dark_stylesheet())
            self.statusBar().showMessage("Dark mode enabled - របៀបងងឹតបានបើក")
        else:
            self.setStyleSheet(self.get_light_stylesheet())
            self.statusBar().showMessage("Light mode enabled - របៀបពន្លឺបានបើក")
    
    def connect_signals(self):
        """Connect signals between widgets"""
        self.translator_tab.word_searched.connect(
            lambda word, search_type, found: [
                self.stats_tab.increment_search_count(),
                self.statusBar().showMessage(f"Searched: {word} ({'Found' if found else 'Not found'})")
            ]
        )
        
        self.manager_tab.word_added.connect(
            lambda word: [
                self.statusBar().showMessage(f"✔️ Created word: {word}"),
                self.stats_tab.update_stats()
            ]
        )
        
        self.manager_tab.word_updated.connect(
            lambda word_id: [
                self.statusBar().showMessage(f"✔️ Updated word ID: {word_id}"),
                self.stats_tab.update_stats()
            ]
        )
        
        self.manager_tab.word_deleted.connect(
            lambda word_id: [
                self.statusBar().showMessage(f"✔️ Deleted word ID: {word_id}"),
                self.stats_tab.update_stats()
            ]
        )
    
    def closeEvent(self, event):
        """Save user profile when application closes"""
        self.user_profile.save_profile()
        event.accept()

def main():
    app = QApplication(sys.argv)
    
    # Create font manager and set application font
    font_manager = FontManager()
    app.setFont(font_manager.get_font())
    app.setApplicationName("Expert System Khmer-English Dictionary with Voice Search")
    app.setApplicationVersion("2.1 - AI Enhanced + Voice + Dark Mode")
    app.setOrganizationName("AI Learning Tools")
    
    try:
        window = KhmerEnglishDictionaryApp()
        window.show()
        window.showMaximized()
        sys.exit(app.exec())
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        import traceback
        traceback.print_exc()
        
        # Show error dialog
        try:
            error_msg = QMessageBox()
            error_msg.setIcon(QMessageBox.Icon.Critical)
            error_msg.setWindowTitle("Application Error")
            error_msg.setText(f"An error occurred while starting the application:\n\n{str(e)}")
            error_msg.setDetailedText(traceback.format_exc())
            error_msg.exec()
        except:
            pass
        sys.exit(1)

if __name__ == "__main__":
    main()