import sys
import mss
import easyocr
from PIL import Image, ImageDraw, ImageFont
from PyQt5.QtWidgets import QApplication, QWidget, QLabel
from PyQt5.QtGui import QPixmap, QPainter, QColor
from PyQt5.QtCore import Qt, QPoint, QRect, pyqtSignal
from pynput import keyboard
import io
import deepl
from transformers import MarianMTModel, MarianTokenizer

# Import font_manager for cross-platform font discovery
try:
    import matplotlib.font_manager as fm
    print("matplotlib.font_manager loaded for better font discovery.")
except ImportError:
    fm = None
    print("matplotlib not found. Font discovery will rely on direct paths or default.")

# Translation Model Imports (Optional)
# DeepL imports
try:
    # THIS IS WHERE YOU PLACE YOUR DEEPL AUTH KEY!!!
    DEEPL_AUTH_KEY = ''  # Replace with your DeepL Auth Key
    if DEEPL_AUTH_KEY:
        deepl_translator = deepl.Translator(DEEPL_AUTH_KEY)
        print("DeepL API key found. DeepL will be used for translation.")
    else:
        deepl_translator = None
        print("DEEPL_AUTH_KEY is empty. Falling back to Helsinki-NLP model.")
except ImportError:
    deepl_translator = None
    print("DeepL library not found. Falling back to Helsinki-NLP model.")
except Exception as e:
    deepl_translator = None
    print(f"Error initializing DeepL translator: {e}. Falling back to Helsinki-NLP model.")


# Helsinki-NLP imports (only if DeepL is not going to be used)
if not deepl_translator:
    try:
        tokenizer = MarianTokenizer.from_pretrained("Helsinki-NLP/opus-mt-ja-en")
        model = MarianMTModel.from_pretrained("Helsinki-NLP/opus-mt-ja-en")
        print("Helsinki-NLP model loaded for translation.")
    except ImportError:
        print("Helsinki-NLP transformers library not found. Translation will not be available.")
        tokenizer = None
        model = None
    except Exception as e:
        print(f"Error loading Helsinki-NLP model: {e}. Translation will not be available.")
        tokenizer = None
        model = None


# Globals
reference_boxes = []
screenshot_size = (0, 0)
overlay_window = None # Will be initialized in main
selection_window = None # Will be initialized in main
current_keys = set()

# Initialize EasyOCR reader once
# 'ja' for Japanese, 'en' for English (can help with mixed text, though we filter for Japanese)
reader = easyocr.Reader(['ja', 'en'], gpu=True)  # Change gpu=True to gpu=False if no GPU


def take_screenshot(region=None):
    # Captures a screenshot, if 'region' is provided as (x, y, width, height), captures only that region.
    with mss.mss() as sct:
        # Get all monitors and find the one containing the region
        if region:
            monitor = {
                "top": region[1],
                "left": region[0],
                "width": region[2],
                "height": region[3],
                "monid": 1  # Assume primary monitor for region grab
            }
        else:
            # Assuming monitor 1 is your primary monitor. Adjust if needed.
            monitor = sct.monitors[1]

        shot = sct.grab(monitor)
        img = Image.frombytes('RGB', shot.size, shot.rgb)
        return img


def contains_japanese(text):
    # Checks if the given text contains Japanese characters
    return any('\u3040' <= c <= '\u30FF' or '\u4e00' <= c <= '\u9faf' for c in text)


def translate_japanese(text):
    # Translates Japanese text to English using DeepL or Helsinki-NLP
    if not text:
        return ""

    # Conditional Translation Logic
    if deepl_translator:
        try:
            # Specify 'JA' for source language and 'EN-US' for target language
            result = deepl_translator.translate_text(text, target_lang="EN-US", source_lang="JA")
            return result.text
        except deepl.exceptions.DeepLException as e:
            print(f"DeepL translation error: {e}. Falling back to Helsinki-NLP if available.")
            if tokenizer and model:
                inputs = tokenizer([text], return_tensors="pt", padding=True, truncation=True)
                translated_tokens = model.generate(**inputs)
                return tokenizer.decode(translated_tokens[0], skip_special_tokens=True)
            else:
                return f"[DeepL Error] {text}"
        except Exception as e:
            print(f"An unexpected error occurred during DeepL translation: {e}. "
                  f"Falling back to Helsinki-NLP if available.")
            if tokenizer and model:
                inputs = tokenizer([text], return_tensors="pt", padding=True, truncation=True)
                translated_tokens = model.generate(**inputs)
                return tokenizer.decode(translated_tokens[0], skip_special_tokens=True)
            else:
                return f"[DeepL Error] {text}"
    elif tokenizer and model:
        inputs = tokenizer([text], return_tensors="pt", padding=True, truncation=True)
        translated_tokens = model.generate(**inputs)
        return tokenizer.decode(translated_tokens[0], skip_special_tokens=True)
    else:
        print("No translation service available.")
        return f"[No Translator] {text}"


