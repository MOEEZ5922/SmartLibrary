# Project Plan: Smart Library Dashboard

This document outlines the project plan for an IoT-based system to monitor and display key environmental and usage metrics within a library. This version has been updated to reflect a minimalist hardware approach.

### Project Goal

*   **Primary Goal:** To develop and deploy an IoT-based system that monitors and displays real-time environmental and usage metrics within a library, with the aim of improving user comfort, optimizing space utilization, and increasing energy efficiency.
*   **Justification & Needs:**
    *   **Operational Need:** To provide data-driven insights for optimizing HVAC and lighting systems, leading to significant energy savings and reduced operational costs.
    *   **User Need:** To offer students and patrons real-time information on study space availability, noise levels, and air quality, enabling them to find a comfortable and productive environment.
    *   **Business Need:** To gather analytics on library usage patterns, helping administrators make informed decisions regarding staffing, resource allocation, and future planning.

### UN Sustainable Development Goals (SDGs)

*   **SDG 11: Sustainable Cities and Communities:** The project directly contributes to Target 11.6 (reduce the adverse per capita environmental impact of cities) by providing the tools to lower the library's energy consumption, making a public building more sustainable.
*   **SDG 4: Quality Education:** The project supports Target 4.a (build and upgrade education facilities) by ensuring the library environment is comfortable, quiet, and conducive to learning, thereby improving the quality of the study experience for all users.

### Users, Use Cases, & User Stories

*   **Users:**
    *   **Library Administrator:** Responsible for overall library management, budget, and strategic planning.
    *   **Facilities Manager:** Responsible for building maintenance, operations, and energy management.
    *   **Student/Patron:** The primary end-user of the library's facilities.

*   **Use Cases:**
    *   **Facilities Manager:** Monitors the dashboard to detect poor air quality or anomalies in energy use, enabling preventative maintenance and efficient climate control.
    *   **Student/Patron:** Accesses the web dashboard or looks at a local LED indicator to quickly find a quiet, available, and comfortable study spot.

*   **User Stories:**
    1.  "As a **Facilities Manager**, I want to **receive an alert when the air quality index drops below a certain threshold** so that **I can adjust the building's ventilation system**."
    2.  "As a **Student**, I want to **see a real-time indicator light (LED) turn from green to red as a zone gets noisy or full** so that **I can decide at a glance if I want to enter**."
    3.  "As a **Library Administrator**, I want to **generate a weekly report on peak usage hours based on camera-based people counting** so that **I can schedule staff more effectively**."

### Project Management

*   **Methodology:** **Agile (Scrum)**.
*   **Key Roles:**
    *   **Project Lead**
    *   **Hardware Engineer**
    *   **Backend Developer**
    *   **Frontend/DataViz Developer**

### Technology Stack

*   **Single-Board Computer:** A **Raspberry Pi** (e.g., Model 3B+ or 4) will serve as the central controller for the system.

*   **Hardware Components:**
    *   **Camera:** An Arducam OV5647 camera connected to the Pi's CSI port.
    *   **Sensors:**
        *   **Air Quality Sensor:** Connected to the Pi's GPIO pins (via I2C or SPI).
        *   **Microphone:** A microphone module connected to the Pi's GPIO pins (likely via an ADC if it's an analog mic).
    *   **Actuators:**
        *   **Servo:** Connected to a PWM-capable GPIO pin.
        *   **LED:** Connected to a standard GPIO pin.

*   **Connectivity:**
    *   **Protocol:** **MQTT** for lightweight, publish/subscribe messaging.
    *   **Network:** **Wi-Fi** or **Ethernet** on the Raspberry Pi.

*   **Software (Device):**
    *   **Operating System:** **Raspberry Pi OS**.
    *   **Language:** **Python 3**.
    *   **Key Libraries:**
        *   **OpenCV:** For capturing and processing camera frames.
        *   **TensorFlow Lite Runtime:** For running the person detection model.
        *   **RPi.GPIO** or **gpiozero:** For controlling the Servo and LED.
        *   **paho-mqtt:** For publishing data.
        *   **CircuitPython Libraries:** For interfacing with I2C/SPI sensors like the air quality module.

*   **Software (Cloud/Dashboard):**
    *   **Data Sink:** **InfluxDB** (Cloud or self-hosted).
    *   **Data Bridge:** **Telegraf** to subscribe to MQTT and write to InfluxDB.
    *   **Visualization:** **Grafana** (Cloud or self-hosted).

