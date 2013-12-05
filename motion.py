import cv2, cv
import numpy
import datetime
import settings

class MotionEvent(object):
	def __init__(self, start=None, end=None):
		self.start = start if start else datetime.datetime.now()
		self.end = end

	def ago(self):
		return datetime.datetime.now() - self.end if self.end else datetime.timedelta(seconds=0)

class MotionDetector(object):
	def __init__(self, threshold = settings.MOTION_THRESHOLD, min_sec_between_events=settings.MOTION_EVENT_GAP, timeout_seconds=settings.MOTION_TIMEOUT):
		self.running_average = None
		self.running_average_converted = None
		self._smoothed_frame = None
		self.motion_image = None

		self.min_sec_between_events = min_sec_between_events
		self.min_time_between_events = datetime.timedelta(seconds=min_sec_between_events)
		self.timeout_seconds = timeout_seconds
		self.timeout = datetime.timedelta(timeout_seconds)
		self.threshold = threshold
		self.motion_events = []
		self.motion_avg = None

		# Is there motion being detected right now
		self.motion_detected = False
		# Last time motion was detected
		self.last_motion = None

	def last_event(self):
		return self.motion_events[-1] if self.motion_events else None

	def should_start_new_event(self):
		return not self.motion_events or self.last_event().ago() > self.min_time_between_events

	def update(self, frame):
		size = cv.GetSize(frame)
		if self.motion_image is None:
			self.running_average = cv.CreateImage(size, 32, 3)
			self.running_average_converted = cv.CreateImage(size, frame.depth, 3)
			self._smoothed_frame = cv.CreateImage(size, frame.depth, 3)
			self.motion_image = cv.CreateImage(size, frame.depth, 3)
			return

		cv.Smooth(frame, self._smoothed_frame, cv.CV_GAUSSIAN, 9, 0)
		cv.AbsDiff(self._smoothed_frame, self.running_average_converted, self.motion_image)

		cv.RunningAvg(self._smoothed_frame, self.running_average, 0.5, None)
		cv.ConvertScale(self.running_average, self.running_average_converted)

		motion_avg = float(cv.Sum(self.motion_image)[0])/(size[0]*size[1]) 
		if motion_avg > self.threshold and not self.motion_detected and self.should_start_new_event():
			self.motion_events.append(MotionEvent())
			self.motion_detected = True
		elif motion_avg < self.threshold and self.motion_detected:
			last_event = self.last_event()
			last_event.end = datetime.datetime.now()
			self.motion_events[-1] = last_event
			self.motion_detected = False

		self.motion_avg = motion_avg
		print self.last_event().ago()

	def recent_motion(self):
		last_event = self.last_event()
		if not last_event or last_event.ago() > self.timeout: 
			return False

		return True