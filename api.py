from twisted.web import server, resource
from twisted.web.error import NoResource
from twisted.internet import reactor
import threading
import os

# Resource definitions
class RecorderResource(object, resource.Resource):
	isLeaf = True

	def __init__(self, api, *args, **kwargs):
		self.api = api 
		super(RecorderResource, self).__init__(*args, **kwargs)

	def serve_jpg(self, request, jpg_frame):
		request.setHeader("content-type", "image/jpg")
		return jpg_frame.tostring()

	def serve_latest_video(self, request):
		candidates = os.listdir(".")
		candidates = sorted([x for x in candidates if x.startswith("pool-")])
		if not candidates:
			return NoResource


		file_name = candidates[0]
		f = open(file_name)
		content = f.read()

		request.setHeader("content-type", "application/octet-stream")
		request.setHeader('content-disposition', 'attachment; filename="%s"' % file_name)
		return content

	def render_GET(self, request):
		path = request.path[1:]
		if path == "save":
			self.api.trigger("save")
		elif path == "quit":
			self.api.trigger("quit")
		elif path == "current" or path == "current.jpg":
			return self.serve_jpg(request, self.api.recorder.current_jpg_frame)
		elif path == "latest_video" or path == "latest_video.avi":
			return self.serve_latest_video(request)

		return "'ello."

class Api:
	""" An api for a pool recorder, uses a twisted server inside a thread to keep track of webby things. """

	def __init__(self, recorder):
		self.recorder = recorder
		self.events = []

		reactor.listenTCP(8080, server.Site(RecorderResource(self)))
		t = threading.Thread(target=reactor.run)
		t.daemon = True
		t.start()

	def trigger(self, event):
		self.events.append(event)