# Instant Translator - Real-time Japanese OCR and Translation Overlay

## 📝 Description

**Instant Translator** is a powerful Python application designed to provide real-time, on-screen translation of Japanese text. It functions as a transparent overlay, detecting Japanese characters on your screen, translating them into English, and displaying the English translation directly over the original content. This tool is invaluable for scenarios like live-streaming, gaming, reading untranslated manga, or Browse Japanese websites where direct text selection isn't possible.

The application leverages a robust set of libraries to achieve its functionality:
* **`mss`**: For highly efficient and fast screen capturing.
* **`EasyOCR`**: The backbone for Optical Character Recognition (OCR), adept at identifying Japanese text.
* **`DeepL API`**: Offers high-quality, professional machine translation (preferred when an API key is configured).
* **`Helsinki-NLP MarianMT model`**: Provides a reliable open-source translation alternative if DeepL is unavailable or not configured.
* **`PyQt5`**: Powers the dynamic, transparent, and always-on-top overlay.
* **`pynput`**: Enables seamless global hotkey control for a smooth user experience.

## ✨ Features

* **Real-time OCR & Translation:** Instantly captures your screen, detects Japanese text, and provides an English translation.
* **Flexible Translation Backends:**
    * Prioritizes **DeepL API** for superior translation quality if your API key is provided.
    * Automatically falls back to the **Helsinki-NLP MarianMT model** for Japanese-to-English translation if DeepL is not configured or encounters issues.
* **Dynamic Live Overlay:** Displays English translations directly over the regions where Japanese text was detected, effectively "censoring" the original text with its translation.
* **Transparent & Non-Intrusive:** The overlay is fully transparent to mouse input, allowing you to interact with the underlying applications without hindrance.
* **Intuitive Hotkey Control:** Manage the application's core functions with convenient global keyboard shortcuts:
    * **`Ctrl + Alt + Q`**: Capture a full-screen screenshot, perform OCR, translate, and update the overlay.
    * **`Ctrl + Alt + W`**: Activate a screen region selection mode. Click and drag to define a specific area for OCR and translation.
    * **`Ctrl + Alt + E`**: Clear all currently displayed translations from the overlay.
    * **`Ctrl + Alt + R`**: Exit the Instant Translator application.

## ⚠️ Known Limitations

While effective for many scenarios, please be aware of the following current limitations:

* **Vertical Text and Multiple Rows:** The OCR engine may not accurately detect or correctly order text that is arranged vertically (top-to-bottom writing) or spread across multiple tightly packed lines. This can result in jumbled or incomplete translations for such text layouts.
* **OCR Accuracy:** Like all OCR systems, `EasyOCR`'s accuracy can vary based on font, text size, image quality, and background complexity.
* **Translation Quality:** While Helsinki-NLP offers decent results and DeepL offers good quality and more accurate results, machine translation is not always perfect and may occasionally produce awkward or incorrect phrases.
* **Performance:** OCR and translation can be resource-intensive. Performance may vary depending on your system specifications, especially without a dedicated GPU.

## 🚀 Getting Started

Follow these steps to set up and run the application on your system.

### Prerequisites

* **Python Version:** Python 3.8 to 3.10 is recommended.
* **Internet Connection:** Required for initial model downloads (EasyOCR, Helsinki-NLP) and for DeepL API calls.
* **GPU (Recommended):** An NVIDIA GPU with compatible drivers will significantly accelerate OCR and translation processes (via `torch`). While not strictly required, performance will be noticeably better with one.

### 1. Clone the Repository

Begin by cloning the project repository to your local machine:

```bash
git clone [https://github.com/Ciuflea-Alexandru/Instant-Translator.git](https://github.com/Ciuflea-Alexandru/Instant-Translator.git)
cd Instant-Translator