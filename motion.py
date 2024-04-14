import RPi.GPIO as GPIO
import time
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder

# Constants
SENSOR_PIN = 37  # GPIO26 when using GPIO.BOARD numbering scheme

# GPIO Setup
GPIO.setmode(GPIO.BOARD)
GPIO.setup(SENSOR_PIN, GPIO.IN)

picam2 = Picamera2()

# Camera Setup
def setup_picture():
    camera_config = picam2.create_preview_configuration()
    picam2.configure(camera_config)
    picam2.start()

def setup_video():
    video_config = picam2.create_video_configuration()
    picam2.configure(video_config)

def take_picture():
    """Takes a picture and saves it with a timestamp."""
    timestamp = int(time.time())
    filename = f"motion_{timestamp}.jpg"
    picam2.capture_file(filename)
    print(f"Picture saved as {filename}")

def record_video():
    """Records a 5 second video"""
    timestamp = int(time.time())
    encoder = H264Encoder(bitrate=10000000)
    output = f"video_{timestamp}.h264"
    picam2.start_recording(encoder, output)
    time.sleep(10)
    picam2.stop_recording()

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

    # Setup event detection
    GPIO.add_event_detect(SENSOR_PIN, GPIO.BOTH, callback=detect_motion, bouncetime=200)

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
