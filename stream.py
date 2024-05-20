from flask import Flask, Response
from picamera2 import Picamera2
import cv2
import signal
import sys
import boto3

app = Flask(__name__)
picam2 = Picamera2()

# AWS Kinesis Video Stream configuration
stream_name = 'my-kvs-stream'  # Replace with your Kinesis Video Stream name
region_name = 'eu-west-1'  # Replace with your AWS region

# Initialize Kinesis Video Stream client
kvs_client = boto3.client('kinesisvideo', region_name=region_name)

# Get the endpoint for the Kinesis Video Stream
response = kvs_client.get_data_endpoint(
    StreamName=stream_name,
    APIName='PUT_MEDIA'
)
endpoint = response['DataEndpoint']

# Initialize the Kinesis Video Stream media client
kvs_media_client = boto3.client('kinesis-video-media', endpoint_url=endpoint)


def init_camera():
    picam2.start_preview()  # Start the preview to configure the camera
    preview_config = picam2.create_preview_configuration(main={"size": (1300, 1050), "format": "XRGB8888"})
    picam2.configure(preview_config)
    picam2.start()

def send_frame_to_kinesis(frame):
    # Send frame to Kinesis Video Stream
    kvs_media_client.put_media(
        StreamName=stream_name,
        Payload=frame
    )
 
    
def gen_frames():
    while True:
        buffer = picam2.capture_array()
        ret, jpeg = cv2.imencode('.jpg', buffer)  # Convert frame to JPEG
        frame = jpeg.tobytes()
        send_frame_to_kinesis(frame)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

def signal_handler(sig, frame):
    print('You pressed Ctrl+C!')
    if picam2:
        picam2.stop()
    sys.exit(0)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    init_camera()
    app.run(host='0.0.0.0', port=5000)
