# License Plate Monitor

This is a **license plate monitoring application**. It is built with **Python**. The app uses **Computer Vision** and **Deep Learning** to find cars and read their license plates in real-time. It can process video from **YouTube** directly. The app shows results on a simple **PyQt6 GUI**.

## 🚀 Features

- **Vehicle Detection:** Uses **YOLO26** model to find and track vehicles.
- **Object Tracking:** Follows vehicles smoothly with **ByteTrack** algorithm.
- **License Plate Recognition:** Can detect and read license plates automatically.
- **YouTube Streaming:** Works with video from **YouTube URLs** without downloading.
- **Fast Performance:** Optimized for **Intel CPUs** using **OpenVINO** (INT8 quantization).
- **Simple GUI:** Easy-to-use interface built with **PyQt6**.

## 🛠️ Installation

We recommend using **uv** for extremely fast setup and package management.

### Prerequisites

- Python 3.12 or higher.
- **uv** installed.

### Option 1: Using uv (Recommended for Speed)

1. **Clone the repository:**

   ```bash
   git clone [https://github.com/ngxccc/license-plate-monitor.git](https://github.com/ngxccc/license-plate-monitor.git)
   cd license-plate-monitor
   ```

2. **Install dependencies:**
   This command creates a virtual environment and installs all required packages.

   ```bash
   uv sync
   ```

### Option 2: Using venv (Standard)

If you prefer the standard Python tools, use **venv**.

1. **Create a virtual environment:**

    ```bash
    uv venv
    ```

2. **Activate the environment:**

    - **Windows:**

      ```bash
      .venv\Scripts\activate
      ```

    - **macOS / Linux:**

      ```bash
      source venv/bin/activate
      ```

3. **Install the package:**

    ```bash
    uv pip install .[dev]
    ```

## 🧠 Model Export (OpenVINO)

To get the best performance on Intel CPUs, you must export the YOLO model to **OpenVINO** format with **INT8** quantization.

Run this command in your terminal:

```bash
yolo export model=path-to-your-model/yolo.pt format=openvino int8=True
```

## ▶️ Usage

Start the application using **uv**:

```bash
uv run traffic-app
```

Or run with Python directly:

```bash
python -m traffic_monitor
```
