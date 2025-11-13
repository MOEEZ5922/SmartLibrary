import cv2
import time
import json
import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO
import bme680


MQTT_BROKER = "192.168.1.125"  # Replace with your MQTT broker address
MQTT_PORT = 1883
MQTT_TOPIC = "library/sensor_data"
CAMERA_INDEX = 0

# MobileNet-SSD Model
PROTOTXT_PATH = "/home/pi/MobileNetSSD_deploy.prototxt"
CAFFEMODEL_PATH = "/home/pi/MobileNetSSD_deploy.caffemodel"
PERSON_CLASS_ID = 15   # "person" class in MobileNet-SSD
CONF_THRESHOLD = 0.5   # confidence threshold

try:
    sensor = bme680.BME680(bme680.I2C_ADDR_PRIMARY)
except (RuntimeError, IOError):
    sensor = bme680.BME680(bme680.I2C_ADDR_SECONDARY)

# These oversampling settings can be tweaked to trade accuracy for power consumption
sensor.set_humidity_oversample(bme680.OS_2X)
sensor.set_pressure_oversample(bme680.OS_4X)
sensor.set_temperature_oversample(bme680.OS_8X)
sensor.set_filter(bme680.FILTER_SIZE_3)
sensor.set_gas_status(bme680.ENABLE_GAS_MEAS)
sensor.set_gas_heater_temperature(320)
sensor.set_gas_heater_duration(150)
sensor.select_gas_heater_profile(0)

# Load MobileNet-SSD model
try:
    net = cv2.dnn.readNetFromCaffe(PROTOTXT_PATH, CAFFEMODEL_PATH)
except Exception as e:
    print(f"Error loading MobileNet-SSD model: {e}")
    net = None

# --- MQTT Callbacks ---
def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("Connected to MQTT Broker!")
    else:
        print(f"Failed to connect, return code {reason_code}\n")

def on_message(client, userdata, msg):
    print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")
    # Add logic here to handle commands from the cloud (e.g., control servo)

# --- Hardware Interaction ---
def read_noise_level():
    # Implement actual noise level reading from a microphone sensor
    return {"noise_db": 45.0}

def get_light_level(frame):
    # Convert frame to grayscale
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    # Calculate the average brightness (mean pixel value)
    light_level = gray_frame.mean()
    return {"light_level": light_level}

# --- Person Detection ---
def detect_people(frame):
    if net is None:
        return {"people_count": 0}

    h, w = frame.shape[:2]
    blob = cv2.dnn.blobFromImage(frame, 0.007843, (300, 300), 127.5)
    net.setInput(blob)
    detections = net.forward()

    count = 0
    for i in range(detections.shape[2]):
        confidence = float(detections[0, 0, i, 2])
        class_id = int(detections[0, 0, i, 1])
        if confidence >= CONF_THRESHOLD and class_id == PERSON_CLASS_ID:
            count += 1
    return {"people_count": count}

# --- Main Loop ---
def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()

    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("Error: Could not open camera.")
        return
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    # --- BME680 Burn-in ---
    # The Pimoroni library calculates IAQ based on a baseline gas resistance.
    # This requires a burn-in period of approx. 5 minutes to stabilize.
    print("BME680 burn-in started... This will take approx. 5 minutes.")
    burn_in_data = []
    start_time = time.time()
    while time.time() - start_time < 60:
        if sensor.get_sensor_data():
            gas = sensor.data.gas_resistance
            burn_in_data.append(gas)
        time.sleep(1)
    gas_baseline = sum(burn_in_data[-50:]) / 50.0
    hum_baseline = 40.0 # Approx. 40% RH
    hum_weighting = 0.25
    print(f"BME680 burn-in complete. Gas baseline: {gas_baseline:.2f} Ohms")


    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Error: Failed to grab frame.")
                time.sleep(0.1)
                continue

            # 1. Person Detection
            detection_results = detect_people(frame)
            people_count = detection_results.get("people_count", 0)

            # 2. Sensor Readings & Data Publishing
            if sensor.get_sensor_data():
                temperature = sensor.data.temperature
                hum = sensor.data.humidity
                gas = sensor.data.gas_resistance
                
                hum_offset = hum - hum_baseline
                gas_offset = gas_baseline - gas

                if hum_offset > 0:
                    hum_score = (100 - hum_baseline - hum_offset) / (100 - hum_baseline) * (hum_weighting * 100)
                else:
                    hum_score = (hum_baseline + hum_offset) / hum_baseline * (hum_weighting * 100)
                
                if gas_offset > 0:
                    gas_score = (gas / gas_baseline) * (100 - (hum_weighting * 100))
                else:
                    gas_score = 100 - (hum_weighting * 100)
                
                iaq = hum_score + gas_score

                light_data = get_light_level(frame)
                noise_data = read_noise_level()

                # Prepare and Publish Data ONLY if sensor reading was successful
                sensor_data = {
                    "timestamp": time.time(),
                    "location": "library_zone_A",
                    "sensor_id": "pi_controller_01",
                    "metrics": {
                        "people_count": people_count,
                        "temperature": temperature,
                        "iaq": iaq,
                        "light_level": light_data.get("light_level"),
                        "noise_db": noise_data.get("noise_db")
                    }
                }
                
                client.publish(MQTT_TOPIC, json.dumps(sensor_data))
                print(f"Published: {json.dumps(sensor_data)}")
            else:
                print("Warning: Failed to get sensor data. Skipping publish.")

            time.sleep(5)

    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        cap.release()
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()
