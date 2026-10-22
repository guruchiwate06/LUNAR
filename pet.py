"""
pet.py - Animated desktop pet widget using PyQt6 with per-pixel transparency.
Features smooth physics-based bobbing, autonomous lifelike behaviors (blink, look, turn),
click responsiveness (happy bounce, wake-up), auto-sleep after idle timeout, and
persistent screen positioning.
"""
import os
import sys
import json
import math
import random
import time
from PyQt6.QtWidgets import QApplication, QWidget, QMenu
from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import QPixmap, QPainter, QAction, QColor

# ==============================================================================
# CONFIGURATION CONSTANTS (Adjustable)
# ==============================================================================
SPRITE_HEIGHT = 210       # On-screen height of the sprite in pixels
BOB_SPEED = 0.05          # Speed of the floating sine-wave bob (radians/frame)
BOB_HEIGHT = 11           # Maximum vertical amplitude of the bob in pixels
SLEEP_TIMEOUT = 60.0      # Seconds of inactivity before falling asleep
FPS = 60                  # Frame rate for buttery-smooth animations

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "pet_position.json")
SPRITES_DIR = os.path.join(SCRIPT_DIR, "sprites")


class DesktopPet(QWidget):
    def __init__(self):
        super().__init__()

        # Window styling: Frameless, transparent, tool (hidden from taskbar)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)

        self.always_on_top = True
        self.sprite_height = SPRITE_HEIGHT
        self.sprite_width = SPRITE_HEIGHT  # 1:1 aspect ratio square canvases

        # Window padding to accommodate vertical bob without clipping
        self.padding_x = 10
        self.padding_y = BOB_HEIGHT + 14
        self.window_width = self.sprite_width + self.padding_x * 2
        self.window_height = self.sprite_height + self.padding_y * 2
        self.setFixedSize(self.window_width, self.window_height)

        # Load sprites
        self.sprites = {}
        self.load_sprites()

        # Animation & Physics State
        self.current_state = "idle"        # "idle", "blink", "look", "turn", "happy", "sleep"
        self.current_pixmap_name = "idle"
        self.bob_phase = 0.0
        self.bob_offset_y = 0.0
        self.last_interaction_time = time.time()

        # Timers / State Durations
        self.state_end_time = 0.0
        self.next_blink_time = time.time() + random.uniform(3.0, 7.0)
        self.next_look_time = time.time() + random.uniform(10.0, 18.0)
        self.next_turn_time = time.time() + random.uniform(18.0, 30.0)

        # Drag tracking
        self.drag_position = QPoint()
        self.is_dragging = False
        self.drag_moved = False

        # Restore saved coordinates or center at bottom-right
        self.restore_position()

        # Master Animation Loop Timer (60 FPS)
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.update_animation)
        self.anim_timer.start(int(1000 / FPS))

        self.show()
        self.raise_()
        self.activateWindow()

    def load_sprites(self):
        """Loads and scales all 8 transparent sprites into QPixmaps."""
        names = ["idle", "blink", "happy", "float_up", "float_down", "sleep", "look", "turn"]
        for name in names:
            path = os.path.join(SPRITES_DIR, f"{name}.png")
            if os.path.exists(path):
                pm = QPixmap(path)
                scaled_pm = pm.scaled(
                    self.sprite_width,
                    self.sprite_height,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.sprites[name] = scaled_pm
            else:
                print(f"Warning: Sprite '{path}' not found. Please run prepare_sprites.py first.")
                # Fallback transparent pixmap
                empty = QPixmap(self.sprite_width, self.sprite_height)
                empty.fill(QColor(0, 0, 0, 0))
                self.sprites[name] = empty

    def restore_position(self):
        """Restores position from JSON or docks above bottom-right taskbar."""
        screen = QApplication.primaryScreen().availableGeometry()
        default_x = screen.right() - self.window_width - 30
        default_y = screen.bottom() - self.window_height - 30

        pos_x, pos_y = default_x, default_y

        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                    px = data.get("x")
                    py = data.get("y")
                    self.always_on_top = data.get("always_on_top", True)
                    # Verify on-screen
                    if px is not None and py is not None:
                        if -self.window_width < px < screen.right() + 500 and -self.window_height < py < screen.bottom() + 500:
                            pos_x, pos_y = px, py
            except Exception as e:
                print(f"Notice: Could not load position config: {e}")

        self.apply_always_on_top(self.always_on_top)
        self.move(int(pos_x), int(pos_y))

    def save_position(self):
        """Saves current window coordinates to CONFIG_FILE."""
        try:
            data = {
                "x": self.x(),
                "y": self.y(),
                "always_on_top": self.always_on_top,
            }
            with open(CONFIG_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Notice: Could not save position: {e}")

    def apply_always_on_top(self, enable: bool):
        """Toggles the WindowStaysOnTopHint."""
        self.always_on_top = enable
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if enable:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.show()

    # ==============================================================================
    # ANIMATION STATE MACHINE
    # ==============================================================================
    def trigger_interaction(self):
        """Resets idle timer and wakes up or triggers happy bounce."""
        self.last_interaction_time = time.time()
        if self.current_state == "sleep":
            self.wake_up()
        else:
            self.set_state("happy", duration=2.0)

    def set_state(self, state: str, duration: float = 0.0):
        self.current_state = state
        self.state_end_time = time.time() + duration if duration > 0 else 0.0

    def wake_up(self):
        """Wakes up from sleep to happy."""
        self.last_interaction_time = time.time()
        self.set_state("happy", duration=2.2)

    def fall_asleep(self):
        """Transitions into sleep state."""
        self.set_state("sleep")

    def update_animation(self):
        now = time.time()

        # Check for state expiration
        if self.state_end_time > 0 and now >= self.state_end_time:
            self.state_end_time = 0.0
            self.current_state = "idle"

        # Check auto-sleep timeout
        if self.current_state not in ("sleep", "happy") and (now - self.last_interaction_time >= SLEEP_TIMEOUT):
            self.fall_asleep()

        # Autonomous behaviors during IDLE
        if self.current_state == "idle":
            # Blink check
            if now >= self.next_blink_time:
                self.set_state("blink", duration=0.15)
                self.next_blink_time = now + random.uniform(3.0, 7.0)
            # Look around check
            elif now >= self.next_look_time:
                look_dur = random.uniform(1.2, 2.0)
                self.set_state("look", duration=look_dur)
                self.next_look_time = now + look_dur + random.uniform(12.0, 22.0)
            # Turn check
            elif now >= self.next_turn_time:
                turn_dur = random.uniform(0.6, 0.9)
                self.set_state("turn", duration=turn_dur)
                self.next_turn_time = now + turn_dur + random.uniform(18.0, 30.0)

        # Physics & bob offset calculations based on state
        if self.current_state == "sleep":
            # Gentle, slow breathing motion
            self.bob_phase += BOB_SPEED * 0.4
            self.bob_offset_y = (BOB_HEIGHT * 0.35) * math.sin(self.bob_phase)
            self.current_pixmap_name = "sleep"

        elif self.current_state == "happy":
            # Energetic, excited bounce
            self.bob_phase += BOB_SPEED * 2.8
            self.bob_offset_y = -abs((BOB_HEIGHT * 1.6) * math.sin(self.bob_phase))
            self.current_pixmap_name = "happy"

        elif self.current_state == "blink":
            self.bob_phase += BOB_SPEED
            self.bob_offset_y = BOB_HEIGHT * math.sin(self.bob_phase)
            self.current_pixmap_name = "blink"

        elif self.current_state == "look":
            self.bob_phase += BOB_SPEED * 0.5
            self.bob_offset_y = (BOB_HEIGHT * 0.5) * math.sin(self.bob_phase)
            self.current_pixmap_name = "look"

        elif self.current_state == "turn":
            self.bob_phase += BOB_SPEED * 0.5
            self.bob_offset_y = (BOB_HEIGHT * 0.5) * math.sin(self.bob_phase)
            self.current_pixmap_name = "turn"

        else:
            # Standard IDLE: Smooth sine-wave floating bob, alternating float_up and float_down
            self.bob_phase += BOB_SPEED
            self.bob_offset_y = BOB_HEIGHT * math.sin(self.bob_phase)

            # Velocity is derivative of sine: cos(phase)
            # Moving up: velocity is negative
            # Moving down: velocity is positive
            velocity = math.cos(self.bob_phase)
            if velocity < -0.32:
                self.current_pixmap_name = "float_up"
            elif velocity > 0.32:
                self.current_pixmap_name = "float_down"
            else:
                self.current_pixmap_name = "idle"

        # Request repaint
        self.update()

    # ==============================================================================
    # PAINT EVENT (Smooth per-pixel rendering with anti-aliasing)
    # ==============================================================================
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        pixmap = self.sprites.get(self.current_pixmap_name)
        if pixmap and not pixmap.isNull():
            draw_x = self.padding_x
            draw_y = int(self.padding_y + self.bob_offset_y)
            painter.drawPixmap(draw_x, draw_y, pixmap)

    # ==============================================================================
    # MOUSE EVENTS (Draggable & Clickable)
    # ==============================================================================
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.is_dragging = True
            self.drag_moved = False
            self.last_interaction_time = time.time()
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            self.show_context_menu(event.globalPosition().toPoint())
            event.accept()

    def mouseMoveEvent(self, event):
        if self.is_dragging and (event.buttons() & Qt.MouseButton.LeftButton):
            new_pos = event.globalPosition().toPoint() - self.drag_position
            # Only count as drag if moved more than 2 pixels
            if (new_pos - self.pos()).manhattanLength() > 2:
                self.drag_moved = True
            self.move(new_pos)
            self.last_interaction_time = time.time()
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False
            self.save_position()
            if not self.drag_moved:
                # User clicked without dragging: trigger interaction
                self.trigger_interaction()
            event.accept()

    def show_context_menu(self, global_pos: QPoint):
        """Displays right-click context menu."""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1e222d;
                color: #e2e8f0;
                border: 1px solid #3b4252;
                border-radius: 8px;
                padding: 4px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #3b82f6;
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background-color: #333c4d;
                margin: 4px 8px;
            }
        """)

        # Sleep action
        sleep_act = QAction("Sleep", self)
        sleep_act.triggered.connect(self.fall_asleep)
        menu.addAction(sleep_act)

        # Wake action
        wake_act = QAction("Wake", self)
        wake_act.triggered.connect(self.wake_up)
        menu.addAction(wake_act)

        menu.addSeparator()

        # Always on top toggle action
        top_act = QAction("Always on Top", self)
        top_act.setCheckable(True)
        top_act.setChecked(self.always_on_top)
        top_act.triggered.connect(lambda checked: self.toggle_always_on_top(checked))
        menu.addAction(top_act)

        # LUNAR Assistant integration
        assistant_act = QAction("Open LUNAR Assistant", self)
        assistant_act.triggered.connect(self.launch_lunar_assistant)
        menu.addAction(assistant_act)

        menu.addSeparator()

        # Quit action
        quit_act = QAction("Quit", self)
        quit_act.triggered.connect(self.quit_app)
        menu.addAction(quit_act)

        menu.exec(global_pos)

    def launch_lunar_assistant(self):
        """Launches the main LUNAR GUI assistant."""
        import subprocess
        gui_path = os.path.join(os.path.dirname(__file__), "gui_assistant.py")
        if os.path.exists(gui_path):
            subprocess.Popen([sys.executable, gui_path])

    def mouseDoubleClickEvent(self, event):
        """Double clicking mascot opens the LUNAR Assistant GUI."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.launch_lunar_assistant()
            event.accept()

    def toggle_always_on_top(self, checked: bool):
        self.apply_always_on_top(checked)
        self.save_position()

    def quit_app(self):
        self.save_position()
        QApplication.quit()

    def closeEvent(self, event):
        self.save_position()
        event.accept()


def main():
    app = QApplication(sys.argv)
    # Ensure application doesn't exit if hidden or minimized
    app.setQuitOnLastWindowClosed(True)
    pet = DesktopPet()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
