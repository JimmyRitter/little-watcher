from flask import Flask, Response
from picamera2 import Picamera2
import io
import cv2

app = Flask(__name__)

def gen_frames():
    picam2 = Picamera2()
    picam2.start_preview()  # Start the preview to configure the camera
    preview_config = picam2.create_preview_configuration(main={"size": (640, 480)})
    picam2.configure(preview_config)

    picam2.start()

    while True:
        buffer = picam2.capture_array()  # Capture frame as a numpy array
        ret, jpeg = cv2.imencode('.jpg', buffer)  # Convert frame to JPEG
        frame = jpeg.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
