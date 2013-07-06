import cv2, cv
import subprocess
import time

DEBUG = True
SHOW_WINDOW = False

class Recorder(object):
    def __init__(self, width=640, height=480, num_frames=30*25, limit_fps=None):
        self.capture = cv2.VideoCapture(0)
        self.capture.set(cv.CV_CAP_PROP_FRAME_WIDTH, width);
        self.capture.set(cv.CV_CAP_PROP_FRAME_HEIGHT, height);
        if DEBUG:
            cv2.namedWindow("preview")

        if self.capture.isOpened(): # try to get the first frame
            rval, frame = self.capture.read()
        else:
            raise Exception("Could not open video device")

        self.num_frames = num_frames
        self.frames = [None] * self.num_frames
        self.buffer_index = 0

        self.frame_rate = 0
        self.last_frame = time.time()
        self.limit_fps = limit_fps

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

    def buffer_frame(self, frame):
        self.frames[self.buffer_index] = frame
        if self.buffer_index == self.num_frames - 1:
           self.buffer_index = 0
        else:
           self.buffer_index += 1 

    def get_ordered_buffer(self):
        """ Returns buffer in correct frame order """
        return self.frames[self.buffer_index:]+self.frames[:self.buffer_index]

    def save_buffer_to_video(self):
        # Fixme: make shit configurable
        cmdstring = ('ffmpeg',
                     '-r', '%d' % int(round(self.frame_rate)),
                     '-f','image2pipe',
                     '-vcodec', 'mjpeg',
                     '-i', 'pipe:', 
                     '-c:v', 'libx264',
                     '-preset', 'fast',
                     '-crf', '23',
                     'ffmpegtest.avi'
                     )

        p = subprocess.Popen(cmdstring, stdin=subprocess.PIPE)
        for jpg_frame in self.get_ordered_buffer():
            if jpg_frame is not None:
                p.stdin.write(jpg_frame.tostring())
        p.stdin.close()

    def loop(self):
        while True:
            self.update_frame_rate()

            rval, frame = self.capture.read()
            (retval, jpg_frame) = cv2.imencode(".jpg", frame, (cv.CV_IMWRITE_JPEG_QUALITY, 50))
            self.buffer_frame(jpg_frame)

            if DEBUG:
                print "FPS: %s" % round(self.frame_rate)
                print "Buffer index: %s" % self.buffer_index
            if SHOW_WINDOW:
                cv2.imshow("preview", frame)
                key = cv2.waitKey(20)
                if key == 27: # exit on ESC
                    self.save_buffer_to_video()
                    break

if __name__ == "__main__":
    recorder = Recorder(limit_fps = 20)
    try:
        recorder.loop()
    except KeyboardInterrupt:
        recorder.save_buffer_to_video()
   