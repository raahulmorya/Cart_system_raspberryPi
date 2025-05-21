import RPi.GPIO as GPIO
import cv2
import numpy as np
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import time
import threading
from ultralytics import YOLO

# LED Setup
GPIO.setmode(GPIO.BCM)
GREEN_LED = 17  # New item added
BLUE_LED = 27   # Quantity updated
RED_LED = 22    # No recognized items
GPIO.setup(GREEN_LED, GPIO.OUT)
GPIO.setup(BLUE_LED, GPIO.OUT)
GPIO.setup(RED_LED, GPIO.OUT)

# Initialize Firebase
cred = credentials.Certificate("serviceAccount.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Initialize YOLO model
model = YOLO('honey.pt')

# Product name mapping
# Create a list of all product base names from your database
BASE_NAMES = [
     "amul_darkchocolate", "balaji_aloo_sev", "balaji_ratlami_sev", 
    "balaji_wafers_chaatchaska", "balaji_wafers_masalamasti",
    "balaji_wafers_simplysalted", "balaji_wafers_tomatotwist",
    "britannia_marie_gold", "cadbury_celebrations", "closeup",
    "colgate_strong_teeth", "dark_fantasy_choco_fills", "dove_shampoo",
    "dove_soap", "everest_chaat_masala", "everest_garam_masala",
    "head_and_shoulders", "krack_jack", "lakme_peach_moisturiser",
    "lifebuoy", "liril_bodywash", "lux", "maggi", "nescafe_coffee",
    "patanjali_aloevera_gel", "pears", "real_grape_juice", "rin_soap",
    "shreeji_dabeli_masala", "shreeji_undhiyu_masala", "surf_excel",
    "tata_salt", "tresemme_black", "vaseline_aloe_fresh",
    "veg_hakka_noodles", "vicco_vajradanti", "vim_bar"
]

# Pre-sort the base names by length (longest first) for more efficient matching
BASE_NAMES_SORTED = sorted(BASE_NAMES, key=len, reverse=True)

CLASS_NAME_MAP = {}
for class_id, name in model.names.items():
    # Find the longest matching base name
    matched_name = None
    for base_name in BASE_NAMES_SORTED:
        if name.startswith(base_name):
            matched_name = base_name
            break
    
    # If no match found, fall back to first two parts
    if matched_name is None:
        parts = name.split('_')
        matched_name = '_'.join(parts[:2])
    
    CLASS_NAME_MAP[class_id] = matched_name

# Track recognized items
last_recognition_time = time.time()
RECOGNITION_TIMEOUT = 2  # Seconds before red LED activates

def blink_led(pin, duration=0.5):
    """Blink an LED for visual feedback"""
    GPIO.output(pin, GPIO.HIGH)
    time.sleep(duration)
    GPIO.output(pin, GPIO.LOW)

def set_led_state(recognized):
    """Control red LED based on recognition state"""
    global last_recognition_time
    if recognized:
        last_recognition_time = time.time()
        GPIO.output(RED_LED, GPIO.LOW)
    elif time.time() - last_recognition_time > RECOGNITION_TIMEOUT:
        GPIO.output(RED_LED, GPIO.HIGH)

def add_to_cart(product):
    """Modified to include LED feedback"""
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
                threading.Thread(target=blink_led, args=(BLUE_LED,)).start()
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
                threading.Thread(target=blink_led, args=(GREEN_LED,)).start()
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
            threading.Thread(target=blink_led, args=(GREEN_LED,)).start()
            
    except Exception as e:
        print(f"❌ Error updating cart: {e}")

def process_frame(frame):
    global last_recognition_time
    recent_detections = {}  # Reset each frame
    
    results = model(frame, verbose=False)
    recognized = False
    
    for result in results:
        for box in result.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())
            class_id = int(box.cls[0])
            conf = float(box.conf[0])
            
            product_name = CLASS_NAME_MAP.get(class_id, f"ID {class_id}")
            color = get_category_color(class_id)
            
            # Draw bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, f"{product_name} {conf:.2f}", 
                       (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            
            if conf > 0.5:
                recognized = True
                if class_id not in recent_detections:
                    product = lookup_product(product_name)
                    if product:
                        recent_detections[class_id] = time.time()
                        threading.Thread(
                            target=lambda: (time.sleep(1), add_to_cart(product))
                        ).start()
    
    set_led_state(recognized)
    return frame

def main():
    try:
        # Initialize LEDs
        GPIO.output(GREEN_LED, GPIO.LOW)
        GPIO.output(BLUE_LED, GPIO.LOW)
        GPIO.output(RED_LED, GPIO.HIGH)  # Start with red LED on
        
        # Camera setup
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        print("System ready! LEDs:")
        print("- Green: New item added")
        print("- Blue: Quantity updated")
        print("- Red: No items recognized")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Failed to grab frame")
                time.sleep(0.1)
                continue
            
            frame = process_frame(frame)
            cv2.imshow('Product Scanner', frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
    finally:
        cap.release()
        cv2.destroyAllWindows()
        GPIO.cleanup()

if __name__ == "__main__":
    main()