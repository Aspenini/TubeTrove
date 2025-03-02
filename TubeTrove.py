import sys
import os
import json
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QPushButton, QLineEdit, QTabWidget, QGridLayout, 
                            QLabel, QFrame, QComboBox, QHBoxLayout, QMenuBar, QStatusBar)
from PyQt6.QtGui import QPixmap, QClipboard, QAction
from PyQt6.QtCore import Qt, QSize, QPropertyAnimation, QMutex
import yt_dlp
import ffmpeg
from pathlib import Path
import threading
import shutil

mutex = QMutex()

class DownloadTile(QWidget):
    def __init__(self, title, thumbnail_path, file_path, parent=None):
        super().__init__(parent)
        self.setFixedSize(150, 180)
        self.title = title
        self.file_path = file_path
        
        self.frame = QFrame(self)
        self.frame.setGeometry(0, 0, 150, 180)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.thumbnail = QLabel(self.frame)
        pixmap = QPixmap(thumbnail_path).scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatio,
                                              Qt.TransformationMode.SmoothTransformation)
        self.thumbnail.setPixmap(pixmap)
        self.thumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.title_label = QLabel(title, self.frame)
        self.title_label.setWordWrap(True)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(self.thumbnail)
        layout.addWidget(self.title_label)
        self.setLayout(layout)
        
        self.hover_anim = QPropertyAnimation(self.frame, b"geometry")
        self.hover_anim.setDuration(200)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            os.startfile(self.file_path)
        
    def enterEvent(self, event):
        self.hover_anim.setStartValue(self.frame.geometry())
        self.hover_anim.setEndValue(self.frame.geometry().adjusted(-5, -5, 5, 5))
        self.hover_anim.start()
        
    def leaveEvent(self, event):
        self.hover_anim.setStartValue(self.frame.geometry())
        self.hover_anim.setEndValue(self.frame.geometry().adjusted(5, 5, -5, -5))
        self.hover_anim.start()

