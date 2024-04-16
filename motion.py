import os
import time
import RPi.GPIO as GPIO
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from azure.identity import AzureCliCredential
from azure.storage.blob import BlobServiceClient

# import logging

# # Enable logging at the DEBUG level
# logger = logging.getLogger('azure')
# logger.setLevel(logging.DEBUG)

# # Configure console output
# stream_handler = logging.StreamHandler()
# logger.addHandler(stream_handler)

# Constants
MOTION_SENSOR_PIN = 37  # GPIO26 when using GPIO.BOARD numbering scheme
LED_PIN = 13 

# GPIO Setup
GPIO.setmode(GPIO.BOARD)
GPIO.setup(MOTION_SENSOR_PIN, GPIO.IN)


GPIO.setup(LED_PIN, GPIO.OUT)
GPIO.output(LED_PIN, False)

picam2 = Picamera2()


account_url = "https://jimmyiotstorageaccount.blob.core.windows.net"
default_credential = AzureCliCredential()


# # Create the BlobServiceClient object
blob_service_client = BlobServiceClient(account_url, credential=default_credential)


def upload_midia(file_name):
    """Save media to azure"""
    
    # # Create a local directory to hold blob data
    # local_path = "./midia"
    # if not os.path.exists(local_path):
    #     os.mkdir(local_path)
        
    full_path = os.path.join("./midia", file_name)

    # Create a blob client using the local file name as the name for the blob
    blob_client = blob_service_client.get_blob_client(container="1df9de74-a779-4877-a90a-ded37feecbd3", blob=file_name)

    print("\nUploading to Azure Storage as blob:\n\t" + file_name)

    # Upload the created file
    with open(file=full_path, mode="rb") as data:
        blob_client.upload_blob(data)   

# Camera Setup
def setup_picture():
    # camera_config = picam2.create_preview_configuration()
    camera_config = picam2.create_video_configuration(main={"format": 'XRGB8888', "size": (1280, 720), "frame_rate": 15})
    # picam2.configure(video_config)
    picam2.configure(camera_config)
    picam2.start()

def setup_video():
    video_config = picam2.create_video_configuration()
    picam2.configure(video_config)

def take_picture():
    """Takes a picture and saves it with a timestamp."""
    timestamp = int(time.time())
    filename = f"picture_{timestamp}.jpg"
    picam2.capture_file(f"./midia/{filename}")
    
    print(f"Picture saved as {filename}")
    upload_midia(filename)

def record_video():
    """Records a 5 second video"""
    timestamp = int(time.time())
    encoder = H264Encoder(bitrate=10000000)
    filename = f"video_{timestamp}.h264"
    output = f"./midia/{filename}"
    GPIO.output(LED_PIN, True)
    picam2.start_recording(encoder, output)
    time.sleep(10)
    picam2.stop_recording()
    GPIO.output(LED_PIN, False)
    # upload_midia(filename)

def detect_motion(channel):
    """Callback function to detect motion."""
    if GPIO.input(channel):
        print("Motion detected!")
        # take_picture()
        record_video()
    else:
        print("Motion stopped!")

def main(): 
    """Main program loop."""
    print("Calibrating...")
    time.sleep(5)  # Calibration time for the sensor
    print("Started....")

    # setup_picture()
    setup_video()

    # Setup event detection
    GPIO.add_event_detect(MOTION_SENSOR_PIN, GPIO.BOTH, callback=detect_motion, bouncetime=200)

    try:
        while True:
            time.sleep(1)  # Keep program running
    except RuntimeError as e:
        print(f"Error setting up GPIO: {e}")
    except KeyboardInterrupt:
        print('Shutting down...')
    finally:
        GPIO.cleanup()  # Clean up GPIO on CTRL+C exit
        picam2.stop()  # Stop the camera
        print('GPIO and camera cleanup done')

if __name__ == '__main__':
    main()
