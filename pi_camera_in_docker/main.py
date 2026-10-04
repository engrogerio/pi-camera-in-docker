import io
import time
import asyncio
import numpy as np
import cv2

from threading import Condition
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse, Response
from contextlib import asynccontextmanager

from picamera2 import Picamera2
from picamera2.encoders import JpegEncoder
from picamera2.outputs import FileOutput


# -------------------------------------------------
# Your original StreamingOutput (kept intact)
# -------------------------------------------------
class StreamingOutput(io.BufferedIOBase):
    def __init__(self, edge_detection=True):
        self.frame = None
        self.condition = Condition()
        self.edge_detection = edge_detection

    def write(self, buf):
        if self.edge_detection:
            img_array = np.frombuffer(buf, dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            edges = cv2.Canny(img, 100, 200)
            _, buf = cv2.imencode('.jpg', edges)
            buf = buf.tobytes()

        with self.condition:
            self.frame = buf
            self.condition.notify_all()


# -------------------------------------------------
# Lifespan: startup / shutdown
# -------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):

    resolution = (1080, 1920)

    picam2 = Picamera2()
    config = picam2.create_video_configuration(
        main={"size": resolution}
    )
    picam2.configure(config)

    output = StreamingOutput(edge_detection=False)

    picam2.start_recording(JpegEncoder(), FileOutput(output))

    app.state.picam2 = picam2
    app.state.output = output

    yield

    picam2.stop_recording()
    picam2.close()


app = FastAPI(lifespan=lifespan)


# -------------------------------------------------
# /stream  (Live MJPEG)
# -------------------------------------------------
def generate_stream(output: StreamingOutput):
    while True:
        with output.condition:
            output.condition.wait()
            frame = output.frame

        yield (
            b"--FRAME\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" +
            frame +
            b"\r\n"
        )


@app.get("/stream")
async def stream():
    return StreamingResponse(
        generate_stream(app.state.output),
        media_type="multipart/x-mixed-replace; boundary=FRAME"
    )


# -------------------------------------------------
# /frame  (Single JPEG)
# -------------------------------------------------
app.get("/frame")
async def frame():
    output = app.state.output

    with output.condition:
        if output.frame is None:
            raise HTTPException(status_code=503, detail="Camera not ready")
        frame = output.frame

    return Response(content=frame, media_type="image/jpeg")


# -------------------------------------------------
# /clip?duration=5.0  (MJPEG clip, no file)
# -------------------------------------------------
@app.get("/clip")
async def clip(duration: float = Query(5.0, ge=0.1, le=60.0)):

    output = app.state.output
    start = time.time()

    def clip_generator():
        while time.time() - start < duration:
            with output.condition:
                output.condition.wait()
                frame = output.frame

            yield (
                b"--FRAME\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" +
                frame +
                b"\r\n"
            )

    return StreamingResponse(
        clip_generator(),
        media_type="multipart/x-mixed-replace; boundary=FRAME"
    )