class YouTubeDownloader(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube Downloader")
        self.setGeometry(100, 100, 800, 600)
        
        # Load settings
        self.config_file = Path("config.json")
        self.load_settings()
        
        # Themes
        self.themes = {
            "Dark Blue": """
                QMainWindow { background-color: #1e1e2f; }
                QLineEdit { 
                    background-color: #2a2a3e; 
                    border: 1px solid #3b3b54; 
                    border-radius: 10px; 
                    padding: 5px; 
                    font-size: 14px; 
                    color: #ffffff; 
                }
                QPushButton { 
                    background-color: #007bff; 
                    color: white; 
                    border: none; 
                    border-radius: 10px; 
                    padding: 8px; 
                    font-size: 14px; 
                }
                QPushButton:hover { background-color: #0056b3; }
                QComboBox { 
                    background-color: #2a2a3e; 
                    border: 1px solid #3b3b54; 
                    border-radius: 10px; 
                    padding: 5px; 
                    font-size: 14px; 
                    color: #ffffff; 
                }
                QTabWidget::pane { border: none; }
                QTabBar::tab { 
                    background-color: #2a2a3e; 
                    border-radius: 10px; 
                    padding: 8px 16px; 
                    margin-right: 5px; 
                    color: #ffffff; 
                }
                QTabBar::tab:selected { 
                    background-color: #007bff; 
                    color: white; 
                }
                QFrame { 
                    background-color: #2a2a3e; 
                    border-radius: 15px; 
                }
                QLabel { color: #ffffff; font-size: 12px; }
                QStatusBar { 
                    background-color: #2a2a3e; 
                    color: #ffffff; 
                    font-size: 12px; 
                }
            """,
            "Light": """
                QMainWindow { background-color: #ffffff; }
                QLineEdit { 
                    border: 1px solid #ddd; 
                    border-radius: 10px; 
                    padding: 5px; 
                    font-size: 14px; 
                    color: #333; 
                }
                QPushButton { 
                    background-color: #007bff; 
                    color: white; 
                    border: none; 
                    border-radius: 10px; 
                    padding: 8px; 
                    font-size: 14px; 
                }
                QPushButton:hover { background-color: #0056b3; }
                QComboBox { 
                    border: 1px solid #ddd; 
                    border-radius: 10px; 
                    padding: 5px; 
                    font-size: 14px; 
                    color: #333; 
                }
                QTabWidget::pane { border: none; }
                QTabBar::tab { 
                    background-color: #f0f0f0; 
                    border-radius: 10px; 
                    padding: 8px 16px; 
                    margin-right: 5px; 
                    color: #333; 
                }
                QTabBar::tab:selected { 
                    background-color: #007bff; 
                    color: white; 
                }
                QFrame { 
                    background-color: #f0f0f0; 
                    border-radius: 15px; 
                }
                QLabel { color: #333; font-size: 12px; }
                QStatusBar { 
                    background-color: #f0f0f0; 
                    color: #333; 
                    font-size: 12px; 
                }
            """
        }
        self.setStyleSheet(self.themes[self.settings.get("theme", "Dark Blue")])
        
        # Menu bar
        menu_bar = QMenuBar(self)
        self.setMenuBar(menu_bar)
        settings_menu = menu_bar.addMenu("Settings")
        
        theme_menu = settings_menu.addMenu("Theme")
        for theme_name in self.themes.keys():
            action = QAction(theme_name, self)
            action.triggered.connect(lambda checked, t=theme_name: self.change_theme(t))
            theme_menu.addAction(action)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        input_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter YouTube URL or paste from clipboard...")
        self.type_selector = QComboBox()
        self.type_selector.addItems(["Video", "Audio"])
        self.type_selector.currentTextChanged.connect(self.update_format_selector)
        self.format_selector = QComboBox()
        self.update_format_selector("Video")
        self.paste_button = QPushButton("Paste & Download")
        self.paste_button.clicked.connect(self.download_content)
        
        input_layout.addWidget(self.url_input)
        input_layout.addWidget(self.type_selector)
        input_layout.addWidget(self.format_selector)
        input_layout.addWidget(self.paste_button)
        layout.addLayout(input_layout)
        
        self.tabs = QTabWidget()
        self.videos_tab = QWidget()
        self.music_tab = QWidget()
        
        self.tabs.addTab(self.videos_tab, "Videos")
        self.tabs.addTab(self.music_tab, "Music")
        
        self.video_grid = QGridLayout(self.videos_tab)
        self.music_grid = QGridLayout(self.music_tab)
        
        layout.addWidget(self.tabs)
        
        self.video_dir = Path("videos")
        self.music_dir = Path("music")
        self.thumbnail_dir = Path("thumbnails")
        self.cover_dir = Path("covers")
        self.ffmpeg_dir = Path("ffmpeg")
        
        for directory in [self.video_dir, self.music_dir, self.thumbnail_dir, self.cover_dir, self.ffmpeg_dir]:
            directory.mkdir(exist_ok=True)
        # Clean up any stray .webp files in videos/music folders
        for file in self.video_dir.glob("*.webp"):
            file.unlink()
        for file in self.music_dir.glob("*.webp"):
            file.unlink()
        
        self.grid_positions = {
            "videos": {"row": 0, "col": 0},
            "music": {"row": 0, "col": 0}
        }
        
        self.refresh_display()

    def load_settings(self):
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                self.settings = json.load(f)
        else:
            self.settings = {"theme": "Dark Blue"}
            self.save_settings()

    def save_settings(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.settings, f)

    def change_theme(self, theme_name):
        self.settings["theme"] = theme_name
        self.setStyleSheet(self.themes[theme_name])
        self.save_settings()
        self.refresh_display()

    def update_format_selector(self, type_choice):
        self.format_selector.clear()
        if type_choice == "Video":
            self.format_selector.addItems([".mp4", ".m4a", ".mkv"])
        else:  # Audio
            self.format_selector.addItems([".mp3", ".ogg", ".wav"])

    def clear_grid(self, grid):
        while grid.count():
            item = grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def refresh_display(self):
        mutex.lock()
        self.clear_grid(self.video_grid)
        self.clear_grid(self.music_grid)
        self.grid_positions = {
            "videos": {"row": 0, "col": 0},
            "music": {"row": 0, "col": 0}
        }
        
        for video in self.video_dir.glob("*.[mp4|m4a|mkv]"):
            thumb = self.thumbnail_dir / f"{video.stem}.webp"
            if thumb.exists():
                self.add_tile(video.stem, str(thumb), str(video), "videos")
        
        for audio in self.music_dir.glob("*.[mp3|ogg|wav]"):
            cover = self.cover_dir / f"{audio.stem}.webp"
            if cover.exists():
                self.add_tile(audio.stem, str(cover), str(audio), "music")
        mutex.unlock()

    def add_tile(self, title, thumbnail_path, file_path, category):
        tile = DownloadTile(title, thumbnail_path, file_path)
        pos = self.grid_positions[category]
        grid = self.video_grid if category == "videos" else self.music_grid
        grid.addWidget(tile, pos["row"], pos["col"])
        pos["col"] += 1
        if pos["col"] >= 5:
            pos["col"] = 0
            pos["row"] += 1

    def download_content(self):
        clipboard = QApplication.clipboard()
        url = self.url_input.text() or clipboard.text()
        type_choice = self.type_selector.currentText()
        format_choice = self.format_selector.currentText().lstrip('.')
        
        if not url:
            self.status_bar.showMessage("Error: Please enter a YouTube URL.")
            return
        
        self.url_input.setText(url)
        self.status_bar.showMessage(f"Starting download: {url}")
        threading.Thread(target=self._download, args=(url, type_choice, format_choice), daemon=True).start()
    
    def _download(self, url, type_choice, format_choice):
        try:
            ffmpeg_path = str(self.ffmpeg_dir / "ffmpeg.exe")
            if not os.path.exists(ffmpeg_path):
                raise Exception("ffmpeg.exe not found in ffmpeg folder")
                
            output_dir = self.music_dir if type_choice == "Audio" else self.video_dir
            art_dir = self.cover_dir if type_choice == "Audio" else self.thumbnail_dir
            
            def progress_hook(d):
                if d['status'] == 'downloading':
                    percentage = d.get('downloaded_bytes', 0) / d.get('total_bytes', 1) * 100
                    self.status_bar.showMessage(f"Downloading: {d['filename']} - {percentage:.1f}%")
                elif d['status'] == 'finished':
                    self.status_bar.showMessage(f"Download completed: {d['filename']}")
            
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                title = info.get('title', 'Unknown Title').replace('/', '_').replace('\\', '_')
            
            ydl_opts = {
                'ffmpeg_location': ffmpeg_path,
                'writethumbnail': True,
                'outtmpl': str(output_dir / f"{title}.{format_choice}"),
                'progress_hooks': [progress_hook],
            }
            
            if type_choice == "Audio":
                ydl_opts.update({
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': format_choice,
                        'preferredquality': '192' if format_choice == 'mp3' else '5',
                    }],
                })
            else:  # Video
                ydl_opts.update({
                    'format': 'bestvideo+bestaudio/best',
                    'merge_output_format': format_choice,
                })
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                
                thumbnail_path = None
                content_path = None
                for file in output_dir.glob(f"{title}.*"):
                    if file.suffix in ['.webp', '.jpg', '.png']:
                        thumbnail_path = art_dir / f"{title}.webp"
                        shutil.move(str(file), str(thumbnail_path))
                    elif file.suffix in ['.mp3', '.ogg', '.wav', '.mp4', '.m4a', '.mkv']:
                        content_path = file
                
                if thumbnail_path and content_path:
                    if type_choice == "Video" and content_path.suffix in ['.mp4', '.m4a', '.mkv']:
                        try:
                            # Use ffmpeg-python to embed thumbnail
                            video_stream = ffmpeg.input(str(content_path))
                            thumbnail_stream = ffmpeg.input(str(thumbnail_path), vframes=1)
                            output = ffmpeg.output(
                                video_stream,
                                thumbnail_stream,
                                str(content_path),
                                map=['0:0', '1:0'],  # Use a list for multiple mappings
                                c='copy',
                                disposition='attached_pic',
                                loglevel='error'
                            )
                            ffmpeg.run(output)
                        except ffmpeg.Error as e:
                            raise Exception(f"FFmpeg error: {e.stderr.decode()}")
                    
                    category = "music" if type_choice == "Audio" else "videos"
                    mutex.lock()
                    self.add_tile(title, str(thumbnail_path), str(content_path), category)
                    mutex.unlock()
                
                self.refresh_display()
                self.status_bar.showMessage(f"Download completed: {title}.{format_choice}")
                
        except Exception as e:
            self.status_bar.showMessage(f"Download failed: {str(e)}")
            print(f"Error downloading: {e}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = YouTubeDownloader()
    window.show()
    sys.exit(app.exec())