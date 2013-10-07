# General
DEBUG = False
SHOW_WINDOW = False

# Recorder 
RECORDER = 'kinect' # cv or kinect
LIMIT_FPS = 20
BUFFER_LENGTH = 30*25

# UI 
UI_FULLSCREEN = True
UI_RESOLUTION = None # None for display resolution or tuple (x,y)

# Kinect
TOUCH_LAYERS = {
	# Low, high, value
	# Actual data starts around 125 (closest to sensor), 100 when not using calibration
	'touch': (125, 126, 255), 
	#(160, 180, 150), 
	#(200, 220, 100), 
	#(240, 255, 0) # Background
}
OVERLAY_VIDEO = False

# Calibration
CALIBRATION_THRESHOLD = 40

# Load additional settings
try:
	from custom_settings import *
except:
	pass