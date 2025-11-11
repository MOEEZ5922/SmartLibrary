# Smart Library IoT System: Development Plan (Raspberry Pi Edition)

This document provides a phased development plan for the Smart Library project, using a Raspberry Pi as the central controller.

---

### **Phase 1: Raspberry Pi Setup & Environment**

**Goal:** To prepare the Raspberry Pi by installing all necessary software and libraries.

*   **Step 1.1: Initial Pi Setup:**
    *   Install the latest **Raspberry Pi OS** on your SD card.
    *   Run `sudo apt update` and `sudo apt full-upgrade` to ensure all packages are current.
    *   Use the `raspi-config` tool to **enable the Camera (Legacy)** interface and other interfaces like I2C/SPI if your sensors require them.

*   **Step 1.2: Install Python Libraries:**
    *   **OpenCV:** For capturing and processing video from the camera.
        ```bash
        pip install opencv-python
        ```
    *   **TensorFlow Lite:** The runtime engine for our person detection model.
        ```bash
        # Follow the official TensorFlow guide for installing the TFLite runtime on Raspberry Pi
        # It usually involves downloading a specific .whl file for your Pi's architecture
        pip install tflite-runtime
        ```
    *   **MQTT Client:** For sending data to the cloud/dashboard.
        ```bash
        pip install paho-mqtt
        ```
    *   **Sensor/GPIO Libraries:**
        ```bash
        pip install RPi.GPIO adafruit-circuitpython-ens160
        # Add other libraries specific to your air quality sensor and microphone
        ```

---

### **Phase 2: Hardware Integration & Validation**

**Goal:** To connect and test each hardware component with a simple, standalone Python script.

*   **Step 2.1: Connect Hardware:**
    *   Connect the Camera to the CSI port.
    *   Connect the Air Quality Sensor, Microphone, LED, and Servo to the appropriate GPIO pins on the Raspberry Pi (power, ground, and data pins).

*   **Step 2.2: Validate Each Component:**
    *   **Camera:** Write a simple Python script using OpenCV to capture a few frames from the camera and save them as image files to confirm it works.
    *   **Sensors:** Write individual scripts to read data from the Air Quality sensor and the Microphone and print the values to the console.
    *   **Actuators:** Write individual scripts to light up the LED and to move the Servo to specific positions.

---

### **Phase 3: Real-Time Person Detection Script**

**Goal:** To create the core application logic for detecting and counting people in real-time.

*   **Step 3.1: Download a Pre-trained Model:**
    *   Download a lightweight, pre-trained person detection model in `.tflite` format (e.g., "MobileNet SSD" or "EfficientDet-Lite"). You will also need its corresponding label file.

*   **Step 3.2: Write the Detection Script:**
    *   Create a Python script that uses OpenCV to open a continuous video stream from the camera.
    *   In a `while True:` loop, read one frame at a time.
    *   For each frame:
        1.  Pre-process it (resize, normalize) to match the model's input requirements.
        2.  Feed the frame into the loaded TensorFlow Lite model.
        3.  Run inference to get the detection results (bounding boxes, classes, scores).
        4.  Loop through the results and count how many detected objects are "person" with a confidence score above a set threshold (e.g., 50%).
    *   Print the final person count for each frame to the console.

---

### **Phase 4: Full Application Logic**

**Goal:** To combine all individual scripts into a single, main application that reads all sensors and triggers actions.

*   **Step 4.1: Structure the Main Script:**
    *   Create a main Python file.
    *   Initialize all hardware (camera, sensors, actuators).
    *   Integrate the person detection loop from Phase 3.

*   **Step 4.2: Implement Rules and Actions:**
    *   Inside the main loop, after getting the `person_count` and other sensor readings:
        *   **Light Control:** If `person_count` is 0 for a certain duration, call the function to move the servo to the "off" position. Otherwise, move it to "on".
        *   **Noise Alert:** If the microphone reading exceeds a threshold, call the function to turn the LED red. Otherwise, keep it green.

---

### **Phase 5: Cloud Integration (InfluxDB & Grafana)**

**Goal:** To send all collected data to a dashboard for visualization.

*   **Step 5.1: Set up InfluxDB & Grafana:**
    *   Follow the steps from the previous version of this plan to set up InfluxDB Cloud and Grafana Cloud.

*   **Step 5.2: Implement MQTT Publishing:**
    *   In your main Python script, add the `paho-mqtt` client logic.
    *   At the end of each loop, create a JSON payload containing all the latest data (`person_count`, `temperature`, `humidity`, `noise_level`, etc.).
    *   Publish this JSON payload to an MQTT topic.

*   **Step 5.3: Bridge MQTT to InfluxDB:**
    *   The easiest way to get data from your MQTT broker into InfluxDB is to use **Telegraf** (another tool from InfluxData).
    *   Install Telegraf on your Raspberry Pi or another server.
    *   Configure Telegraf with an `[[inputs.mqtt_consumer]]` section to subscribe to your topic and a `[[outputs.influxdb_v2]]` section to write the data to your InfluxDB Cloud bucket.
    *   Start the Telegraf service. Your Grafana dashboard should now start receiving live data.