### Software/Hardware Architecture

1.  **Central Controller (Raspberry Pi):** A single Python application runs continuously on the Raspberry Pi. This script is responsible for all operations.
2.  **Data Collection:**
    *   The script uses the **OpenCV** library to capture frames from the CSI camera. It runs a **TensorFlow Lite** model to count the number of people in each frame.
    *   It uses GPIO-specific libraries (e.g., CircuitPython, RPi.GPIO) to read data from the connected **Air Quality Sensor** and **Microphone**.
3.  **Local Actuation:** Based on the collected data, the script directly controls the **LED** and **Servo** via the Pi's GPIO pins.
4.  **Data Publishing:** The script formats all sensor readings (`person_count`, `temperature`, `noise_level`, etc.) into a JSON payload and publishes it to an **MQTT** topic.
5.  **Dashboarding Pipeline:** A **Telegraf** agent (running on the Pi or elsewhere) subscribes to the MQTT topic, collects the data, and writes it to an **InfluxDB** database. A **Grafana** dashboard is connected to InfluxDB to provide visualization.

### Database Architecture

*   **Table/Measurement Name:** `SensorReadings`
*   **Fields:**
    *   `timestamp` (Time, Indexed)
    *   `location` (Tag, Indexed)
    *   `sensor_id` (Tag, Indexed)
    *   `metric_type` (Tag, Indexed): "temperature", "humidity", "air_quality_index", "noise_db", "estimated_light_lux", "people_count".
    *   `metric_value` (Field, Float/Int)
    *   `unit` (Tag): "celsius", "percent", "aqi", "db", "lux", "persons".

### Automated Actions & Interventions

*   **Energy Management (Lighting Control):**
    *   **Trigger:** `people_count` in a zone is 0 for a sustained period (e.g., 15 minutes).
    *   **Action:** The cloud backend sends an MQTT command to the ESP32 to activate the **Servo**, which mechanically flips the light switch to the "off" position. The process is reversed when presence is detected again.

*   **Noise Level Feedback (Behavioral Nudging):**
    *   **Trigger:** `noise_db` in a "Quiet Zone" exceeds a predefined threshold.
    *   **Action:** The ESP32 immediately changes its local **LED** from Green to Red. (Note: The speaker is now optional).

*   **Air Quality Alerts (Facility Management):**
    *   **Trigger:** The `air_quality_index` falls below a safe threshold.
    *   **Action:** An alert is automatically sent from the cloud platform to the Facilities Manager.

### Environmental Impact of the Project

*   **Positive Impacts:**
    *   **Energy Efficiency:** Data-driven control of lighting and HVAC based on occupancy and environmental data can significantly reduce the building's carbon footprint.
*   **Negative Impacts:**
    *   **E-Waste:** The sensors and microcontrollers will become e-waste at their end-of-life and must be managed.
    *   **Upstream Energy Consumption:** The manufacturing and 24/7 operation of the hardware and cloud servers consume energy.

### Ecodesign Evaluation (based on RGESN)

*   **Main Compliant Criteria (Potential):**
    1.  **Criterion 1.1: Is the service's objective aligned with a societal need?** Yes, it addresses energy conservation and the improvement of public educational facilities.
    2.  **Criterion 7.2: Does the service have a positive environmental or social impact?** Yes, its core purpose is to reduce energy consumption.
*   **Main Non-Compliant Criteria (Risks):**
    1.  **Criterion 5.1: Is the hardware end-of-life managed?** This is a significant risk requiring a proactive recycling/disposal plan.
    2.  **Criterion 6.2: Is the amount of data retained proportionate to the real need?** Storing high-resolution data indefinitely would be wasteful.

### Opportunities for Improvement (Sustainability)

*   **Short/Mid-Term:**
    1.  **Low-Power Strategy:** Use the ESP32's deep-sleep modes to minimize power consumption, waking only to take and send readings.
    2.  **Data Aggregation & Retention Policy:** Retain raw data for a short period (e.g., 7 days), then automatically aggregate it into hourly averages and discard the raw points.
    3.  **Use the LED for Efficiency:** The LED provides a low-power way to communicate information locally, reducing the need for users to load the full web dashboard.
*   **Long-Term:**
    1.  **Hardware Lifecycle Plan:** Develop a partnership with an e-waste recycler for responsible hardware disposal.
    2.  **Open Data for Research:** Anonymize and publish the dataset to allow researchers to study building efficiency, multiplying the project's positive impact.
