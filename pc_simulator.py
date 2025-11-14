import time
import json
import random
import paho.mqtt.client as mqtt

# --- Configuration ---
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "library/sensor_data"
SIMULATION_INTERVAL_SECONDS = 5

# --- Simulation & Normalization Parameters ---
SIMULATION_LIMITS = {
    "people_count": {"min": 0, "max": 50},
    "temperature": {"min": 18.0, "max": 25.0},
    "iaq": {"min": 40, "max": 100},
    "light_level_raw": {"min": 10, "max": 130}, # Realistic range on a 0-255 scale
    "noise_db": {"min": 35.0, "max": 80.0}
}

LIGHT_LEVEL_NORMALIZATION = {
    "min_observed": 0.0,
    "max_observed": 120.0 # Tuned so a "normal" reading of 100 appears around 83%
}

# --- MQTT Callbacks ---
def on_connect(client, userdata, flags, reason_code, properties):
    """Callback for when the client connects to the broker."""
    if reason_code == 0:
        print("Simulator connected to MQTT Broker!")
    else:
        print(f"Failed to connect, return code {reason_code}\n")

# --- Data Generation ---
def generate_simulated_metrics():
    """Generates a dictionary of simulated sensor metrics."""
    
    # --- Generate basic random values ---
    people_count = random.randint(SIMULATION_LIMITS["people_count"]["min"], SIMULATION_LIMITS["people_count"]["max"])
    temperature = round(random.uniform(SIMULATION_LIMITS["temperature"]["min"], SIMULATION_LIMITS["temperature"]["max"]), 2)
    iaq = round(random.uniform(SIMULATION_LIMITS["iaq"]["min"], SIMULATION_LIMITS["iaq"]["max"]), 2)
    noise_db = round(random.uniform(SIMULATION_LIMITS["noise_db"]["min"], SIMULATION_LIMITS["noise_db"]["max"]), 2)

    # --- Generate and normalize light level ---
    raw_light_level = random.uniform(SIMULATION_LIMITS["light_level_raw"]["min"], SIMULATION_LIMITS["light_level_raw"]["max"])
    
    min_obs = LIGHT_LEVEL_NORMALIZATION["min_observed"]
    max_obs = LIGHT_LEVEL_NORMALIZATION["max_observed"]
    normalized = (raw_light_level - min_obs) / (max_obs - min_obs)
    
    if normalized >= 1.0:
        light_level_percent = 100.0
    elif normalized <= 0.0:
        light_level_percent = 0.0
    else:
        light_level_percent = round(normalized * 100.0, 2)

    # --- Return final metrics dictionary ---
    return {
        "people_count": people_count,
        "temperature": temperature,
        "iaq": iaq,
        "light_level": light_level_percent,
        "noise_db": noise_db
    }

# --- Main Application ---
def main():
    """Connects to MQTT and publishes simulated data in a loop."""
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect

    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
    except ConnectionRefusedError:
        print("Connection refused. Is the MQTT broker (Docker container) running?")
        return
    except Exception as e:
        print(f"An error occurred while connecting: {e}")
        return

    client.loop_start()

    print("Starting data simulation... Press Ctrl+C to stop.")
    print(f"Using simulation limits: {json.dumps(SIMULATION_LIMITS, indent=2)}")

    try:
        while True:
            # 1. Generate the metrics
            metrics = generate_simulated_metrics()

            # 2. Construct the full data payload
            sensor_data = {
                "timestamp": time.time(),
                "location": "library_zone_A_simulated",
                "sensor_id": "pc_simulator_01",
                "metrics": metrics
            }

            # 3. Publish to MQTT
            payload = json.dumps(sensor_data)
            result = client.publish(MQTT_TOPIC, payload)

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"Published: {payload}")
            else:
                print(f"Failed to publish message. Error code: {result.rc}")

            time.sleep(SIMULATION_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print("\nSimulation stopped by user.")
    finally:
        client.loop_stop()
        client.disconnect()
        print("Disconnected from MQTT Broker.")

if __name__ == "__main__":
    main()
