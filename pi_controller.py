import cv2
import time
import json
import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO
import bme680
import smbus2
# import tflite_runtime.interpreter as tflite # Placeholder for TensorFlow Lite

# --- Configuration ---
MQTT_BROKER = "192.168.1.125"  # Replace with your MQTT broker address
MQTT_PORT = 1883
MQTT_TOPIC = "library/sensor_data"
CAMERA_INDEX = 0  # Reverted to 0 as confirmed working previously

# MobileNet-SSD Model Configuration
PROTOTXT_PATH = "/home/pi/MobileNetSSD_deploy.prototxt"
CAFFEMODEL_PATH = "/home/pi/MobileNetSSD_deploy.caffemodel"
PERSON_CLASS_ID = 15   # "person" class in MobileNet-SSD
CONF_THRESHOLD = 0.5   # confidence threshold

# GPIO Pin Definitions (Placeholders for when you add them)
# LED_PIN = 17
# SERVO_PIN = 18
# MICROPHONE_PIN = 27 # Example, actual sensor might use ADC

# BME680 Sensor Setup
try:
    bus = smbus2.SMBus(1)
    sensor = bme680.BME680(i2c_addr=bme680.I2C_ADDR_PRIMARY, i2c_device=bus)
    # These oversampling settings can be tweaked to trade accuracy for power consumption
    sensor.set_humidity_oversample(bme680.OS_2X)
    sensor.set_pressure_oversample(bme680.OS_4X)
    sensor.set_temperature_oversample(bme680.OS_8X)
    sensor.set_filter(bme680.FILTER_SIZE_3)
    sensor.set_gas_status(bme680.ENABLE_GAS_MEAS)
    sensor.set_gas_heater_temperature(320)
    sensor.set_gas_heater_duration(150)
    sensor.select_gas_heater_profile(0)
except Exception as e:
    print(f"Error initializing BME680 sensor: {e}")
    sensor = None

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
# def initialize_gpio():
#     GPIO.setmode(GPIO.BCM)
#     GPIO.setup(LED_PIN, GPIO.OUT)
#     GPIO.setup(SERVO_PIN, GPIO.OUT)
#     # Initialize other sensor pins as needed
#     print("GPIO initialized.")

def read_bme680():
    if sensor and sensor.get_sensor_data():
        return {
            "temperature": sensor.data.temperature,
            "humidity": sensor.data.humidity,
            "pressure": sensor.data.pressure,
            "air_quality_resistance": sensor.data.gas_resistance
        }
    return {}

# def read_noise_level():
#     # Placeholder: Replace with actual microphone reading logic (e.g., ADC reading)
#     return {"noise_db": 55}

# def control_led(state):
#     GPIO.output(LED_PIN, GPIO.HIGH if state else GPIO.LOW)
#     print(f"LED set to {'ON' if state else 'OFF'}")

# def control_servo(angle):
#     print(f"Servo set to angle {angle}")

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
            # Optional: Draw bounding boxes for visual debugging
            # box = detections[0, 0, i, 3:7] * [w, h, w, h]
            # x1, y1, x2, y2 = box.astype("int")
            # cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

    # Optional: Save frame with detections for debugging
    # cv2.putText(frame, f"Persons: {count}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    # cv2.imwrite("/dev/shm/people_latest.jpg", frame)

    return {"people_count": count}

# --- Main Loop ---
def main():
    # initialize_gpio()

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

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Error: Failed to grab frame.")
                time.sleep(0.1) # Wait a bit before retrying
                continue

            # 1. Person Detection
            detection_results = detect_people(frame)
            people_count = detection_results.get("people_count", 0)

            # 2. Sensor Readings
            bme_data = read_bme680()
            light_data = get_light_level(frame)
            # noise_data = read_noise_level()

            # 3. Local Actuation Logic (Example: LED based on people count)
            # if people_count > 0:
            #     control_led(True) # Turn LED on if people are detected
            # else:
            #     control_led(False) # Turn LED off

            # 4. Prepare and Publish Data
            sensor_data = {
                "timestamp": time.time(),
                "location": "library_zone_A", # Example location
                "sensor_id": "pi_controller_01",
                "metrics": {
                    "people_count": people_count,
                    "temperature": bme_data.get("temperature"),
                    "humidity": bme_data.get("humidity"),
                    "pressure": bme_data.get("pressure"),
                    "air_quality_resistance": bme_data.get("air_quality_resistance"),
                    "light_level": light_data.get("light_level"),
                    # "noise_db": noise_data.get("noise_db")
                }
            }
            # Filter out None values before sending - REMOVED TO ENSURE CONSISTENT JSON STRUCTURE
            # sensor_data["metrics"] = {k: v for k, v in sensor_data["metrics"].items() if v is not None}
            
            client.publish(MQTT_TOPIC, json.dumps(sensor_data))
            print(f"Published: {json.dumps(sensor_data)}")

            time.sleep(5) # Publish every 5 seconds

    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        cap.release()
        client.loop_stop()
        client.disconnect()
        # GPIO.cleanup() # Clean up GPIO settings

if __name__ == "__main__":
    main()
