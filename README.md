# Smart Product Detection System

![System Overview](hardware/hardware.jpg)

An automated computer vision system that detects products using YOLO object detection and manages a digital cart via Firebase. Designed for Raspberry Pi 4 with LED status indicators.

## Features

- 🛒 Automatic product detection and cart management
- 📷 Real-time camera processing
- 🔴🟢🔵 LED status indicators (Red=No detection, Green=New Item added to cart, Blue=Quantity Updated)
- ☁️ Firebase cloud synchronization
- 🤖 Auto-start on boot

## Hardware Requirements
| Component              | Specification                    |
|------------------------|----------------------------------|
| Raspberry Pi           | 4 (4GB+ recommended)             |
| Camera                 | Official Pi Camera or USB webcam |
| LEDs                   | Red, Green, Blue                 |
| Resistors              | 220Ω (x3)                        |

## Option 1 - One step Initialization 

- Create a firebase project  
- Download Firebase Admin SDK 
- Rename it as serviceAccountKey.json 
- Move file to Cart_system_raspberryPi/
Then run this :

On Windows:
```bash
mkdir CartSystem
cd CartSystem
python -m venv cart_env
Set-ExecutionPolicy Unrestricted -Scope Process
.\cart_env\Scripts\activate
pip install numpy firebase-admin ultralytics pillow tk RPi.GPIO
git clone https://github.com/raahulmorya/Cart_system_raspberryPi
cd Cart_system_raspberryPi
```

On Linux:
```bash
mkdir CartSystem
cd CartSystem
python -m venv cart_env
source cart_env/bin/activate
pip install numpy firebase-admin ultralytics pillow tk RPi.GPIO
git clone https://github.com/raahulmorya/Cart_system_raspberryPi
cd Cart_system_raspberryPi
```
Then switch to [Running the System on Window/Linux](#running-the-system-on-windowlinux)
 
## Option 2 - Create a Virtual Environment
Use the following command to create a virtual environment named myenv:

```bash
python -m venv cart_env
```
This will create a directory cart_env/ containing a standalone Python environment.

## Activate the Virtual Environment

On Windows
```bash
Set-ExecutionPolicy Unrestricted -Scope Process
.\cart_env\Scripts\activate
```

On Linux
Activate it using this command:
```bash
source cart_env/bin/activate
```

Once activated, your terminal will show (cart_env) at the beginning of the prompt.

## Installation

On Windows
```bash
pip install numpy firebase-admin ultralytics pillow tk
```

On Linux
```bash
pip install numpy firebase-admin ultralytics pillow tk 
```
On Linux(Raspberry Pi)
```bash
# 1. Install dependencies
sudo apt update && sudo apt install -y python-pip python-opencv

# 2. Install Python packages
pip install numpy firebase-admin ultralytics pillow tk RPi.GPIO

# 3. Enable camera
sudo raspi-config
# → Interface Options → Camera → Enable
```

## GPIO Wiring
- Green LED  → GPIO 17
- Blue LED   → GPIO 27  
- Red LED    → GPIO 22
- All GND    → Ground (via 220Ω resistors)

## Firebase Setup

- Create Firestore database and name it anything
- Place your serviceAccountKey.json in the project root

Create Collections
```bash
python create_db_structure.py
```

## Running the System on Window/Linux

To test on Windows/Linux
```bash
python detect_products.py
```
If camera not detected Change cv2.VideoCapture(0, backend) with cv2.VideoCapture(1, backend)

## Running the System on Raspberry Pi 4
Manual Start
```bash
python raspberry_pi_detect_products.py
```

Auto-start (systemd)
```bash
sudo cp systemd/product_scanner.service /etc/systemd/system/
sudo systemctl enable --now product_scanner
```

## Live Cart and Checkout
To view Real-Time cart items

In new Terminal
```bash
python smart_cart.py
```
Proceed for checkout 
+ Invoice Generation


## Automate scripts using ssh login
To Enable SSH on Raspberry Pi
-Boot your Raspberry Pi and log in
-Open terminal and run:
```bash
sudo raspi-config
```
Navigate to: Interfacing Options → SSH → Yes → OK → Finish

Reboot if prompted

Setup ssh in Windows
- [Windows Terminal SSH Tutorial](https://learn.microsoft.com/en-us/windows/terminal/tutorials/ssh)

or
Using Git Bash
If you have Git installed, you can use Git Bash which includes SSH:

Open Git Bash from Start menu

Then use ssh normally
or
Using WSL (Windows Subsystem for Linux)
Install WSL: wsl --install in PowerShell (admin)

Then use ssh from the Linux terminal

Once ssh installation done
run this in terminal/git bash
```bash
ssh [USER_NAME]@[RASPBERRY_PI_IP]
```
then Enter password

Now, Create a new script file:

```bash
nano ~/run_cart_system.sh
```


```bash
#!/bin/bash
cd ~/CartSystem
source cart_env/bin/activate
cd Cart_system_raspberryPi
python raspberry_pi_detect_products.py
```
Save (Ctrl+O, Enter) and exit (Ctrl+X)

Make the script executable:

```bash
chmod +x ~/run_cart_system.sh
```
Run it:

```bash
~/run_cart_system.sh
```

Next time when login via ssh, simply run

```bash
~/run_cart_system.sh
```
