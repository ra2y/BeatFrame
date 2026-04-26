import sys
import os
import json
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QFileDialog, QSlider, QVBoxLayout, QHBoxLayout, QGridLayout,
    QDialog, QMessageBox, QFrame, QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal, QUrl, QPointF
from PySide6.QtGui import QFont, QColor, QPalette, QPainter, QPen, QBrush, QLinearGradient, QPixmap
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

# ── paths ──────────────────────────────────────────────────────────────────────
OUTPUT_DIR          = os.path.dirname(__file__)  # Project directory for timestamps.csv
INSTALLER_SCRIPT    = os.path.join(os.path.dirname(__file__), "installer.py")

# Path to BeatFrameScript.py in DaVinci Resolve's Scripts folder
def get_resolve_scripts_path():
    import platform
    from pathlib import Path
    system = platform.system()

    if system == "Darwin":  # macOS
        return Path("/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Utility")
    elif system == "Windows":
        return Path(r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Fusion\Scripts\Utility")
    elif system == "Linux":
        return Path("/opt/resolve/Fusion/Scripts/Utility")
    else:
        raise Exception("Unsupported OS")


# ── background worker ──────────────────────────────────────────────────────────
class AnalyzeWorker(QThread):
    finished = Signal(str)   # emits csv path
    error    = Signal(str)

    def __init__(self, audio_path, sensitivity, max_markers, min_gap, top_n):
        super().__init__()
        self.audio_path  = audio_path
        self.sensitivity = sensitivity
        self.max_markers = max_markers
        self.min_gap     = min_gap
        self.top_n       = top_n

    def run(self):
        try:
            from analyze import analyze_audio          # ← matches the real function name
            csv_path = os.path.join(os.path.dirname(__file__), "timestamps.csv")  # Always use timestamps.csv
            print(f"Analysis will write to: {csv_path}")
            analyze_audio(
                self.audio_path,
                sensitivity  = self.sensitivity,
                max_markers  = self.max_markers,
                min_gap      = self.min_gap,
                top_n        = self.top_n,
                output_dir   = OUTPUT_DIR,
            )
            self.finished.emit(csv_path)
        except Exception as e:
            import traceback
            self.error.emit(traceback.format_exc())


# ── install-check popup ────────────────────────────────────────────────────────
class InstallDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("BeatFrame — setup")
        self.setFixedWidth(400)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("Script folder not found")
        title.setStyleSheet("font-size: 15px; font-weight: 500;")
        layout.addWidget(title)

        desc = QLabel(
            "BeatFrame needs a scripts folder to store your analysis files.\n"
            "Would you like to create it now?"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 13px; color: #666;")
        layout.addWidget(desc)

        path_label = QLabel(OUTPUT_DIR)
        path_label.setStyleSheet(
            "font-family: monospace; font-size: 11px; background: #f4f4f4;"
            "padding: 6px 10px; border-radius: 6px; color: #444;"
        )
        layout.addWidget(path_label)

        btn_row = QHBoxLayout()
        self.skip_btn    = QPushButton("Skip for now")
        self.install_btn = QPushButton("Yes, create folder")
        self.install_btn.setStyleSheet(
            "background: #534AB7; color: white; border: none;"
            "padding: 8px 16px; border-radius: 6px; font-size: 13px;"
        )
        btn_row.addWidget(self.skip_btn)
        btn_row.addWidget(self.install_btn)
        layout.addLayout(btn_row)

        self.status = QLabel("")
        self.status.setStyleSheet("font-size: 12px; color: #3B6D11;")
        self.status.hide()
        layout.addWidget(self.status)

        self.install_btn.clicked.connect(self.run_install)
        self.skip_btn.clicked.connect(self.accept)

    def run_install(self):
        self.install_btn.setEnabled(False)
        self.install_btn.setText("Creating...")
        try:
            os.makedirs(OUTPUT_DIR, exist_ok=True)

            # run installer.py if it exists — it copies BeatFrameScript.py to Resolve
            if os.path.exists(INSTALLER_SCRIPT):
                import subprocess
                result = subprocess.run(
                    [sys.executable, INSTALLER_SCRIPT],
                    capture_output=True, text=True
                )
                if result.returncode != 0:
                    raise RuntimeError(result.stderr)

            self.status.setText("Folder created. Continuing to BeatFrame...")
            self.status.show()
            QTimer.singleShot(1400, self.accept)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            self.install_btn.setEnabled(True)
            self.install_btn.setText("Yes, create folder")


# ── landing page ───────────────────────────────────────────────────────────────
class LandingPage(QWidget):
    get_started = Signal()

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(0)
        layout.setContentsMargins(60, 0, 60, 40)

        # ── hero section ──────────────────────────────────────────────────────
        layout.addStretch(2)

        title_row = QHBoxLayout()
        title_row.setAlignment(Qt.AlignCenter)
        title_row.setSpacing(14)

        logo = QLabel()
        dpr = self.devicePixelRatio()
        size = 58
        pixmap = QPixmap("soundicon.png").scaled(
            int(size * dpr), int(size * dpr),
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        pixmap.setDevicePixelRatio(dpr)
        logo.setPixmap(pixmap)
        logo.setFixedSize(size, size)
        logo.setAlignment(Qt.AlignVCenter)

        title = QLabel("BeatFrame")
        title.setStyleSheet("font-size: 50px; font-weight: 700; letter-spacing: -1px;")
        title.setAlignment(Qt.AlignVCenter)

        title_row.addWidget(logo)
        title_row.addWidget(title)
        layout.addLayout(title_row)

        layout.addSpacing(12)

        subtitle = QLabel(
            "Sync your video edits to music — automatically.\n"
            "Analyze a track, preview the beat drops, export to Resolve."
        )
        subtitle.setStyleSheet("font-size: 15px; color: #888; line-height: 1.5;")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        layout.addSpacing(24)

        btn = QPushButton("Get started →")
        btn.setFixedWidth(150)
        btn.setStyleSheet(
            "background: #534AB7; color: white; border: none;"
            "padding: 11px 24px; border-radius: 8px; font-size: 14px; font-weight: 600;"
        )
        btn.clicked.connect(self.get_started)
        layout.addWidget(btn, alignment=Qt.AlignCenter)

        layout.addStretch(1)

        # ── divider ───────────────────────────────────────────────────────────
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("color: #e0e0e0;")
        layout.addWidget(divider)

        layout.addSpacing(24)

        # ── how it works label ────────────────────────────────────────────────
        how_label = QLabel("HOW IT WORKS")
        how_label.setStyleSheet("font-size: 11px; font-weight: 600; color: #aaa; letter-spacing: 2px;")
        how_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(how_label)

        layout.addSpacing(16)

        # ── cards ─────────────────────────────────────────────────────────────
        cards_row = QHBoxLayout()
        cards_row.setSpacing(12)
        for title_txt, body_txt in [
            ("Analyze",  "Upload audio, detect beats, peaks, and mood sections"),
            ("Preview",  "See every beat drop flash in real time before exporting"),
            ("Export",   "Save a CSV + JSON, then run the Resolve script to apply markers"),
        ]:
            card = QFrame()
            card.setStyleSheet(
                "background: white; border-radius: 10px; border: 1px solid #e8e8e8;"
            )
            card.setMinimumHeight(110)
            cl = QVBoxLayout(card)
            cl.setContentsMargins(16, 16, 16, 16)
            cl.setSpacing(6)
            ct = QLabel(title_txt)
            ct.setStyleSheet("font-size: 13px; font-weight: 600; border: none;")
            cb = QLabel(body_txt)
            cb.setStyleSheet("font-size: 12px; color: #888; border: none;")
            cb.setWordWrap(True)
            cl.addWidget(ct)
            cl.addWidget(cb)
            cards_row.addWidget(card)

        layout.addLayout(cards_row)
        layout.addSpacing(24)


# ── beat timeline canvas ───────────────────────────────────────────────────────
class BeatTimeline(QWidget):
    """
    Draws a horizontal timeline with:
      - cut point markers (purple ticks)
      - a moving playhead
      - a flash highlight when the playhead crosses a cut point
    """
    seek_requested = Signal(float)   # fraction 0-1

    FLASH_MS = 120

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(54)
        self.setMaximumHeight(54)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor)

        self._duration    = 1.0    # seconds
        self._position    = 0.0    # seconds
        self._cut_points  = []     # list of float seconds
        self._flash_on    = False
        self._flash_timer = QTimer(self)
        self._flash_timer.setSingleShot(True)
        self._flash_timer.timeout.connect(self._end_flash)
        self._next_cut_idx = 0

    def set_cut_points(self, points, duration):
        self._cut_points   = sorted(points)
        self._duration     = max(duration, 1.0)
        self._next_cut_idx = 0
        self.update()

    def set_position(self, seconds: float):
        prev = self._position
        self._position = seconds

        # fire flash when we pass a cut point
        while (self._next_cut_idx < len(self._cut_points) and
               seconds >= self._cut_points[self._next_cut_idx]):
            self._next_cut_idx += 1
            self._start_flash()

        # reset index if playback jumped backward
        if seconds < prev - 0.5:
            self._next_cut_idx = sum(1 for c in self._cut_points if c <= seconds)

        self.update()

    def reset(self):
        self._position     = 0.0
        self._next_cut_idx = 0
        self._flash_on     = False
        self.update()

    def _start_flash(self):
        self._flash_on = True
        self._flash_timer.start(self.FLASH_MS)
        self.update()

    def _end_flash(self):
        self._flash_on = False
        self.update()

    # ── painting ───────────────────────────────────────────────────────────────
    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        # background
        bg = QColor("#f0f0f0") if not self._flash_on else QColor("#e8e5ff")
        p.fillRect(0, 0, w, h, bg)

        # track groove
        groove_y = h // 2
        groove_h = 6
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#d0d0d0"))
        p.drawRoundedRect(12, groove_y - groove_h // 2, w - 24, groove_h, 3, 3)

        # played portion
        pct = self._position / self._duration
        played_w = int((w - 24) * pct)
        if played_w > 0:
            p.setBrush(QColor("#534AB7"))
            p.drawRoundedRect(12, groove_y - groove_h // 2, played_w, groove_h, 3, 3)

        # cut point ticks
        tick_h = 16
        p.setPen(QPen(QColor("#534AB7"), 2))
        for cp in self._cut_points:
            x = 12 + int((w - 24) * (cp / self._duration))
            p.drawLine(x, groove_y - tick_h // 2, x, groove_y + tick_h // 2)

        # playhead
        ph_x = 12 + int((w - 24) * pct)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#ffffff"))
        p.drawEllipse(ph_x - 7, groove_y - 7, 14, 14)
        p.setBrush(QColor("#534AB7") if not self._flash_on else QColor("#D85A30"))
        p.drawEllipse(ph_x - 5, groove_y - 5, 10, 10)

        p.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            frac = (event.position().x() - 12) / max(self.width() - 24, 1)
            frac = max(0.0, min(1.0, frac))
            self.seek_requested.emit(frac)


# ── beat flash indicator widget ────────────────────────────────────────────────
class BeatFlashWidget(QWidget):
    """
    A small pill that pulses through colors on each beat.
    Idle: grey. On beat: cycles purple → orange → teal, fading back.
    """
    COLORS = ["#534AB7", "#D85A30", "#1D9E75", "#C4820A"]
    FADE_MS = 180

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(52, 24)
        self._color     = QColor("#cccccc")
        self._target    = QColor("#cccccc")
        self._color_idx = 0
        self._active    = False

        self._fade_timer = QTimer(self)
        self._fade_timer.setInterval(12)   # ~80 fps fade
        self._fade_timer.timeout.connect(self._fade_step)

        self._hold_timer = QTimer(self)
        self._hold_timer.setSingleShot(True)
        self._hold_timer.timeout.connect(self._start_fade_out)

    def flash(self):
        col = self.COLORS[self._color_idx % len(self.COLORS)]
        self._color_idx += 1
        self._color  = QColor(col)
        self._target = QColor(col)
        self._active = True
        self._fade_timer.stop()
        self._hold_timer.start(self.FADE_MS)
        self.update()

    def _start_fade_out(self):
        self._target = QColor("#cccccc")
        self._fade_timer.start()

    def _fade_step(self):
        # lerp current color toward target
        r = self._color.red()   + (self._target.red()   - self._color.red())   // 4
        g = self._color.green() + (self._target.green() - self._color.green()) // 4
        b = self._color.blue()  + (self._target.blue()  - self._color.blue())  // 4
        self._color = QColor(r, g, b)
        self.update()
        if abs(r - self._target.red()) < 3 and abs(g - self._target.green()) < 3:
            self._fade_timer.stop()
            self._color  = self._target
            self._active = False
            self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(self._color)
        p.drawRoundedRect(0, 0, self.width(), self.height(), 12, 12)
        if self._active:
            p.setPen(QColor(255, 255, 255, 200))
            p.setFont(QFont("Arial", 9, QFont.Bold))
            p.drawText(self.rect(), Qt.AlignCenter, "◉")
        p.end()


# ── audio player widget ────────────────────────────────────────────────────────
class AudioPlayerWidget(QFrame):
    """
    Full audio player: play/pause, seek timeline with beat markers, time label.
    Uses QMediaPlayer (PySide6 built-in, no extra deps).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            "background: #f8f8f8; border-radius: 10px; border: 1px solid #e0e0e0;"
        )

        self._player = QMediaPlayer(self)
        self._audio  = QAudioOutput(self)
        self._player.setAudioOutput(self._audio)
        self._audio.setVolume(1.0)
        self._duration_sec = 0.0
        self._cut_points   = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # top row: track name + time
        top = QHBoxLayout()
        self._track_label = QLabel("No track loaded")
        self._track_label.setStyleSheet(
            "font-size: 12px; font-weight: 500; color: #333; border: none;"
        )
        self._time_label = QLabel("0:00 / 0:00")
        self._time_label.setStyleSheet("font-size: 11px; color: #888; border: none;")
        top.addWidget(self._track_label)
        top.addStretch()
        top.addWidget(self._time_label)
        layout.addLayout(top)

        # timeline
        self._timeline = BeatTimeline(self)
        self._timeline.seek_requested.connect(self._on_seek)
        layout.addWidget(self._timeline)

        # controls row
        ctrl = QHBoxLayout()
        self._play_btn = QPushButton("▶  Play")
        self._play_btn.setFixedWidth(90)
        self._play_btn.setEnabled(False)
        self._play_btn.setStyleSheet(
            "background: #534AB7; color: white; border: none;"
            "padding: 6px 12px; border-radius: 6px; font-size: 12px;"
        )
        self._play_btn.clicked.connect(self.toggle_play)

        vol_label = QLabel("Vol")
        vol_label.setStyleSheet("font-size: 11px; color: #aaa; border: none;")
        self._vol_slider = QSlider(Qt.Horizontal)
        self._vol_slider.setRange(0, 100)
        self._vol_slider.setValue(100)
        self._vol_slider.setFixedWidth(80)
        self._vol_slider.valueChanged.connect(
            lambda v: self._audio.setVolume(v / 100.0)
        )

        self._beat_flash = BeatFlashWidget()

        ctrl.addWidget(self._play_btn)
        ctrl.addSpacing(10)
        ctrl.addWidget(vol_label)
        ctrl.addWidget(self._vol_slider)
        ctrl.addStretch()
        ctrl.addWidget(self._beat_flash)
        layout.addLayout(ctrl)

        # poll position every 40 ms (~25 fps)
        self._poll = QTimer(self)
        self._poll.setInterval(40)
        self._poll.timeout.connect(self._tick)

        self._player.playbackStateChanged.connect(self._on_state_change)
        self._player.durationChanged.connect(self._on_duration_changed)

    # ── public API ─────────────────────────────────────────────────────────────
    def load(self, audio_path: str, cut_points: list, duration: float):
        self._player.stop()
        self._poll.stop()
        self._cut_points   = cut_points
        self._duration_sec = duration
        self._timeline.set_cut_points(cut_points, duration)
        self._timeline.reset()
        self._track_label.setText(os.path.basename(audio_path))
        self._time_label.setText(f"0:00 / {self._fmt(duration)}")
        self._play_btn.setEnabled(True)
        self._play_btn.setText("▶  Play")
        self._beat_flash._color = QColor("#cccccc")
        self._beat_flash._active = False
        self._beat_flash.update()
        self._player.setSource(QUrl.fromLocalFile(os.path.abspath(audio_path)))

    def toggle_play(self):
        if self._player.playbackState() == QMediaPlayer.PlayingState:
            self._player.pause()
            self._poll.stop()
            self._play_btn.setText("▶  Play")
        else:
            self._player.play()
            self._poll.start()
            self._play_btn.setText("⏸  Pause")

    # ── internals ──────────────────────────────────────────────────────────────
    def _tick(self):
        ms  = self._player.position()
        sec = ms / 1000.0
        prev_flash = self._timeline._flash_on
        self._timeline.set_position(sec)
        self._time_label.setText(f"{self._fmt(sec)} / {self._fmt(self._duration_sec)}")

        # trigger flash widget when timeline just turned on
        if self._timeline._flash_on and not prev_flash:
            self._beat_flash.flash()

    def _on_seek(self, frac: float):
        ms = int(frac * self._duration_sec * 1000)
        self._player.setPosition(ms)
        self._timeline.set_position(frac * self._duration_sec)

    def _on_duration_changed(self, ms: int):
        if ms > 0 and self._duration_sec == 0:
            self._duration_sec = ms / 1000.0
            self._timeline.set_cut_points(self._cut_points, self._duration_sec)

    def _on_state_change(self, state):
        if state == QMediaPlayer.StoppedState:
            self._poll.stop()
            self._play_btn.setText("▶  Play")
            self._timeline.reset()

    @staticmethod
    def _fmt(sec: float) -> str:
        m = int(sec) // 60
        s = int(sec) % 60
        return f"{m}:{s:02d}"


# ── main analysis page ─────────────────────────────────────────────────────────
class AnalysisPage(QWidget):
    def __init__(self):
        super().__init__()
        self.audio_path  = None
        self.worker      = None
        self.cut_points  = []
        self.duration    = 0.0       # filled after analysis

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── top area: left + right panels side by side ────────────────────────
        top_area = QWidget()
        top_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        top_layout = QHBoxLayout(top_area)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(0)

        # ── left panel ────────────────────────────────────────────────────────
        left = QWidget()
        left.setMinimumWidth(380)
        ll = QVBoxLayout(left)
        ll.setContentsMargins(16, 16, 16, 16)
        ll.setSpacing(12)

        # drop zone
        drop_frame = QFrame()
        drop_frame.setFixedHeight(90)
        drop_frame.setStyleSheet(
            "border: 2px dashed #ccc; border-radius: 8px; background: #fafafa;"
        )
        df_layout = QVBoxLayout(drop_frame)
        df_layout.setAlignment(Qt.AlignCenter)
        df_layout.setContentsMargins(16, 16, 16, 16)
        drop_label = QLabel("Drop audio file here")
        drop_label.setStyleSheet("font-size: 13px; color: #666; border: none;")
        drop_label.setAlignment(Qt.AlignCenter)
        drop_hint = QLabel("WAV · MP3 · FLAC")
        drop_hint.setStyleSheet("font-size: 11px; color: #aaa; border: none;")
        drop_hint.setAlignment(Qt.AlignCenter)
        browse_btn = QPushButton("Browse file")
        browse_btn.setFixedWidth(100)
        browse_btn.clicked.connect(self.browse_file)
        df_layout.addWidget(drop_label)
        df_layout.addWidget(drop_hint)
        df_layout.addWidget(browse_btn, alignment=Qt.AlignCenter)
        ll.addWidget(drop_frame)

        # loaded file row
        self.file_row = QFrame()
        self.file_row.setStyleSheet(
            "background: #f4f4f4; border-radius: 8px; border: 1px solid #e0e0e0;"
        )
        fr_layout = QHBoxLayout(self.file_row)
        fr_layout.setContentsMargins(10, 8, 10, 8)
        self.file_name_label = QLabel("No file loaded")
        self.file_name_label.setStyleSheet("font-size: 12px; font-weight: 500; border: none;")
        self.file_meta_label = QLabel("")
        self.file_meta_label.setStyleSheet("font-size: 11px; color: #aaa; border: none;")
        fl = QVBoxLayout()
        fl.setSpacing(2)
        fl.addWidget(self.file_name_label)
        fl.addWidget(self.file_meta_label)
        fr_layout.addLayout(fl)
        fr_layout.addStretch()
        self.file_status = QLabel("")
        self.file_status.setStyleSheet(
            "font-size: 11px; color: #3B6D11; background: #EAF3DE;"
            "padding: 2px 8px; border-radius: 10px; border: none;"
        )
        fr_layout.addWidget(self.file_status)
        ll.addWidget(self.file_row)

        # sliders
        slider_title = QLabel("Analysis settings")
        slider_title.setStyleSheet("font-size: 11px; color: #aaa;")
        ll.addWidget(slider_title)

        self.sliders = {}
        slider_defs = [
            ("sensitivity", "Peak sensitivity",  0,  100, 70,  "%"),
            ("max_markers", "Max markers",        5,   50, 20,  ""),
            ("min_gap",     "Min gap (sec)",      1,   10,  3,  "s"),
            ("top_n",       "Top N peaks",        5,   40, 15,  ""),
        ]
        for key, label, mn, mx, default, unit in slider_defs:
            row = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setFixedWidth(120)
            lbl.setStyleSheet("font-size: 12px; color: #555;")
            slider = QSlider(Qt.Horizontal)
            slider.setRange(mn, mx)
            slider.setValue(default)
            val_label = QLabel(f"{default}{unit}")
            val_label.setFixedWidth(36)
            val_label.setStyleSheet("font-size: 12px; font-weight: 500;")
            slider.valueChanged.connect(
                lambda v, vl=val_label, u=unit: vl.setText(f"{v}{u}")
            )
            self.sliders[key] = slider
            row.addWidget(lbl)
            row.addWidget(slider)
            row.addWidget(val_label)
            ll.addLayout(row)

        # analyze button
        self.analyze_btn = QPushButton("Analyze and export CSV")
        self.analyze_btn.setStyleSheet(
            "background: #534AB7; color: white; border: none;"
            "padding: 10px; border-radius: 8px; font-size: 13px; font-weight: 500;"
        )
        self.analyze_btn.clicked.connect(self.run_analysis)
        ll.addWidget(self.analyze_btn)

        self.export_label = QLabel("")
        self.export_label.setStyleSheet(
            "font-size: 12px; color: #3B6D11; background: #EAF3DE;"
            "padding: 7px 10px; border-radius: 8px;"
        )
        self.export_label.hide()
        ll.addWidget(self.export_label)

        # ── right panel ───────────────────────────────────────────────────────
        divider = QFrame()
        divider.setFrameShape(QFrame.VLine)
        divider.setStyleSheet("color: #e0e0e0;")

        right = QWidget()
        right.setFixedWidth(220)
        rl = QVBoxLayout(right)
        rl.setContentsMargins(14, 14, 14, 14)
        rl.setSpacing(10)

        results_title = QLabel("Results")
        results_title.setStyleSheet("font-size: 11px; color: #aaa;")
        rl.addWidget(results_title)

        stat_grid = QGridLayout()
        stat_grid.setSpacing(8)
        self.stat_labels = {}
        stats = [("BPM", "—"), ("Peaks", "—"), ("Beats", "—"), ("Mood", "—")]
        for i, (name, val) in enumerate(stats):
            card = QFrame()
            card.setStyleSheet("background: #f4f4f4; border-radius: 8px;")
            cl = QVBoxLayout(card)
            cl.setContentsMargins(10, 8, 10, 8)
            cl.setSpacing(2)
            n = QLabel(name)
            n.setStyleSheet("font-size: 11px; color: #aaa;")
            v = QLabel(val)
            v.setStyleSheet("font-size: 20px; font-weight: 500;")
            cl.addWidget(n)
            cl.addWidget(v)
            self.stat_labels[name] = v
            stat_grid.addWidget(card, i // 2, i % 2)
        rl.addLayout(stat_grid)

        ts_title = QLabel("Top peak timestamps")
        ts_title.setStyleSheet("font-size: 11px; color: #aaa;")
        rl.addWidget(ts_title)

        self.ts_frame = QFrame()
        self.ts_frame.setStyleSheet(
            "background: #f4f4f4; border-radius: 8px; border: 1px solid #e0e0e0;"
        )
        self.ts_layout = QVBoxLayout(self.ts_frame)
        self.ts_layout.setContentsMargins(10, 6, 10, 6)
        self.ts_layout.setSpacing(4)
        placeholder = QLabel("Run analysis to see timestamps")
        placeholder.setStyleSheet("font-size: 11px; color: #aaa;")
        self.ts_layout.addWidget(placeholder)
        rl.addWidget(self.ts_frame)

        rl.addStretch()

        note = QFrame()
        note.setStyleSheet(
            "background: #FAEEDA; border-radius: 8px;"
        )
        nl = QVBoxLayout(note)
        nl.setContentsMargins(10, 10, 10, 10)
        nl.setSpacing(4)
        note_title = QLabel("Next step")
        note_title.setStyleSheet("font-size: 12px; font-weight: 500; color: #633806;")
        note_body = QLabel(
            "Happy with the results? Go back to DaVinci Resolve, click "
            "Workspace> Scripts > Utility > BeatFrameScript.py "
            "to place markers on your timeline."
        )
        note_body.setStyleSheet("font-size: 11px; color: #854F0B;")
        note_body.setWordWrap(True)
        nl.addWidget(note_title)
        nl.addWidget(note_body)
        rl.addWidget(note)

        top_layout.addWidget(left)
        top_layout.addWidget(divider)
        top_layout.addWidget(right)

        # ── bottom player bar — always visible ────────────────────────────────
        player_bar = QFrame()
        player_bar.setStyleSheet(
            "background: #f0eff8; border-top: 1px solid #ddd;"
        )
        player_bar.setFixedHeight(130)
        player_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        pb_layout = QVBoxLayout(player_bar)
        pb_layout.setContentsMargins(16, 8, 16, 8)
        pb_layout.setSpacing(0)

        self.player = AudioPlayerWidget()
        pb_layout.addWidget(self.player)

        # top_area gets all remaining space; player_bar stays fixed at bottom
        root.addWidget(top_area, stretch=1)
        root.addWidget(player_bar, stretch=0)

    # ── browse file ────────────────────────────────────────────────────────────
    def browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open audio file", "",
            "Audio files (*.mp3 *.wav *.flac *.aiff *.ogg)"
        )
        if path:
            self.audio_path = path
            name = os.path.basename(path)
            size = os.path.getsize(path) // 1024
            self.file_name_label.setText(name)
            self.file_meta_label.setText(f"{size} KB")
            self.file_status.setText("loaded")
            # reset results from any previous file
            self.cut_points = []
            self.export_label.hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)

    # ── run analysis ───────────────────────────────────────────────────────────
    def run_analysis(self):
        if not self.audio_path:
            QMessageBox.warning(self, "No file", "Please load an audio file first.")
            return

        self.analyze_btn.setEnabled(False)
        self.analyze_btn.setText("Analyzing…")
        self.export_label.hide()

        self.worker = AnalyzeWorker(
            audio_path  = self.audio_path,
            sensitivity = self.sliders["sensitivity"].value() / 100.0,
            max_markers = self.sliders["max_markers"].value(),
            min_gap     = float(self.sliders["min_gap"].value()),
            top_n       = self.sliders["top_n"].value(),
        )
        self.worker.finished.connect(self.on_analysis_done)
        self.worker.error.connect(self.on_analysis_error)
        self.worker.start()

    # ── called when AnalyzeWorker emits finished(csv_path) ────────────────────
    def on_analysis_done(self, csv_path: str):
        self.analyze_btn.setEnabled(True)
        self.analyze_btn.setText("Analyze and export CSV")

        # inject csv path into resolve script so it points at this run's file
        self._inject_csv_path(csv_path)

        self.export_label.setText(f"Saved → {csv_path}")
        self.export_label.show()

        # load the JSON manifest written by analyze_audio()
        json_path = csv_path.replace(".csv", ".json")
        if os.path.exists(json_path):
            with open(json_path, encoding="utf-8") as f:
                m = json.load(f)

            # stat cards
            self.stat_labels["BPM"].setText(str(round(m.get("bpm", 0))))
            self.stat_labels["Peaks"].setText(str(m.get("peak_count", "—")))
            self.stat_labels["Beats"].setText(str(m.get("beat_count", "—")))
            self.stat_labels["Mood"].setText(m.get("mood", "—"))
            self.stat_labels["Mood"].setStyleSheet(
                "font-size: 13px; font-weight: 500; color: #534AB7;"
            )

            # store cut points so flash preview can use them
            self.cut_points  = m.get("cut_points", [])
            self.duration    = m.get("duration", 0.0)

            # load player with real beat markers
            self.player.load(self.audio_path, self.cut_points, self.duration)

            # timestamp list
            for i in reversed(range(self.ts_layout.count())):
                w = self.ts_layout.itemAt(i).widget()
                if w:
                    w.deleteLater()
            for peak in m.get("top_peaks", [])[:8]:
                row = QLabel(
                    f"{peak['time_fmt']}  —  {round(peak['strength'] * 100)}%"
                )
                row.setStyleSheet("font-size: 11px; font-family: monospace; color: #333;")
                self.ts_layout.addWidget(row)

        # enable player now that we have real cut points
        if self.cut_points:
            self.player._play_btn.setEnabled(True)

    # ── called when AnalyzeWorker emits error(msg) ─────────────────────────────
    def on_analysis_error(self, msg: str):
        self.analyze_btn.setEnabled(True)
        self.analyze_btn.setText("Analyze and export CSV")
        QMessageBox.critical(self, "Analysis error", msg)

    # ── patch resolve script with the new csv path ─────────────────────────────
    def _inject_csv_path(self, csv_path: str):
        """Update the CSV path in BeatFrameScript.py inside DaVinci Resolve."""
        resolve_scripts_dir = get_resolve_scripts_path()
        resolve_script = resolve_scripts_dir / "BeatFrameScript.py"
        print(f"Updating BeatFrameScript.py at: {resolve_script}")
        if not os.path.exists(str(resolve_script)):
            print(f"Warning: BeatFrameScript.py not found at {resolve_script}")
            return
        import re
        # Normalize path to forward slashes (works on all platforms: Windows/Mac/Linux)
        # Windows: C:\path\file → C:/path/file | Mac/Linux: /path/file → /path/file (unchanged)
        csv_path_normalized = csv_path.replace('\\', '/')
        print(f"Setting CSV path to: {csv_path_normalized}")
        with open(str(resolve_script), "r", encoding="utf-8") as f:
            content = f.read()
        content = re.sub(
            r'CSV_FILEPATH\s*=\s*".*?"',
            lambda m: f'CSV_FILEPATH = "{csv_path_normalized}"',
            content,
        )
        with open(str(resolve_script), "w", encoding="utf-8") as f:
            f.write(content)


# ── main window ────────────────────────────────────────────────────────────────
class BeatFrameApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BeatFrame")
        self.setMinimumSize(680, 680)

        if not os.path.exists(OUTPUT_DIR):
            dialog = InstallDialog(self)
            dialog.exec()

        self._ensure_resolve_script_installed()

        self.landing  = LandingPage()
        self.analysis = AnalysisPage()
        self.landing.get_started.connect(self.show_analysis)
        self.setCentralWidget(self.landing)

    def closeEvent(self, event):
        """Handle graceful shutdown when the app is closed."""
        # Stop any running worker threads
        if hasattr(self.analysis, 'worker') and self.analysis.worker and self.analysis.worker.isRunning():
            self.analysis.worker.quit()
            self.analysis.worker.wait(3000)  # Wait up to 3 seconds for clean shutdown
        
        # Accept the close event
        event.accept()

    def _ensure_resolve_script_installed(self):
        """Check if DaVinci Resolve script exists; run installer if missing."""
        resolve_scripts_dir = get_resolve_scripts_path()
        resolve_script = resolve_scripts_dir / "BeatFrameScript.py"
        if not os.path.exists(str(resolve_script)):
            print(f"BeatFrameScript.py not found at {resolve_script}. Running installer...")
            # Create output directory if it doesn't exist
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            
            # Run installer script
            if os.path.exists(INSTALLER_SCRIPT):
                try:
                    import subprocess
                    result = subprocess.run(
                        [sys.executable, INSTALLER_SCRIPT],
                        capture_output=True, text=True
                    )
                    print(result.stdout)  # Print installer output
                    if result.returncode != 0:
                        raise RuntimeError(f"Installer failed: {result.stderr}")
                except Exception as e:
                    print(f"Warning: Could not install DaVinci script: {e}")

    def show_analysis(self):
        self.setCentralWidget(self.analysis)