import os
import time
import boto3
import asyncio
from datetime import datetime, timedelta
import RPi.GPIO as GPIO
import logging
import jsonpickle
from dotenv import load_dotenv
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder

load_dotenv()  # This line brings all environment variables from .env into os.environ

# # Enable logging at the DEBUG level
# logger = logging.getLogger('azure')
# logger.setLevel(logging.DEBUG)

# # Configure console output
# stream_handler = logging.StreamHandler()
# logger.addHandler(stream_handler)

# Constants
MOTION_SENSOR_PIN = 37  # GPIO26 when using GPIO.BOARD numbering scheme
LED_PIN = 13  # Where LED is connected on breadboard
MOTION_SECONDS_TO_RECORD = 10  # How much seconds of motion should be the limit to start recording (the less, the more sensitive it is)

# GPIO Setup
GPIO.setmode(GPIO.BOARD)
GPIO.setup(MOTION_SENSOR_PIN, GPIO.IN)
GPIO.setup(LED_PIN, GPIO.OUT)
GPIO.output(LED_PIN, False)

motion_times = []  # how many times the PIR sensor detection detected movement

picam2 = Picamera2()  # Camera setup

# prepare folder to upload recorded midias
midia_path = "./midia"
if not os.path.exists(midia_path):
    os.mkdir(midia_path)


def upload_midia(file_name):
    """Save media to S3"""
    
    s3_client = boto3.client('s3')

    full_path = os.path.join("./midia", file_name)

    print("\nUploading to S3:\n\t" + file_name)

    # Upload the created file
    with open(file=full_path, mode="rb") as data:
        s3_client.upload_fileobj(data, os.environ["AWS_S3_RECORDINGS_BUCKET"], file_name)

    expiration_time = 60 * 60 * 24

    presigned_url = s3_client.generate_presigned_url('get_object',
                                                    Params={'Bucket': os.environ["AWS_S3_RECORDINGS_BUCKET"],
                                                            'Key': file_name},
                                                    ExpiresIn=expiration_time)

    return presigned_url


def setup_picture():
    camera_config = picam2.create_preview_configuration()
    picam2.configure(camera_config)
    picam2.start()


def setup_video():
    video_config = picam2.create_video_configuration(
        main={"format": "XRGB8888", "size": (1280, 720)}
    )
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
    time.sleep(int(os.environ["RECORDING_TIME_IN_SECONDS"]))
    picam2.stop_recording()
    GPIO.output(LED_PIN, False)
    print("Finished recording video")
    recorded_at = datetime.now().strftime("%m/%d/%Y-%H:%M:%S")
    payload = {
        "midia-name": filename,
        "recorded-at": recorded_at,
    }
    
    # How to call async function from a sync parent function
    # asyncio.run(send_succesful_message_to_iot_hub(jsonpickle.dumps(payload)))
    # print("Send message to IoT Hub")

    file_url = upload_midia(filename)
    print("File Uploaded")

    send_email(file_url, recorded_at)
    print("Email Sent")

# async def send_succesful_message_to_iot_hub(payload):
#     await device_client.send_message(Message(data=payload))


def should_start_midia_capture():
    time_limit = datetime.now() - timedelta(seconds=MOTION_SECONDS_TO_RECORD)
    new_list = [times for times in motion_times if times > time_limit]
    minium_movements_detection = 2
    return len(new_list) >= minium_movements_detection


def detect_motion(channel):

    """Callback function to detect motion."""
    if GPIO.input(channel):
        print("Motion detected!")

        # list of when movement was detected, so it decideds if should start recording
        now = datetime.now()
        motion_times.append(now)

        if should_start_midia_capture():
            record_video()
            # take_picture()
        else:
            print("not enough movement to start recording")


def send_email(file_url, motion_date_time):
    """
        For sending email, it's using AWS WorkMail & SES.
        Workmail provides us a free domain name and custom emails.
        With this, we can register for SES, and use the free domain,
        so emails can be sent from python using SES
    """
    try:
        client = boto3.client('ses')

        response = client.send_email(
            Source=os.environ["AWS_SES_EMAIL_SOURCE_ADDRESS"],
            Destination={
                'ToAddresses': [os.environ["AWS_SES_EMAIL_RECIPIENT_ADDRESS"]],
            },
            Message={
                'Subject': {
                    'Data': 'Motion detected!',
                },
                'Body': {
                    'Text': {
                        'Data': f"Motion was detected on {motion_date_time}, and you can access the recording on the link below:\n{file_url}\nThe link expires in 24h from the recording time.",
                    },
                }
            }
        )
            
        return response
    except Exception as ex:
        print(ex)

async def main():
    """Main program loop."""
    print("Calibrating...")
    time.sleep(3)  # Calibration time for the sensor
    print("Started....")

    # setup if it's picture or video, as its not ready to work both at same time
    # setup_picture()
    setup_video()

    # Setup event detection
    GPIO.add_event_detect(
        MOTION_SENSOR_PIN, GPIO.BOTH, callback=detect_motion, bouncetime=200
    )

    try:
        while True:
            time.sleep(0.01)  # Keep program running

    except RuntimeError as e:
        print(f"Error setting up GPIO: {e}")
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        GPIO.cleanup()  # Clean up GPIO on CTRL+C exit
        picam2.stop()  # Stop the camera
        print("GPIO and camera cleanup done")

if __name__ == "__main__":
    asyncio.run(main())
