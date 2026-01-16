# Traffic Monitor

This is a **traffic monitoring application** built with **Python**. It uses **Computer Vision** and **Deep Learning** to detect and track vehicles in real-time. The application streams video directly from **YouTube** and shows the results on a **PyQt6 GUI**.

## 🚀 Features

- **Object Detection:** Uses **YOLO11** to detect vehicles with high accuracy.
- **Object Tracking:** Tracks objects smoothly using **ByteTrack**.
- **Live Streaming:** Processes video streams directly from **YouTube** URLs.
- **Performance:** Optimized for **Intel CPUs** using **OpenVINO** (INT8 quantization).
- **GUI:** User-friendly interface built with **PyQt6**.

## 🛠️ Installation

We recommend using **uv** for extremely fast setup and package management.

### Prerequisites

- Python 3.12 or higher.
- **uv** installed.

### Option 1: Using uv (Recommended for Speed)

1. **Clone the repository:**

   ```bash
   git clone [https://github.com/ngxccc/traffic-monitor.git](https://github.com/ngxccc/traffic-monitor.git)
   cd traffic-monitor
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
