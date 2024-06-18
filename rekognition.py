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

GPIO.setmode(GPIO.BOARD)

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


def setup_video():
    video_config = picam2.create_preview_configuration(
        main={
            "size": (1100, 800)
            # "format": "XRGB8888"
        } 
    )
    picam2.configure(video_config)

def record_video():
    timestamp = int(time.time())
    bitrate = 10000000  # 10 Mbps bitrate
    encoder = H264Encoder(bitrate=bitrate)
    filename = f"video_{timestamp}.mp4"  # MPEG-4 format
    output = f"./midia/{filename}"
    picam2.start_recording(encoder, output)
    time.sleep(int(os.environ["RECORDING_TIME_IN_SECONDS"]))
    picam2.stop_recording()
    print("Finished recording video")
    recorded_at = datetime.now().strftime("%m/%d/%Y-%H:%M:%S")
    
    file_url = upload_midia(filename)
    print("File Uploaded")

    send_email(file_url, recorded_at)
    print("Email Sent")

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
    time.sleep(4)  # Calibration time for the sensor
    print("Started....")
    record_video()

if __name__ == "__main__":
    asyncio.run(main())
