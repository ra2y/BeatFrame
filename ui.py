import sys
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QFileDialog, QSlider, QVBoxLayout, QHBoxLayout, QGridLayout,
    QDialog, QMessageBox, QFrame, QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QFont, QColor, QPalette

# ── paths ──────────────────────────────────────────────────────────────────────
RESOLVE_SCRIPT_PATH = os.path.expanduser("~/Documents/BeatFrame/resolve_apply.py")
OUTPUT_DIR          = os.path.expanduser("~/Documents/BeatFrame/")
INSTALLER_SCRIPT    = os.path.join(os.path.dirname(__file__), "installer.py")


# ── background worker so the UI doesn't freeze while librosa runs ───────────
class AnalyzeWorker(QThread):
    finished = Signal(str)   # emits the csv path when done
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
            from analyze import analyze_audio   # your librosa script
            csv_path = analyze_audio(
                self.audio_path,
                sensitivity  = self.sensitivity,
                max_markers  = self.max_markers,
                min_gap      = self.min_gap,
                top_n        = self.top_n,
                output_dir   = OUTPUT_DIR,
            )
            self.finished.emit(csv_path)
        except Exception as e:
            self.error.emit(str(e))


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

        path_label = QLabel(RESOLVE_SCRIPT_PATH)
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
            # copy resolve_apply.py template if installer script exists
            if os.path.exists(INSTALLER_SCRIPT):
                import subprocess
                subprocess.run([sys.executable, INSTALLER_SCRIPT], check=True)
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

        # three feature cards
        cards_row = QHBoxLayout()
        for title_txt, body_txt in [
            ("Analyze",  "Upload audio, detect beats, peaks, and mood sections"),
            ("Preview",  "See every beat drop flash in real time before exporting"),
            ("Export",   "Save a JSON file, then run the Resolve script to apply markers"),
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
        self.audio_path = None
        self.worker     = None

        # flash overlay (sits on top of everything)
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
        flash_desc = QLabel("Flash screen 3× at detected peaks")
        flash_desc.setStyleSheet("font-size: 12px; color: #555; border: none;")
        self.flash_btn = QPushButton("Test flash")
        self.flash_btn.setFixedWidth(90)
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

        # stat cards grid
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

        # top timestamps list
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

        # next step note
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
            "Happy with the results? Go back to DaVinci Resolve "
            "and run the resolve_apply.py script to place markers on your timeline."
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

    # ── beat flash preview ─────────────────────────────────────────────────────
    def run_flash(self):
        self.flash_btn.setEnabled(False)
        self.flash_btn.setText("Flashing...")
        self._flash_count = 0
        self._do_flash()

    def _do_flash(self):
        if self._flash_count >= 3:
            self.flash_overlay.hide()
            self.flash_btn.setEnabled(True)
            self.flash_btn.setText("Test flash")
            return
        self.flash_overlay.setGeometry(self.rect())
        self.flash_overlay.raise_()
        self.flash_overlay.show()
        self._flash_count += 1
        QTimer.singleShot(180, self._hide_flash)

    def _hide_flash(self):
        self.flash_overlay.hide()
        QTimer.singleShot(350, self._do_flash)

    def resizeEvent(self, event):
        self.flash_overlay.setGeometry(self.rect())
        super().resizeEvent(event)

    # ── run librosa analysis ───────────────────────────────────────────────────
    def run_analysis(self):
        if not self.audio_path:
            QMessageBox.warning(self, "No file", "Please load an audio file first.")
            return

        self.analyze_btn.setEnabled(False)
        self.analyze_btn.setText("Analyzing...")
        self.export_label.hide()

        self.worker = AnalyzeWorker(
            audio_path  = self.audio_path,
            sensitivity = self.sliders["sensitivity"].value() / 100,
            max_markers = self.sliders["max_markers"].value(),
            min_gap     = self.sliders["min_gap"].value(),
            top_n       = self.sliders["top_n"].value(),
        )
        self.worker.finished.connect(self.on_analysis_done)
        self.worker.error.connect(self.on_analysis_error)
        self.worker.start()

    def on_analysis_done(self, csv_path):
        self.analyze_btn.setEnabled(True)
        self.analyze_btn.setText("Analyze and export CSV")

        # inject csv path into resolve script
        self._inject_csv_path(csv_path)

        self.export_label.setText(f"CSV saved to {csv_path}")
        self.export_label.show()

        # update stat cards — pull real values from your analyze module
        try:
            import json
            manifest_path = csv_path.replace(".csv", ".json")
            if os.path.exists(manifest_path):
                with open(manifest_path) as f:
                    m = json.load(f)
                self.stat_labels["BPM"].setText(str(round(m.get("bpm", 0))))
                self.stat_labels["Peaks"].setText(str(m.get("peak_count", "—")))
                self.stat_labels["Beats"].setText(str(m.get("beat_count", "—")))
                self.stat_labels["Mood"].setText(m.get("mood", "—"))
                self.stat_labels["Mood"].setStyleSheet(
                    "font-size: 13px; font-weight: 500; color: #534AB7;"
                )
                # populate timestamps
                for i in reversed(range(self.ts_layout.count())):
                    self.ts_layout.itemAt(i).widget().deleteLater()
                for ts in m.get("top_peaks", [])[:8]:
                    row = QLabel(f"{ts['time_fmt']}  —  {round(ts['strength']*100)}%")
                    row.setStyleSheet("font-size: 11px; font-family: monospace; color: #333;")
                    self.ts_layout.addWidget(row)
        except Exception:
            pass

    def on_analysis_error(self, msg):
        self.analyze_btn.setEnabled(True)
        self.analyze_btn.setText("Analyze and export CSV")
        QMessageBox.critical(self, "Analysis error", msg)

    # ── inject csv path into resolve script ────────────────────────────────────
    def _inject_csv_path(self, csv_path):
        if not os.path.exists(RESOLVE_SCRIPT_PATH):
            return
        with open(RESOLVE_SCRIPT_PATH, "r") as f:
            content = f.read()
        # replaces whatever is currently assigned to CSV_PATH
        import re
        content = re.sub(
            r'CSV_PATH\s*=\s*".*?"',
            f'CSV_PATH = "{csv_path}"',
            content
        )
        with open(RESOLVE_SCRIPT_PATH, "w") as f:
            f.write(content)


# ── main window ────────────────────────────────────────────────────────────────
class BeatFrameApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BeatFrame")
        self.setMinimumSize(680, 520)

        # check for resolve script on startup
        if not os.path.exists(RESOLVE_SCRIPT_PATH):
            dialog = InstallDialog(self)
            dialog.exec()

        # stacked pages
        self.landing  = LandingPage()
        self.analysis = AnalysisPage()

        self.landing.get_started.connect(self.show_analysis)

        self.setCentralWidget(self.landing)

    def show_analysis(self):
        self.setCentralWidget(self.analysis)


# ── entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BeatFrameApp()
    window.show()
    sys.exit(app.exec())