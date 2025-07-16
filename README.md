# Instant Translator - Real-time Japanese OCR and Translation Overlay

## 📝 Description

This Python application provides a real-time overlay on your screen that detects Japanese text, translates it into English, and displays the translation over the original text. It's designed to be useful for tasks like live translation during gaming, streaming, or reading untranslated content on your screen.

The application uses a powerful combination of:
* **`mss`** for efficient screen capturing.
* **`EasyOCR`** for robust Optical Character Recognition (OCR) to detect Japanese text.
* **`DeepL API`** for high-quality machine translation (preferred if API key is provided).
* **`Helsinki-NLP MarianMT model`** as a fallback for translation if a DeepL API key is not configured.
* **`PyQt5`** for creating a transparent, always-on-top overlay.
* **`pynput`** for global hotkey control.

## ✨ Features

* **Real-time OCR:** Detects Japanese text on your primary monitor.
* **Dual Translation Support:** Prioritizes DeepL for high-quality translations if an API key is provided; otherwise, it seamlessly falls back to the open-source Helsinki-NLP MarianMT model.
* **Live Overlay:** Displays English translations directly over the detected Japanese text regions.
* **Transparent Overlay:** Allows interaction with applications underneath.
* **Hotkey Control:**
    * **`F8`**: Capture screenshot, perform OCR, translate, and update the overlay.
    * **`F9`**: Clear the translation overlay.
    * **`F10`**: Exit the application.

## 🚀 Getting Started

Follow these steps to set up and run the application.

### Prerequisites

* Python 3.8 or higher.
* A stable internet connection for initial model downloads (EasyOCR, Helsinki-NLP, DeepL API calls).
* (Optional but Recommended) An NVIDIA GPU with compatible drivers for faster OCR and translation with `torch`.

### 1. Clone the Repository

First, clone this repository to your local machine:

```bash
git clone https://github.com/Ciuflea-Alexandru/Instant-Translator.git
cd Instant-Translator