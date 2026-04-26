import sys
import os
import json
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QFileDialog, QSlider, QVBoxLayout, QHBoxLayout, QGridLayout,
    QDialog, QMessageBox, QFrame, QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QFont, QColor, QPalette

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
        layout.setSpacing(16)
        layout.setContentsMargins(40, 40, 40, 40)

        title = QLabel("BeatFrame")
        title.setStyleSheet("font-size: 28px; font-weight: 500;")
        title.setAlignment(Qt.AlignCenter)

        subtitle = QLabel(
            "Sync your video edits to music — automatically.\n"
            "Analyze a track, preview the beat drops, export to Resolve."
        )
        subtitle.setStyleSheet("font-size: 14px; color: #666;")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setWordWrap(True)

        btn = QPushButton("Get started")
        btn.setFixedWidth(160)
        btn.setStyleSheet(
            "background: #534AB7; color: white; border: none;"
            "padding: 10px; border-radius: 8px; font-size: 14px; font-weight: 500;"
        )
        btn.clicked.connect(self.get_started)

        cards_row = QHBoxLayout()
        for title_txt, body_txt in [
            ("Analyze",  "Upload audio, detect beats, peaks, and mood sections"),
            ("Preview",  "See every beat drop flash in real time before exporting"),
            ("Export",   "Save a CSV + JSON, then run the Resolve script to apply markers"),
        ]:
            card = QFrame()
            card.setStyleSheet(
                "background: #f8f8f8; border-radius: 8px;"
                "border: 1px solid #e0e0e0; padding: 4px;"
            )
            cl = QVBoxLayout(card)
            cl.setContentsMargins(12, 12, 12, 12)
            ct = QLabel(title_txt)
            ct.setStyleSheet("font-size: 13px; font-weight: 500;")
            cb = QLabel(body_txt)
            cb.setStyleSheet("font-size: 12px; color: #666;")
            cb.setWordWrap(True)
            cl.addWidget(ct)
            cl.addWidget(cb)
            cards_row.addWidget(card)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(btn, alignment=Qt.AlignCenter)
        layout.addSpacing(16)
        layout.addLayout(cards_row)


# ── main analysis page ─────────────────────────────────────────────────────────
class AnalysisPage(QWidget):
    def __init__(self):
        super().__init__()
        self.audio_path  = None
        self.worker      = None
        self.cut_points  = []        # populated after analysis, used by flash preview

        # flash overlay
        self.flash_overlay = QWidget(self)
        self.flash_overlay.setStyleSheet("background: rgba(83,74,183,160);")
        self.flash_overlay.hide()

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── left panel ────────────────────────────────────────────────────────
        left = QWidget()
        left.setMinimumWidth(380)
        ll = QVBoxLayout(left)
        ll.setContentsMargins(16, 16, 16, 16)
        ll.setSpacing(12)

        # drop zone
        drop_frame = QFrame()
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

        # beat flash preview
        flash_title = QLabel("Beat drop preview")
        flash_title.setStyleSheet("font-size: 11px; color: #aaa;")
        ll.addWidget(flash_title)

        flash_row = QFrame()
        flash_row.setStyleSheet(
            "background: #f4f4f4; border-radius: 8px; border: 1px solid #e0e0e0;"
        )
        fl2 = QHBoxLayout(flash_row)
        fl2.setContentsMargins(10, 8, 10, 8)
        flash_desc = QLabel("Flash at the top N detected cut points")
        flash_desc.setStyleSheet("font-size: 12px; color: #555; border: none;")
        self.flash_btn = QPushButton("Preview flashes")
        self.flash_btn.setFixedWidth(110)
        self.flash_btn.setEnabled(False)      # enabled only after analysis
        self.flash_btn.clicked.connect(self.run_flash)
        fl2.addWidget(flash_desc)
        fl2.addStretch()
        fl2.addWidget(self.flash_btn)
        ll.addWidget(flash_row)

        ll.addStretch()

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
            "background: #FAEEDA; border-radius: 8px; border: 1px solid #EF9F27;"
        )
        nl = QVBoxLayout(note)
        nl.setContentsMargins(10, 10, 10, 10)
        nl.setSpacing(4)
        note_title = QLabel("Next step")
        note_title.setStyleSheet("font-size: 12px; font-weight: 500; color: #633806;")
        note_body = QLabel(
            "Happy with the results? Go back to DaVinci Resolve, "
            "click Workspace at the top > Scripts > Utility > BeatFrameScript.py "
            "to place markers on your timeline."
        )
        note_body.setStyleSheet("font-size: 11px; color: #854F0B;")
        note_body.setWordWrap(True)
        nl.addWidget(note_title)
        nl.addWidget(note_body)
        rl.addWidget(note)

        root.addWidget(left)
        root.addWidget(divider)
        root.addWidget(right)

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
            self.flash_btn.setEnabled(False)
            self.export_label.hide()

    # ── flash preview — plays through actual cut points ────────────────────────
    def run_flash(self):
        if not self.cut_points:
            return
        self.flash_btn.setEnabled(False)
        self.flash_btn.setText("Playing...")
        # show flashes for the first top_n cut points
        n = min(self.sliders["top_n"].value(), len(self.cut_points))
        self._flash_queue = list(self.cut_points[:n])
        self._flash_index = 0
        self._advance_flash()

    def _advance_flash(self):
        if self._flash_index >= len(self._flash_queue):
            self.flash_overlay.hide()
            self.flash_btn.setEnabled(True)
            self.flash_btn.setText("Preview flashes")
            return
        self.flash_overlay.setGeometry(self.rect())
        self.flash_overlay.raise_()
        self.flash_overlay.show()
        self._flash_index += 1
        QTimer.singleShot(150, self._hide_flash)

    def _hide_flash(self):
        self.flash_overlay.hide()
        QTimer.singleShot(300, self._advance_flash)

    def resizeEvent(self, event):
        self.flash_overlay.setGeometry(self.rect())
        super().resizeEvent(event)

    # ── run analysis ───────────────────────────────────────────────────────────
    def run_analysis(self):
        if not self.audio_path:
            QMessageBox.warning(self, "No file", "Please load an audio file first.")
            return

        self.analyze_btn.setEnabled(False)
        self.analyze_btn.setText("Analyzing…")
        self.export_label.hide()
        self.flash_btn.setEnabled(False)

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
            self.cut_points = m.get("cut_points", [])

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

        # enable flash preview now that we have real cut points
        if self.cut_points:
            self.flash_btn.setEnabled(True)

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
            f'CSV_FILEPATH = "{csv_path_normalized}"',
            content,
        )
        with open(str(resolve_script), "w", encoding="utf-8") as f:
            f.write(content)


# ── main window ────────────────────────────────────────────────────────────────
class BeatFrameApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BeatFrame")
        self.setMinimumSize(680, 520)

        # Check if DaVinci Resolve script exists; if not, run installer
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

