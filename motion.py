import os
import time
import asyncio
import datetime
import RPi.GPIO as GPIO
import logging
import jsonpickle
from dotenv import load_dotenv
from picamera2 import Picamera2
from azure.iot.device import Message
from picamera2.encoders import H264Encoder
from azure.identity import AzureCliCredential
from azure.storage.blob import BlobServiceClient
from azure.iot.device.aio import IoTHubDeviceClient

load_dotenv()  # This line brings all environment variables from .env into os.environ

# # Enable logging at the DEBUG level
# logger = logging.getLogger('azure')
# logger.setLevel(logging.DEBUG)

# # Configure console output
# stream_handler = logging.StreamHandler()
# logger.addHandler(stream_handler)

# Constants
MOTION_SENSOR_PIN = 37  # GPIO26 when using GPIO.BOARD numbering scheme
LED_PIN = 13 # Where LED is connected on breadboard
MOTION_SECONDS_TO_RECORD = 10 # How much seconds of motion should be the limit to start recording (the less, the more sensitive it is)

# GPIO Setup
GPIO.setmode(GPIO.BOARD)
GPIO.setup(MOTION_SENSOR_PIN, GPIO.IN)
GPIO.setup(LED_PIN, GPIO.OUT)
GPIO.output(LED_PIN, False)

motion_times = [] # how many times the PIR sensor detection detected movement 
account_url = os.environ['AZURE_STORAGE_ACCOUNT_URL']
conn_str = os.environ['DEVICE_CONNECTION_STRING']

picam2 = Picamera2() # Camera setup
default_credential = AzureCliCredential() # How it will authenticate
blob_service_client = BlobServiceClient(account_url, credential=default_credential)# Create the BlobServiceClient object
device_client = IoTHubDeviceClient.create_from_connection_string(conn_str) # Create instance of the device client using the authentication provider


# prepare folder to upload recorded midias
midia_path = "./midia"
if not os.path.exists(midia_path):
    os.mkdir(midia_path)

def upload_midia(file_name):
    """Save media to azure"""
        
    full_path = os.path.join("./midia", file_name)

    # Create a blob client using the local file name as the name for the blob
    blob_client = blob_service_client.get_blob_client(container="1df9de74-a779-4877-a90a-ded37feecbd3", blob=file_name)

    print("\nUploading to Azure Storage as blob:\n\t" + file_name)

    # Upload the created file
    with open(file=full_path, mode="rb") as data:
        blob_client.upload_blob(data)   

# Camera Setup
def setup_picture():
    camera_config = picam2.create_preview_configuration()
    picam2.configure(camera_config)
    picam2.start()

def setup_video():
    video_config = picam2.create_video_configuration(main={"format": 'XRGB8888', "size": (1280, 720)})
    picam2.configure(video_config)

def take_picture():
    timestamp = int(time.time())
    filename = f"picture_{timestamp}.jpg"
    picam2.capture_file(f"./midia/{filename}")
    
    print(f"Picture saved as {filename}")
    upload_midia(filename)

def record_video():
    timestamp = int(time.time())
    encoder = H264Encoder(bitrate=10000000)
    filename = f"video_{timestamp}.h264"
    output = f"./midia/{filename}"
    GPIO.output(LED_PIN, True)
    picam2.start_recording(encoder, output)
    time.sleep(5)
    picam2.stop_recording()
    GPIO.output(LED_PIN, False)
    print("video recorded")
    print("")
    print("Sending message...")
    payload = {
        "midia-name": filename,
        "recorded-at": datetime.datetime.now().strftime('%m/%d/%Y-%H:%M:%S')
    }
    asyncio.run(send_succesful_message_to_iot_hub(jsonpickle.dumps(payload)))
    
    print("")
    print("Message successfully sent!")
    
    upload_midia(filename)

async def send_succesful_message_to_iot_hub(payload):
    await device_client.send_message(Message(data=payload))

def should_start_midia_capture():
    time_limit = datetime.datetime.now() - datetime.timedelta(seconds=MOTION_SECONDS_TO_RECORD)
    new_list = [times for times in motion_times if times > time_limit]
    minium_movements_detection = 2
    return len(new_list) >= minium_movements_detection

def detect_motion(channel):

    """Callback function to detect motion."""
    if GPIO.input(channel):
        print("Motion detected!")

        # list of when movement was detected, so it decideds if should start recording
        now = datetime.datetime.now()
        motion_times.append(now)
        
        if should_start_midia_capture():
            record_video()
            # take_picture()
        else:
            print("not enough movement to start recording")    

async def main(): 
    """Main program loop."""
    print("Calibrating...")
    time.sleep(5)  # Calibration time for the sensor
    print("Started....")

    # setup if it's picture or video, as its not ready to work both at same time
    # setup_picture()
    setup_video()

    # Setup event detection
    GPIO.add_event_detect(MOTION_SENSOR_PIN, GPIO.BOTH, callback=detect_motion, bouncetime=200)
    
    try:
        # Connect the device client.
        await device_client.connect()

        while True:
            time.sleep(0.01)  # Keep program running

    except RuntimeError as e:
        print(f"Error setting up GPIO: {e}")
    except KeyboardInterrupt:
        print('Shutting down...')
    finally:
        GPIO.cleanup()  # Clean up GPIO on CTRL+C exit
        picam2.stop()  # Stop the camera
        print('GPIO and camera cleanup done')
        await device_client.shutdown()

if __name__ == '__main__':
    asyncio.run(main())
