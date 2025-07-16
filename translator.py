import sys
import mss
import easyocr
from PIL import Image, ImageDraw
from PyQt5.QtWidgets import QApplication, QWidget, QLabel
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
from pynput import keyboard
import io
import deepl
from transformers import MarianMTModel, MarianTokenizer

# Translation Model Imports (Optional)
# DeepL imports
try:
    # THIS IS WHERE YOU PLACE YOUR DEEPL AUTH KEY!!!
    DEEPL_AUTH_KEY = ''
    if DEEPL_AUTH_KEY:
        deepl_translator = deepl.Translator(DEEPL_AUTH_KEY)
        print("DeepL API key found. DeepL will be used for translation.")
    else:
        deepl_translator = None
        print("DEEPL_AUTH_KEY environment variable not set. Falling back to Helsinki-NLP model.")
except ImportError:
    deepl_translator = None
    print("DeepL library not found. Falling back to Helsinki-NLP model.")

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

# Initialize EasyOCR reader once
# 'ja' for Japanese, 'en' for English (can help with mixed text, though we filter for Japanese)
reader = easyocr.Reader(['ja', 'en'], gpu=True)  # Change gpu=True to gpu=False if no GPU


def take_screenshot():
    with mss.mss() as sct:
        monitor = sct.monitors[1]  # Assuming monitor 1 is your primary monitor
        shot = sct.grab(monitor)
        img = Image.frombytes('RGB', shot.size, shot.rgb)
        return img


# This filter is useful as EasyOCR might detect non-Japanese,
def contains_japanese(text):
    return any('\u3040' <= c <= '\u30FF' or '\u4e00' <= c <= '\u9faf' for c in text)


def translate_japanese(text):
    if not text:
        return ""

    # --- Conditional Translation Logic ---
    if deepl_translator:
        try:
            # DeepL automatically detects source language if not specified
            # But specifying 'JA' for Japanese is apparently good practice so...
            result = deepl_translator.translate_text(text, target_lang="EN-US", source_lang="JA")
            return result.text
        except deepl.exceptions.DeepLException as e:
            print(f"DeepL translation error: {e}. Falling back to Helsinki-NLP if available.")
            # If DeepL fails, try Helsinki-NLP if available
            if tokenizer and model:
                inputs = tokenizer([text], return_tensors="pt", padding=True, truncation=True)
                translated_tokens = model.generate(**inputs)
                return tokenizer.decode(translated_tokens[0], skip_special_tokens=True)
            else:
                return f"[DeepL Error] {text}"
        except Exception as e:
            print(f"An unexpected error occurred during DeepL translation: {e}."
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


def get_bounding_boxes(image, min_confidence=0):  # EasyOCR confidence is typically 0.0 to 1.0
    import numpy as np
    opencv_img = np.array(image)
    results = reader.readtext(opencv_img)
    width, height = image.size
    boxes = []

    for (bbox_coords, text, conf) in results:
        text = text.strip()

        if text and conf >= min_confidence and contains_japanese(text):
            x1, y1 = int(bbox_coords[0][0]), int(bbox_coords[0][1])
            x2, y2 = int(bbox_coords[2][0]), int(bbox_coords[2][1])
            translated = translate_japanese(text)
            boxes.append((x1, y1, x2, y2, translated))

    return boxes, (width, height)


class CensorOverlay(QWidget):
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
        self.setGeometry(0, 0, QApplication.desktop().width(), QApplication.desktop().height())
        self.label = QLabel(self)
        self.label.setGeometry(0, 0, self.width(), self.height())

    def update_overlay(self):
        if not reference_boxes:
            self.label.clear()
            return

        overlay = Image.new("RGBA", screenshot_size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # Try to load a suitable font, or fall back to default
        try:
            # You might need to adjust this path based on your system.
            # Common default fonts are 'arial.ttf', 'DejaVuSans.ttf', 'Meiryo.ttc' (Windows Japanese)
            # Make sure the font supports Japanese if you decide to display original text too.
            from PIL import ImageFont
            font = ImageFont.truetype("DejaVuSans.ttf", 14)  # Or 'arial.ttf', 'NotoSans-Regular.ttf' etc.
        except IOError:
            print("Warning: Could not load specified font. Using default PIL font.")
            font = ImageFont.load_default()  # Fallback to default PIL font

        for (x1, y1, x2, y2, translation) in reference_boxes:
            draw.rectangle([x1, y1, x2, y2], fill=(0, 0, 0, 200))
            draw.text((x1 + 2, y1 + 2), translation, fill=(255, 255, 255, 255), font=font)

        byte_arr = io.BytesIO()
        overlay.save(byte_arr, format='PNG')
        pixmap = QPixmap()
        pixmap.loadFromData(byte_arr.getvalue(), 'PNG')
        self.label.setPixmap(pixmap)


def on_press(key):
    global reference_boxes, screenshot_size
    try:
        if key == keyboard.Key.f8:
            print("F8 pressed: taking screenshot and detecting text (EasyOCR)...")
            img = take_screenshot()
            reference_boxes, screenshot_size = get_bounding_boxes(img)
            overlay_window.update_overlay()
            print(f"Applied censorship to {len(reference_boxes)} regions.")
        elif key == keyboard.Key.f9:
            print("F9 pressed: clearing overlay.")
            reference_boxes.clear()
            overlay_window.update_overlay()
        elif key == keyboard.Key.f10:
            print("F10 pressed: exiting application.")
            QApplication.quit()
    except Exception as e:
        print(f"Error: {e}")


def main():
    global overlay_window
    app = QApplication(sys.argv)
    overlay_window = CensorOverlay()
    overlay_window.show()

    listener = keyboard.Listener(on_press=on_press)
    listener.start()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