def get_bounding_boxes(image, min_confidence=0.0):
    """
    Performs OCR on the image to detect Japanese text and its bounding boxes.
    Translates the detected text. Also prints the original and translated text to terminal.
    """
    import numpy as np
    opencv_img = np.array(image)
    results = reader.readtext(opencv_img)
    width, height = image.size
    boxes = []

    for (bbox_coords, original_text, conf) in results: # 'original_text' is the raw detected text
        original_text = original_text.strip()

        if original_text and conf >= min_confidence and contains_japanese(original_text):
            x1, y1 = int(bbox_coords[0][0]), int(bbox_coords[0][1])
            x2, y2 = int(bbox_coords[2][0]), int(bbox_coords[2][1])
            translated_text = translate_japanese(original_text)
            boxes.append((x1, y1, x2, y2, translated_text))
            # Print original and translated text to the terminal
            print(f"Detected: '{original_text}' (Confidence: {conf:.2f}), Translated: '{translated_text}'")

    return boxes, (width, height)


class CensorOverlay(QWidget):
    # A transparent, always-on-top overlay window to display censored regions and their translations.
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Screenshot Censor Overlay")
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.Tool |
            Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        # Set the overlay to cover the entire screen
        self.setGeometry(0, 0, QApplication.desktop().width(), QApplication.desktop().height())
        self.label = QLabel(self)
        self.label.setGeometry(0, 0, self.width(), self.height())
        self._loaded_font = None # Cache the loaded font

    def _get_font(self, size):
        # Attempts to load a suitable font cross-platform
        if self._loaded_font:
            return self._loaded_font

        font_name_preferences = ['Arial', 'DejaVu Sans', 'Noto Sans']  # Common fonts
        font_path = None

        # 1. Try finding via matplotlib.font_manager
        if fm:
            for font_name in font_name_preferences:
                try:
                    font_path = fm.findfont(fm.FontProperties(family=font_name), fontext='ttf')
                    if font_path:
                        print(f"Found font '{font_name}' via font_manager at: {font_path}")
                        break
                except Exception as e:
                    # print(f"Error finding font '{font_name}' with font_manager: {e}")
                    pass  # Continue to next font or fallback

        # 2. Fallback to common hardcoded paths if font_manager didn't find one
        if not font_path:
            # Common Windows paths
            if sys.platform == "win32":
                common_paths = [
                    "C:/Windows/Fonts/arial.ttf",
                    "C:/Windows/Fonts/meiryo.ttc",  # For better Japanese support
                    "C:/Windows/Fonts/msgothic.ttc"  # Another Windows Japanese font
                ]
            # Common Linux paths
            elif sys.platform.startswith("linux"):
                common_paths = [
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
                    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
                ]
            # Common macOS paths
            elif sys.platform == "darwin":
                 common_paths = [
                    "/System/Library/Fonts/Supplemental/Arial.ttf",
                    "/Library/Fonts/Arial.ttf"
                 ]
            else:
                common_paths = [] # Unknown OS

            for path in common_paths:
                try:
                    # Attempt to load just to check if the path is valid
                    ImageFont.truetype(path, size)
                    font_path = path
                    print(f"Found font at hardcoded path: {font_path}")
                    break
                except IOError:
                    pass

        # 3. Load font or fallback to default
        try:
            if font_path:
                self._loaded_font = ImageFont.truetype(font_path, size)
            else:
                raise IOError("No suitable font path found among preferred and common paths.")
        except IOError:
            print("Warning: Could not load any specified font. Using default PIL font.")
            self._loaded_font = ImageFont.load_default()

        return self._loaded_font

    def update_overlay(self):
        # Updates the overlay with new censorship boxes and translations.
        if not reference_boxes or screenshot_size == (0, 0):
            self.label.clear()
            return

        overlay = Image.new("RGBA", screenshot_size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        font = self._get_font(14)  # Get the cached font or load it

        for (x1, y1, x2, y2, translation) in reference_boxes:
            # Draw a semi-transparent black rectangle for censorship
            draw.rectangle([x1, y1, x2, y2], fill=(0, 0, 0, 200))
            # Draw the translated text on top of the censored area
            draw.text((x1 + 2, y1 + 2), translation, fill=(255, 255, 255, 255), font=font)

        byte_arr = io.BytesIO()
        overlay.save(byte_arr, format='PNG')
        pixmap = QPixmap()
        pixmap.loadFromData(byte_arr.getvalue(), 'PNG')
        self.label.setPixmap(pixmap)


class SelectionWindow(QWidget):
    # A transparent window that allows the user to select a rectangular region of the screen using mouse drag
    selection_finished = pyqtSignal(tuple)  # Signal to emit selected coordinates (x, y, width, height)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Select Region")
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setGeometry(0, 0, QApplication.desktop().width(), QApplication.desktop().height())
        self.setCursor(Qt.CrossCursor)

        self.start_point = QPoint()
        self.end_point = QPoint()
        self.selecting = False

    def paintEvent(self, event):
        """Draws the selection rectangle."""
        painter = QPainter(self)
        painter.setPen(QColor(255, 0, 0, 200))  # Red pen for rectangle border
        painter.setBrush(QColor(255, 255, 0, 50))  # Semi-transparent yellow fill

        if self.selecting:
            rect = QRect(self.start_point, self.end_point).normalized()
            painter.drawRect(rect)

    def mousePressEvent(self, event):
        # Records the starting point of the selection or cancels on right-click
        if event.button() == Qt.LeftButton:
            self.start_point = event.pos()
            self.selecting = True
            self.update()  # Redraw to show start of selection
        elif event.button() == Qt.RightButton:
            print("Region selection cancelled by right-click.")
            self.selecting = False
            self.hide()  # Hide selection window
            if overlay_window:  # Ensure overlay_window exists before showing
                overlay_window.show()  # Bring back the main overlay
            self.start_point = QPoint()  # Reset points for next selection
            self.end_point = QPoint()

    def mouseMoveEvent(self, event):
        # Updates the end point of the selection as the mouse moves.
        if self.selecting:
            self.end_point = event.pos()
            self.update()  # Redraw to show current selection rectangle

    def mouseReleaseEvent(self, event):
        # Finalizes the selection and emits the coordinates
        if event.button() == Qt.LeftButton:
            self.end_point = event.pos()
            self.selecting = False
            self.hide()  # Hide selection window immediately

            # Calculate the actual screen coordinates
            rect = QRect(self.start_point, self.end_point).normalized()
            x = self.x() + rect.x()
            y = self.y() + rect.y()
            width = rect.width()
            height = rect.height()

            if width > 0 and height > 0:
                self.selection_finished.emit((x, y, width, height))
            else:
                print("Selection too small or invalid. No OCR performed.")

            if overlay_window:
                overlay_window.show()


def process_selected_region(region_coords):
    # Slot to receive selected region coordinates, take screenshot, perform OCR, and update the overlay.
    global reference_boxes, screenshot_size

    print(f"\n--- Processing selected region (x={region_coords[0]}, y={region_coords[1]}, w={region_coords[2]}, h={region_coords[3]}) ---")
    x, y, width, height = region_coords
    img = take_screenshot(region=(x, y, width, height))
    # For displaying the overlay correctly, we need the *original*
    # coordinates relative to the full screen, not relative to the cropped image.
    # The OCR results (x1, y1, x2, y2) will be relative to the cropped image.
    # So, we need to adjust them by adding the offset of the selected region.
    detected_boxes_relative, _ = get_bounding_boxes(img)

    adjusted_boxes = []
    for (rel_x1, rel_y1, rel_x2, rel_y2, translation) in detected_boxes_relative:
        abs_x1 = x + rel_x1
        abs_y1 = y + rel_y1
        abs_x2 = x + rel_x2
        abs_y2 = y + rel_y2
        adjusted_boxes.append((abs_x1, abs_y1, abs_x2, abs_y2, translation))

    reference_boxes = adjusted_boxes
    # Set screenshot_size to the full desktop size so the overlay spans correctly
    screenshot_size = (QApplication.desktop().width(), QApplication.desktop().height())
    overlay_window.update_overlay()
    overlay_window.show()  # Make sure overlay is visible after selection
    print("--------------------------------------------------\n")


def on_press(key):
    try:
        current_keys.add(key)
        # Check for Ctrl + Alt combination
        if (keyboard.Key.ctrl_l in current_keys or keyboard.Key.ctrl_r in current_keys) and \
           (keyboard.Key.alt_l in current_keys or keyboard.Key.alt_r in current_keys):
            if hasattr(key, 'char'):
                # Check for Ctrl + Alt + Q
                if key.char in ('q', 'Q'):
                    print("\n--- Ctrl+Alt+Q pressed: taking full screenshot and detecting text (EasyOCR) ---")
                    global reference_boxes, screenshot_size
                    img = take_screenshot()
                    screenshot_size = (img.width, img.height)  # Update global screenshot_size
                    reference_boxes, _ = get_bounding_boxes(img)
                    overlay_window.update_overlay()
                    overlay_window.show()
                    print(f"Applied censorship to {len(reference_boxes)} regions.")
                    print("--------------------------------------------------\n")
                # Check for Ctrl + Alt + R (New combination for region selection)
                elif key.char in ('w', 'W'):
                    print("Ctrl+Alt+W pressed: Activating region selection.")
                    overlay_window.hide()  # Hide the censor overlay during selection
                    selection_window.showFullScreen()  # Show selection window to cover screen
                # Check for Ctrl + Alt + W
                elif key.char in ('e', 'E'):
                    print("Ctrl+Alt+E pressed: clearing overlay.")
                    reference_boxes.clear()
                    overlay_window.update_overlay()
                # Check for Ctrl + Alt + E
                elif key.char in ('r', 'R'):
                    print("Ctrl+Alt+r pressed: exiting application.")
                    QApplication.quit()

    except Exception as e:
        print(f"Error in on_press: {e}")


def on_release(key):
    # Handles key release events
    try:
        current_keys.discard(key)
    except Exception as e:
        print(f"Error in on_release: {e}")


def main():
    # Main function to initialize and run the application
    global overlay_window, selection_window
    app = QApplication(sys.argv)

    overlay_window = CensorOverlay()
    overlay_window.show()

    selection_window = SelectionWindow()
    selection_window.selection_finished.connect(process_selected_region)

    # Set up keyboard listener
    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
