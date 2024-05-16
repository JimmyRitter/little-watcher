from flask import Flask, Response
from picamera2 import Picamera2
import cv2
import signal
import sys

app = Flask(__name__)
picam2 = Picamera2()

def init_camera():
    picam2.start_preview()  # Start the preview to configure the camera
    preview_config = picam2.create_preview_configuration(main={"size": (1100, 800)})
    picam2.configure(preview_config)
    picam2.start()

def gen_frames():
    while True:
        buffer = picam2.capture_array()
        ret, jpeg = cv2.imencode('.jpg', buffer)  # Convert frame to JPEG
        frame = jpeg.tobytes()
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
