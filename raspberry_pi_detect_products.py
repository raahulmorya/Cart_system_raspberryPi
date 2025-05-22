import cv2
import numpy as np
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import time
from ultralytics import YOLO
import RPi.GPIO as GPIO
import threading

# Initialize GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# LED pins
GREEN_LED = 17  # New item added
BLUE_LED = 27   # Quantity updated
RED_LED = 22    # No detection

# Setup GPIO pins
GPIO.setup(GREEN_LED, GPIO.OUT)
GPIO.setup(BLUE_LED, GPIO.OUT)
GPIO.setup(RED_LED, GPIO.OUT)

# Initialize all LEDs to off
GPIO.output(GREEN_LED, GPIO.LOW)
GPIO.output(BLUE_LED, GPIO.LOW)
GPIO.output(RED_LED, GPIO.LOW)

# Initialize Firebase
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Initialize YOLO model with optimizations
model = YOLO('honey.pt')
model.overrides['conf'] = 0.5  # Confidence threshold
model.overrides['iou'] = 0.45  # IoU threshold
model.overrides['agnostic_nms'] = True  # Class-agnostic NMS
model.overrides['max_det'] = 10  # Maximum detections per image

# Product names list (unchanged)
BASE_NAMES = [
    "amul_darkchocolate", "balaji_aloo_sev", "balaji_ratlami_sev", 
    # ... (rest of your product list)
]

# Pre-sort the base names by length (longest first)
BASE_NAMES_SORTED = sorted(BASE_NAMES, key=len, reverse=True)

CLASS_NAME_MAP = {}
for class_id, name in model.names.items():
    matched_name = None
    for base_name in BASE_NAMES_SORTED:
        if name.startswith(base_name):
            matched_name = base_name
            break
    if matched_name is None:
        parts = name.split('_')
        matched_name = '_'.join(parts[:2])
    CLASS_NAME_MAP[class_id] = matched_name

# Track recently detected objects
recent_detections = {}
detection_lock = threading.Lock()  # Thread lock for recent_detections

def blink_led(pin, duration=0.3):
    """Non-blocking LED blink"""
    def blink():
        GPIO.output(pin, GPIO.HIGH)
        time.sleep(duration)
        GPIO.output(pin, GPIO.LOW)
    threading.Thread(target=blink).start()

def lookup_product(name):
    """Cache product lookups to reduce Firebase queries"""
    if not hasattr(lookup_product, 'cache'):
        lookup_product.cache = {}
    
    if name in lookup_product.cache:
        return lookup_product.cache[name]
    
    docs = db.collection("products").where("name", "==", name).limit(1).get()
    if docs:
        lookup_product.cache[name] = docs[0].to_dict()
        return lookup_product.cache[name]
    return None

def process_frame(frame, model, frame_scale=0.5):
    """Optimized frame processing with downscaling"""
    # Downscale frame for faster processing
    if frame_scale < 1.0:
        small_frame = cv2.resize(frame, (0, 0), fx=frame_scale, fy=frame_scale)
    else:
        small_frame = frame
    
    # Run detection
    results = model(small_frame, verbose=False)
    
    # Scale coordinates back up if we downscaled
    if frame_scale < 1.0:
        for result in results:
            for box in result.boxes:
                box.xyxy *= (1/frame_scale)
    
    return results

def add_to_cart(product):
    """Optimized cart addition with threading"""
    def _add_to_cart():
        cart_ref = db.collection("carts").document("current")
        try:
            cart = cart_ref.get()
            if cart.exists:
                items = cart.to_dict().get("items", [])
                found = False
                for item in items:
                    if item.get("barcode") == product.get("barcode"):
                        item["quantity"] += 1
                        item["timestamp"] = datetime.now()
                        found = True
                        break
                
                if found:
                    cart_ref.update({"items": items})
                    print(f"➕ Updated quantity for: {product['name']}")
                    blink_led(BLUE_LED)
                else:
                    new_item = {
                        "barcode": product.get("barcode", ""),
                        "name": product["name"],
                        "price": product.get("price", 0),
                        "quantity": 1,
                        "timestamp": datetime.now()
                    }
                    cart_ref.update({"items": firestore.ArrayUnion([new_item])})
                    print(f"✅ Added to cart: {product['name']}")
                    blink_led(GREEN_LED)
            else:
                cart_ref.set({
                    "items": [{
                        "barcode": product.get("barcode", ""),
                        "name": product["name"],
                        "price": product.get("price", 0),
                        "quantity": 1,
                        "timestamp": datetime.now()
                    }]
                })
                print(f"✅ Created cart with: {product['name']}")
                blink_led(GREEN_LED)
        except Exception as e:
            print(f"❌ Error updating cart: {e}")
    
    # Run in separate thread to avoid blocking
    threading.Thread(target=_add_to_cart).start()

def main():
    # Camera initialization with optimized settings
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open camera")
        GPIO.cleanup()
        return
    
    # Optimized camera settings for Raspberry Pi
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 15)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce buffer to minimize lag
    
    # Warm up camera
    for _ in range(5):
        cap.read()
    
    print("System ready! Press 'q' to quit.")
    
    try:
        last_detection_time = time.time()
        while True:
            # Clear camera buffer by reading a few frames
            for _ in range(2):
                cap.grab()
            
            ret, frame = cap.read()
            if not ret:
                print("Failed to grab frame, retrying...")
                time.sleep(0.1)
                continue
            
            # Process frame in a separate thread for better responsiveness
            results = process_frame(frame, model, frame_scale=0.75)
            
            # Update detection status LED
            current_time = time.time()
            if len(results[0].boxes) > 0:
                GPIO.output(RED_LED, GPIO.LOW)
                last_detection_time = current_time
            elif current_time - last_detection_time > 1.0:
                GPIO.output(RED_LED, GPIO.HIGH)
            
            # Draw detections on frame
            for result in results:
                for box in result.boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())
                    class_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    
                    product_name = CLASS_NAME_MAP.get(class_id, f"ID {class_id}")
                    color = (0, 255, 0) if conf > 0.5 else (0, 0, 255)
                    
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(frame, f"{product_name} {conf:.2f}", 
                               (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 
                               0.6, color, 2)
                    
                    # Handle cart additions
                    if conf > 0.5:
                        with detection_lock:
                            if class_id not in recent_detections or \
                               current_time - recent_detections[class_id] > 1.0:
                                recent_detections[class_id] = current_time
                                product = lookup_product(product_name)
                                if product:
                                    time.sleep(0.5)  # Small delay to prevent duplicates
                                    add_to_cart(product)
            
            # Display frame
            cv2.imshow('Product Scanner', frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            
            # Small delay to prevent CPU overload
            time.sleep(0.05)
            
    finally:
        cap.release()
        cv2.destroyAllWindows()
        GPIO.cleanup()

if __name__ == "__main__":
    main()