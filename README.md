# ParkiMotion

**Academic Thesis Project – Electronics Engineering, Universidad del Valle**

---

## Overview

ParkiMotion is an embedded system designed to emulate Parkinsonian tremors for rehabilitation research. The project addresses the need for controlled, repeatable tremor generation to evaluate therapies and devices for Parkinson’s disease. ParkiMotion combines real-time motor control, inertial sensing, and a Python Dash interface for data analysis and visualization.

---

## System Architecture

ParkiMotion consists of two main components:

- **ESP32 Firmware**: Implements closed-loop vibration control using FreeRTOS, a PID controller, and an MPU6050 IMU. The firmware reads IMU data at 100 Hz, applies digital filtering, and communicates with the host via UART.
- **Python Dash Interface**: Provides real-time monitoring, FFT analysis, filtering, and statistical tools (including t-Student tests) for protocol evaluation and patient results.

![System Architecture](/assets/architecture.png)

---

## Module Overview

| Module        | Description                                                                 |
| ------------- | --------------------------------------------------------------------------- |
| IMU           | Reads acceleration and gyroscope data from MPU6050 at 100 Hz                |
| PID           | Closed-loop control for precise vibration generation                        |
| UART          | Serial communication between ESP32 and Python Dash interface                |
| Filtering     | Butterworth band-pass filter (3–7 Hz) for tremor signal isolation           |
| FFT           | Fast Fourier Transform (Hann window) for frequency analysis                 |
| Dash App      | Real-time data visualization, protocol management, and statistical analysis |
| Motor Driver  | Controls vibration motor based on PID output                                |
| Protocol Eval | Tools for running and analyzing patient evaluation protocols                |

---

## Project Structure

```text
Parkimotion/
├── CMakeLists.txt
├── README.md
├── interfazdash/
│   ├── app.py
│   ├── results.py
│   ├── utils.py
│   ├── verificar_puerto.py
│   ├── assets/
│   │   └── custom.css
│   ├── data/
│   │   └── [CSV data files]
│   └── graficas/
├── main/
│   ├── CMakeLists.txt
│   ├── imu_reader.c/h
│   ├── main.c
│   ├── motor_test.c/h
│   └── uart_comm.c/h
```

---

## Installation

### 1. ESP32 Firmware (ESP-IDF)

- Install [ESP-IDF](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/get-started/)
- Clone this repository:
  ```sh
  git clone https://github.com/ToRo18299/Parkimotion.git
  cd Parkimotion
  ```
- Set up ESP-IDF environment:
  ```sh
  . $IDF_PATH/export.sh
  ```
- Build and flash firmware:
  ```sh
  idf.py build
  idf.py -p <PORT> flash
  ```

### 2. Python Dash Interface

- Install Python 3.8+
- Install required packages:
  ```sh
  pip install -r interfazdash/requirements.txt
  ```
- Run the Dash app:
  ```sh
  python interfazdash/app.py
  ```

---

## Main Features

- Real-time IMU data acquisition (100 Hz)
- Closed-loop PID vibration control
- Butterworth band-pass filtering (3–7 Hz)
- FFT analysis with Hann window
- Dominant frequency, amplitude (g), and displacement (cm) estimation
- UART communication between ESP32 and PC
- Python Dash interface for monitoring, protocol management, and statistical analysis (t-Student)
- Protocol evaluation and results storage

---

## Images

- System Overview: ![System Overview](/assets/overview.png)
- Dash Interface: ![Dash Interface](/assets/dash_interface.png)
- FFT Example: ![FFT Example](/assets/fft_example.png)

---

## Results & Validation

ParkiMotion has been validated with patient protocols, demonstrating accurate tremor emulation and reliable data acquisition. The system enables quantitative analysis of vibration parameters and supports statistical evaluation of rehabilitation outcomes.

---

## Academic Attribution

**Project:** ParkiMotion  
**Degree:** Electronics Engineering  
**Institution:** Universidad del Valle  
**Author:** Diego Ramos  
**Contact:** diego.ramos@correounivalle.edu.co

---

## Contributing & Support

If you find this project useful, please ⭐ star the repository!  
For questions or collaboration, open an issue or contact the author.

---
