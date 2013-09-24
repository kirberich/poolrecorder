#!/usr/bin/python

import cv2, cv
import numpy
import math
import subprocess
import time
import freenect
import random 
import threading
import copy
import datetime

from api import Api
from gui import Gui, Color

DEBUG = False
SHOW_WINDOW = True

class Recorder(object):
    def __init__(self, num_frames=30*25, limit_fps=None):
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

        self.gui = Gui()

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

    def to_grayscale(self, image):
        tmp = cv.CreateImage(cv.GetSize(image), image.depth, 1)
        cv.CvtColor(image, tmp,cv.CV_BGR2GRAY)
        image = self.array(tmp)
        return image 

    def calibrate(self):
        """ Fill gui with white, capture a frame, fill with black, capture another frame.
            Substract the images and calculate a threshold, generate a gradient to get the borders.
            Calculate a transformation matrix that converts from the coordinates on the frame to screen coordinates.
        """
        self.gui.fill(Color(255, 255, 255))
        self.gui.update()
        time.sleep(0.2)
        white_frame = self.to_grayscale(self.capture_frame(as_array=False))

        self.gui.fill(Color(0, 0, 0))
        self.gui.update()
        time.sleep(0.2)
        black_frame = self.to_grayscale(self.capture_frame(as_array=False))

        # Calculate threshold and gradient to end up with an image with just the border of the screen as white pixels
        diff_frame = cv2.subtract(white_frame, black_frame)
        threshold_frame = cv2.threshold(diff_frame, 80, 255, cv2.THRESH_BINARY)[1]
        gradient_frame = cv2.Laplacian(threshold_frame, cv2.CV_64F)

        cv2.imwrite("white.jpg", white_frame)
        cv2.imwrite("black.jpg", black_frame)
        cv2.imwrite("diff.jpg", diff_frame)
        cv2.imwrite("threshold.jpg", threshold_frame)
        cv2.imwrite("gradient.jpg", gradient_frame)

        self.gui.fill(Color(255, 255, 255))
        self.gui.update()

        # Get list of all white pixels in the gradient as [(x,y), (x,y), ...]
        border_candidate_points = numpy.transpose(gradient_frame.nonzero())
        border_left = []
        border_right = []
        border_top = []
        border_bottom = []

        for x in range(0, 100):
            candidate = random.choice(border_candidate_points)
            can_x, can_y = candidate
            up = down = left = right = None
            # Walk along a 13x13 square path around the point and look for other border points
            for x in range(-6, 7):
                for y in [-6, 7]:
                    if gradient_frame[can_x+x][can_y+y] == 255:
                        if y < 0:
                            down = (can_x+x, can_y+y)
                        else:
                            up = (can_x+x, can_y+y)

            for y in range(-6, 7):
                for x in [-6, 7]:
                    if gradient_frame[can_x+x][can_y+y] == 255:
                        if x < 0:
                            left = (can_x+x, can_y+y)
                        else:
                            right = (can_x+x, can_y+y)

            # If two opposing sides of the square have border points, and all three points are roughly on a line
            # then assume this is an actual proper point on the screen border
            point_found = False
            if up and down and not left and not right:
                p = (up[0]-can_x, up[1]-can_y)
                q = (down[0]-can_x, can_y-down[1])
                point_found = True
            elif left and right and not up and not down:
                p = (can_x-left[0], left[1]-can_y)
                q = (right[0]-can_x, can_y-right[1])
                point_found = True

            if point_found:
                p_abs = math.sqrt(p[0]*p[0] + p[1]*p[1])
                q_abs = math.sqrt(q[0]*q[0] + q[1]*q[1])
                if (p[0]*q[0] + p[1]*q[1])/(p_abs*q_abs) > 0.95:
                    black_frame[can_x][can_y] = 255

            # debugging, paint point on original black_frame
            #black_frame[candidate[0]][candidate[1]] = 255
        cv2.imwrite("debug.jpg", black_frame)


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
        #if SHOW_WINDOW:
        #    key = cv2.waitKey(20)
        #    self.handle_keys(key)

        (event_type, x,y) = self.gui.handle_events()
        if event_type == 99:
            self.calibrate()
        print event_type

    def debugging_output(self, frame):
        if DEBUG:
            print "Buffer index: %s" % self.buffer_index
        if SHOW_WINDOW:
            cv2.imshow("preview", frame)

    def capture_frame(self):
        raise NotImplementedError()

    def handle_frame(self, *args, **kwargs):
        raise NotImplementedError()

    def start(self):
        raise NotImplementedError()

class CVCaptureRecorder(Recorder):
    def __init__(self, num_frames=30*25, limit_fps=None):
        super(CVCaptureRecorder, self).__init__(num_frames, limit_fps)
        self.capture = cv.CaptureFromCAM(0)
        cv.SetCaptureProperty(self.capture, cv.CV_CAP_PROP_FRAME_WIDTH, 640)
        cv.SetCaptureProperty(self.capture, cv.CV_CAP_PROP_FRAME_HEIGHT, 480)


        if self.capture: # try to get the first frame
            frame = cv.QueryFrame(self.capture)
        else:
            raise Exception("Could not open video device")

    def capture_frame(self, as_array=True):
        frame = cv.QueryFrame(self.capture)
        if not as_array:
            return frame
        frame_array = numpy.asarray(frame[:,:])
        return frame_array

    def handle_frame(self):
        frame_array = self.capture_frame()

        #small_frame = cv.CreateImage( (self.gui.width, self.gui.height), frame.depth, frame.nChannels)
        #cv.Resize(frame, small_frame)
        #self.gui.draw_image(small_frame)

        self.buffer_frame(frame_array)
        self.debugging_output(frame_array)


class KinectRecorder(Recorder):
    def __init__(self, num_frames=30*25, limit_fps=None):
        super(KinectRecorder, self).__init__(num_frames, limit_fps)

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
        self.handle_events()
        if not self.dev:
            self.dev = dev
            self.ctx = ctx
        if not self.keep_running:
            raise freenect.Kill

    def handle_video_frame(self, dev, data, timestamp):
        self.update_frame_rate()
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
	return
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
    #recorder = CVCaptureRecorder(limit_fps=20)
    recorder = KinectRecorder(limit_fps=40)
    try:
        recorder.loop()
    except KeyboardInterrupt:
        pass
   
