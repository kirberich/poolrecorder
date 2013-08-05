#!/usr/bin/python

import cv2, cv
import numpy
import subprocess
import time
import freenect
import random 
import threading
import copy
import datetime

from api import Api

DEBUG = False
SHOW_WINDOW = False

class Recorder(object):
    def __init__(self, width=640, height=480, num_frames=30*25, limit_fps=None):
        if SHOW_WINDOW:
            cv2.namedWindow("preview")

        self.last_video_frame = None

        self.num_frames = num_frames
        self.frames = [None] * self.num_frames
        self.buffer_index = 0

        self.keep_running = True
        self.frame_rate = 0
        self.last_frame = time.time()
        self.limit_fps = limit_fps

        self.api = Api(self)
        self.api_lock = threading.Lock()

    def array(self, image):
        return numpy.asarray(image[:,:])

    def update_frame_rate(self):
        # FIXME: save some kind of average for the fps
        self.frame_diff = time.time() - self.last_frame

        if self.limit_fps:
            minimum_frame_diff = 1.0/self.limit_fps
            if self.frame_diff < minimum_frame_diff:
                time.sleep(minimum_frame_diff - self.frame_diff)
            self.frame_diff = time.time() - self.last_frame

        self.frame_rate = 1.0/self.frame_diff
        self.last_frame = time.time()

        if DEBUG:
            print "FPS: %s" % round(self.frame_rate)

    def buffer_frame(self, frame):
        (retval, jpg_frame) = cv2.imencode(".jpg", frame, (cv.CV_IMWRITE_JPEG_QUALITY, 50))
        jpg_frame = jpg_frame.tostring()
        self.current_jpg_frame = jpg_frame

        self.frames[self.buffer_index] = jpg_frame
        if self.buffer_index >= self.num_frames - 1:
           self.buffer_index = 0
        else:
           self.buffer_index += 1 

    def get_ordered_buffer(self):
        """ Returns buffer in correct frame order """
        return copy.copy(self.frames[self.buffer_index:]+self.frames[:self.buffer_index])

    def loop(self):
        while self.keep_running:
            self.update_frame_rate()
            self.handle_events()
            self.handle_frame()

    def _save_buffer_to_video(self):
        # Fixme: make shit configurable
        output_file = datetime.datetime.now().strftime("pool-%Y-%m-%d %H:%M:%S.avi")
        cmdstring = ('ffmpeg',
                     '-r', '%d' % int(round(self.frame_rate)),
                     '-f','image2pipe',
                     '-vcodec', 'mjpeg',
                     '-i', 'pipe:', 
                     '-c:v', 'libx264',
                     '-preset', 'fast',
                     '-crf', '23',
                     output_file
                     )

        p = subprocess.Popen(cmdstring, stdin=subprocess.PIPE)
        for jpg_frame in self.get_ordered_buffer():
            if jpg_frame is not None:
                p.stdin.write(jpg_frame)
        p.stdin.close()

    def save_buffer_to_video(self):
        t = threading.Thread(target=self._save_buffer_to_video)
        t.daemon = True
        t.start()

    def handle_keys(self, key):
        if key == 27: # exit on ESC
            self.keep_running = False

    def handle_events(self):
        # Handle Api events 
        with self.api_lock:
            for event in self.api.events:
                if event == "save":
                    recorder.save_buffer_to_video()
                elif event == "quit":
                    self.keep_running = False
            self.api.events = []

        # Handle key events, if a window is shown
        if SHOW_WINDOW:
            key = cv2.waitKey(20)
            self.handle_keys(key)

    def debugging_output(self, frame):
        if DEBUG:
            print "Buffer index: %s" % self.buffer_index
        if SHOW_WINDOW:
            cv2.imshow("preview", frame)

    def handle_frame(self, *args, **kwargs):
        raise NotImplementedError()

    def start(self):
        raise NotImplementedError()

class CVCaptureRecorder(Recorder):
    def __init__(self, width=640, height=480, num_frames=30*25, limit_fps=None):
        super(CVCaptureRecorder, self).__init__(width, height, num_frames, limit_fps)
        self.capture = cv.CaptureFromCAM(0)
        cv.SetCaptureProperty(self.capture, cv.CV_CAP_PROP_FRAME_WIDTH, 640)
        cv.SetCaptureProperty(self.capture, cv.CV_CAP_PROP_FRAME_HEIGHT, 480)


        if self.capture: # try to get the first frame
            frame = cv.QueryFrame(self.capture)
        else:
            raise Exception("Could not open video device")

    def handle_frame(self):
        frame = cv.QueryFrame(self.capture)
        frame_array = numpy.asarray(frame[:,:])

        self.buffer_frame(frame_array)
        self.debugging_output(frame_array)


