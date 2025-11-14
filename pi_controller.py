import cv2
import time
import json
import paho.mqtt.client as mqtt
import bme680

# --- Constants & Configuration ---
MQTT_BROKER = "192.168.1.125"  # Replace with your MQTT broker address
MQTT_PORT = 1883
MQTT_TOPIC = "library/sensor_data"
CAMERA_INDEX = 0
BME680_BURN_IN_TIME_SECONDS = 60

# MobileNet-SSD Model
PROTOTXT_PATH = "/home/pi/MobileNetSSD_deploy.prototxt"
CAFFEMODEL_PATH = "/home/pi/MobileNetSSD_deploy.caffemodel"
PERSON_CLASS_ID = 15   # "person" class in MobileNet-SSD
CONF_THRESHOLD = 0.5   # confidence threshold

# --- Light Level Normalization Parameters ---
LIGHT_LEVEL_NORMALIZATION = {
    "min_observed": 0.0,
    "max_observed": 120.0 # Tuned so a "normal" reading of 100 appears around 83%
}

# --- Sensor & Model Initialization ---
try:
    sensor = bme680.BME680(bme680.I2C_ADDR_PRIMARY)
except (RuntimeError, IOError):
    sensor = bme680.BME680(bme680.I2C_ADDR_SECONDARY)

sensor.set_humidity_oversample(bme680.OS_2X)
sensor.set_pressure_oversample(bme680.OS_4X)
sensor.set_temperature_oversample(bme680.OS_8X)
sensor.set_filter(bme680.FILTER_SIZE_3)
sensor.set_gas_status(bme680.ENABLE_GAS_MEAS)
sensor.set_gas_heater_temperature(320)
sensor.set_gas_heater_duration(150)
sensor.select_gas_heater_profile(0)

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

# --- Data Processing Functions ---
def calculate_iaq(humidity, gas_resistance, hum_baseline, gas_baseline):
    """Calculates Indoor Air Quality (IAQ) score based on BME680 readings."""
    hum_weighting = 0.25 # 25% of IAQ score is based on humidity
    
    hum_offset = humidity - hum_baseline
    gas_offset = gas_baseline - gas_resistance

    if hum_offset > 0:
        hum_score = (100 - hum_baseline - hum_offset) / (100 - hum_baseline) * (hum_weighting * 100)
    else:
        hum_score = (hum_baseline + hum_offset) / hum_baseline * (hum_weighting * 100)
    
    if gas_offset > 0:
        gas_score = (gas_resistance / gas_baseline) * (100 - (hum_weighting * 100))
    else:
        gas_score = 100 - (hum_weighting * 100)
    
    return hum_score + gas_score

def normalize_light_level(raw_light_level):
    """Converts raw 0-255 brightness to a normalized 0-100% scale."""
    norm_params = LIGHT_LEVEL_NORMALIZATION
    min_obs = norm_params["min_observed"]
    max_obs = norm_params["max_observed"]
    
    normalized = (raw_light_level - min_obs) / (max_obs - min_obs)
    
    if normalized >= 1.0:
        return 100.0
    elif normalized <= 0.0:
        return 0.0
    else:
        return round(normalized * 100.0, 2)

# --- Hardware Interaction Functions ---
def read_noise_level():
    return 45.0

def get_raw_light_level(frame):
    """Calculates the average brightness (0-255) from a camera frame."""
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return gray_frame.mean()

def detect_people(frame):
    """Detects people in a frame using the MobileNet-SSD model."""
    if net is None:
        return 0

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
    return count

# --- Main Application ---
def main():
    """Main function to run the IoT controller."""
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()

    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("Error: Could not open camera.")
        return
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    # --- BME680 Burn-in ---
    print(f"BME680 burn-in started... This will take approx. {BME680_BURN_IN_TIME_SECONDS} seconds.")
    burn_in_data = []
    start_time = time.time()
    while time.time() - start_time < BME680_BURN_IN_TIME_SECONDS:
        if sensor.get_sensor_data():
            burn_in_data.append(sensor.data.gas_resistance)
        time.sleep(1)
    
    gas_baseline = sum(burn_in_data[-50:]) / 50.0
    hum_baseline = 40.0 # Approx. 40% RH
    print(f"BME680 burn-in complete. Gas baseline: {gas_baseline:.2f} Ohms")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Error: Failed to grab frame.")
                time.sleep(0.1)
                continue

            # --- Collect Metrics ---
            people_count = detect_people(frame)
            raw_light = get_raw_light_level(frame)
            light_level_percent = normalize_light_level(raw_light)
            noise_db = read_noise_level()

            if sensor.get_sensor_data():
                temperature = sensor.data.temperature
                iaq = calculate_iaq(sensor.data.humidity, sensor.data.gas_resistance, hum_baseline, gas_baseline)

                # --- Prepare and Publish Data ---
                sensor_data = {
                    "timestamp": time.time(),
                    "location": "library_zone_A",
                    "sensor_id": "pi_controller_01",
                    "metrics": {
                        "people_count": people_count,
                        "temperature": temperature,
                        "iaq": iaq,
                        "light_level": light_level_percent,
                        "noise_db": noise_db
                    }
                }
                
                client.publish(MQTT_TOPIC, json.dumps(sensor_data))
                print(f"Published: {json.dumps(sensor_data)}")
            else:
                print("Warning: Failed to get BME680 sensor data. Skipping publish.")

            time.sleep(5)

    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        cap.release()
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()
