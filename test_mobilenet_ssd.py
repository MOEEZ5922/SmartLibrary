import cv2
import time
import numpy as np

# --- Constants & Configuration ---
# IMPORTANT: Adjust these paths if your model files are in a different location.
# These files should be downloaded from the original MobileNet-SSD project.
PROTOTXT_PATH = "MobileNetSSD_deploy.prototxt"
CAFFEMODEL_PATH = "MobileNetSSD_deploy.caffemodel"
PERSON_CLASS_ID = 15   # "person" class in MobileNet-SSD
CONF_THRESHOLD = 0.5   # confidence threshold

# --- Model Initialization ---
try:
    net = cv2.dnn.readNetFromCaffe(PROTOTXT_PATH, CAFFEMODEL_PATH)
    print("MobileNet-SSD model loaded successfully.")
except Exception as e:
    print(f"Error loading MobileNet-SSD model: {e}")
    print(f"Please ensure '{PROTOTXT_PATH}' and '{CAFFEMODEL_PATH}' are in the same directory as this script.")
    net = None

def detect_people_mobilenet_ssd(frame):
    """Detects people in a frame using the MobileNet-SSD model."""
    if net is None:
        return 0, []

    h, w = frame.shape[:2]
    # Resize frame to 300x300 for MobileNet-SSD
    blob = cv2.dnn.blobFromImage(frame, 0.007843, (300, 300), 127.5)
    net.setInput(blob)
    detections = net.forward()

    count = 0
    boxes = []
    for i in range(detections.shape[2]):
        confidence = float(detections[0, 0, i, 2])
        class_id = int(detections[0, 0, i, 1])
        if confidence >= CONF_THRESHOLD and class_id == PERSON_CLASS_ID:
            count += 1
            # Get bounding box coordinates
            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            (startX, startY, endX, endY) = box.astype("int")
            boxes.append((startX, startY, endX, endY, confidence))
    return count, boxes

def main():
    """Main function to run MobileNet-SSD detection on laptop camera."""
    cap = cv2.VideoCapture(0)  # 0 for default laptop camera
    if not cap.isOpened():
        print("Error: Could not open camera. Make sure no other application is using it.")
        return

    print("Press 'q' to quit.")
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Error: Failed to grab frame.")
                time.sleep(0.1)
                continue

            start_time = time.time()
            people_count, detection_boxes = detect_people_mobilenet_ssd(frame)
            end_time = time.time()
            inference_time = end_time - start_time

            # Draw bounding boxes and text on the frame
            for (startX, startY, endX, endY, confidence) in detection_boxes:
                # Draw the bounding box
                cv2.rectangle(frame, (startX, startY), (endX, endY), (0, 255, 0), 2)
                # Draw confidence
                text = f"Person: {confidence:.2f}"
                y = startY - 15 if startY - 15 > 15 else startY + 15
                cv2.putText(frame, text, (startX, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            # Display people count and inference time
            info_text = f"People: {people_count} | Inference: {inference_time:.2f}s"
            cv2.putText(frame, info_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)


            cv2.imshow("MobileNet-SSD Detection", frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