class KinectRecorder(Recorder):
    def __init__(self, width=640, height=480, num_frames=30*25, limit_fps=None):
        super(KinectRecorder, self).__init__(width, height, num_frames, limit_fps)

        # Kinect depth layers
        self.layers = [
            # Low, high, value
            # Actual data starts around 125 (closest to sensor), 100 when not using calibration
            (125, 135, 255), 
            (160, 180, 150), 
            (200, 220, 100), 
            (240, 255, 0) # Background
            ]

        self.overlay_video = False

        # Helper images to display depth overlay over video feed
        self.gray_image = None
        self.temp_image = None

        # Kinect loop settings
        self.dev = None
        self.ctx = None
        self.led_state = 0
        self.tilt = 0

    def threshold(self, depth_map, low, high, value=255):
        depth_map = value * numpy.logical_and(depth_map >= low, depth_map < high)
        return depth_map

    def pretty_depth(self, depth):
        numpy.clip(depth, 0, 2**10 - 1, depth)
        depth >>= 2
        return depth

    def img_from_depth_frame(self, depth):
        depth = depth.astype(numpy.uint8)
        image = cv.CreateImageHeader((depth.shape[1], depth.shape[0]), cv.IPL_DEPTH_8U, 1)
        cv.SetData(image, depth.tostring(), depth.dtype.itemsize * depth.shape[1])
        return image

    def img_from_video_frame(self, video):
        video = video[:, :, ::-1]  # RGB -> BGR
        image = cv.CreateImageHeader((video.shape[1], video.shape[0]),
                                     cv.IPL_DEPTH_8U,
                                     3)
        cv.SetData(image, video.tostring(),
                   video.dtype.itemsize * 3 * video.shape[1])
        return image

    def sync_get_depth_frame(self):
        depth, timestamp = freenect.sync_get_depth()
        depth = self.pretty_depth(depth)
        image = cv.CreateImageHeader((depth.shape[1], depth.shape[0]),
                                     cv.IPL_DEPTH_8U,
                                     1)
        cv.SetData(image, depth.tostring(),
                   depth.dtype.itemsize * depth.shape[1])
        return image

    def sync_get_video_frame(self):
        video = freenect.sync_get_video()[0]
        video = video[:, :, ::-1]  # RGB -> BGR
        image = cv.CreateImageHeader((video.shape[1], video.shape[0]),
                                     cv.IPL_DEPTH_8U,
                                     3)
        cv.SetData(image, video.tostring(),
                   video.dtype.itemsize * 3 * video.shape[1])
        return image

    def set_led(self, led_state):
        if not self.dev:
            print "no device set!"
            return
        freenect.set_led(self.dev, led_state)

    def set_tilt(self, tilt):
        if not self.dev:
            print "no device set!"
            return
        freenect.set_tilt_degs(self.dev, tilt)

    def kinect_body_callback(self, dev, ctx):
        if not self.dev:
            self.dev = dev
            self.ctx = ctx
        if not self.keep_running:
            self.save_buffer_to_video()
            raise freenect.Kill

    def handle_video_frame(self, dev, data, timestamp):
        data = data[:, :, ::-1]  # RGB -> BGR
        video_frame = self.img_from_video_frame(data)
        self.last_video_frame = video_frame

        # Convert the current frame to jpeg and put it into the buffer
        self.buffer_frame(data)

        self.debugging_output(data)

    def handle_keys(self, key):
        super(KinectRecorder, self).handle_keys(key)
        if key == ord('o'):
            self.overlay_video = not self.overlay_video

    def handle_depth_frame(self, dev, data, timestamp):
        self.update_frame_rate()
        depth = self.pretty_depth(data)

        # Calculate depth layers
        depth_layers = numpy.zeros_like(depth)
        for (low, high, value) in self.layers:
            depth_copy = numpy.copy(depth)
            segment = self.threshold(depth_copy, low, high, value=value)
            depth_layers = numpy.add(depth_layers, segment)

        frame = self.img_from_depth_frame(depth_layers)

        frame_array = numpy.asarray(frame[:,:])

        if not self.gray_image:
            self.gray_image = cv.CreateImage(cv.GetSize(frame), frame.depth, 1)
            self.temp_image = cv.CreateImage(cv.GetSize(frame), frame.depth, 1)

        if self.overlay_video:
            if self.gray_image and self.last_video_frame:
                cv.CvtColor(self.last_video_frame,self.gray_image,cv.CV_BGR2GRAY)

            gray_frame_array = self.array(self.gray_image)
            empty_frame_array = numpy.zeros_like(gray_frame_array)
            cv.AddWeighted(self.gray_image, 1, frame, 1, 1, self.temp_image)
            frame_array = self.array(self.temp_image)

    def loop(self):
        """ Freenect has its own looping function, so we have to use that. 
            Put general things that should happen in every frame into the "body" callback.
        """
        freenect.runloop(depth=self.handle_depth_frame, video=self.handle_video_frame, body=self.kinect_body_callback)

if __name__ == "__main__":
    recorder = CVCaptureRecorder(limit_fps=20)
    #recorder = KinectRecorder(limit_fps=40)
    try:
        recorder.loop()
    except KeyboardInterrupt:
        pass
   