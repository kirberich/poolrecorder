from twisted.web import http
from twisted.web.http import HTTPChannel
from twisted.internet import reactor, defer
import threading
import os


class RecorderHandler(http.Request, object):
    BOUNDARY = "jpgboundary"

    def __init__(self, api, *args, **kwargs):
        self.api = api
        super(RecorderHandler, self).__init__(*args, **kwargs)

    def get_frame(self):
        return self.api.recorder.current_jpg_frame

    def wait(self, seconds, result=None):
        """Returns a deferred that will be fired later"""
        d = defer.Deferred()
        reactor.callLater(seconds, d.callback, result)
        return d

    def writeBoundary(self):
        self.write("--%s\n" % (self.BOUNDARY))

    def writeStop(self):
        self.write("--%s--\n" % (self.BOUNDARY))

    def not_found(self, message=None):
        self.setResponseCode(404, message)
	self.setHeader("Content-Type", "image/gif")
	f = open("404.gif", "r")
	content = f.read()
	self.write(content)
        self.finish()

    def simple_render(self, content, content_type="text/plain"):
        self.render(content, [("Content-Type", content_type)])

    def render(self, content, headers):
        for (header_name, header_value) in headers:
            self.setHeader(header_name, header_value)
        self.write(content)
        self.finish()

    @defer.inlineCallbacks
    def serve_stream(self):
        """ Serve video stream as multi-part jpg. Yes, this actually works. """
        boundary = "jpgboundary"

        self.setHeader('Connection', 'Keep-Alive')
        self.setHeader('Content-Type', "multipart/x-mixed-replace;boundary=%s" % boundary)

        while True:
            content = self.get_frame()
            self.write("Content-Type: image/jpg\n")
            self.write("Content-Length: %s\n\n" % (len(content)))
            self.write(content)
            self.write("--%s\n" % (boundary))
            yield self.wait(0.05)

    def serve_stream_container(self):
        headers = [("content-type", "text/html")]
        content = "<html><head><title>Potato Pool Camera</title></head><body><img src='/stream.avi' alt='stream'/></body></html>"
	self.render(content, headers)

    def serve_frame(self):
        return self.simple_render(self.get_frame(), "image/jpg")

    def serve_latest_video(self):

        candidates = os.listdir(".")
        candidates = sorted([x for x in candidates if x.startswith("pool-")])
        if not candidates:
            return self.not_found()

        file_name = candidates[0]
        f = open(file_name)
        content = f.read()

        headers = [
            ("content-type", "application/octet-stream"),
            ('content-disposition', 'attachment; filename="%s"' % file_name)
        ]
        self.render(content, headers)

    def process(self):
        command_args_list = [x for x in self.path.split("/") if x]
        command = ""
        args = []
        if command_args_list:
            command = command_args_list[0]
            args = command_args_list[1:]

        try:
            if command == "save":
                self.api.trigger("save")
                return self.simple_render("Saving video.")
            elif command == "quit":
                self.api.trigger("quit")
                return self.simple_render("Quitting.")
            elif command.startswith("current"):
                return self.serve_frame()
            elif command.startswith("latest_video"):
                return self.serve_latest_video()
            elif command.startswith("stream"):
                return self.serve_stream()
            elif command.startswith("show_stream"):
                return self.serve_stream_container()
            elif command == "echo":
                return self.simple_render(args[0])
        except Exception, e:
            return self.simple_render(e.message)

        return self.not_found()


class RecorderHandlerFactory(object):
    def __init__(self, api):
        self.api = api 

    def __call__(self, *args, **kwargs):
        return RecorderHandler(self.api, *args, **kwargs)


class StreamFactory(http.HTTPFactory):
    protocol = HTTPChannel


class Api:
    """ An api for a pool recorder, uses a twisted server inside a thread to keep track of webby things. """

    def __init__(self, recorder):
        # This I believe is what you find when you look up "ugly" in the dictionary
        # But I really don't want to try and understand this FactoryFactoryFactory stuff properly
        HTTPChannel.requestFactory = RecorderHandlerFactory(api=self)

        self.recorder = recorder
        self.events = []

        reactor.listenTCP(8080, StreamFactory())
        t = threading.Thread(target=reactor.run)
        t.daemon = True
        t.start()

    def trigger(self, event):
        self.events.append(event)
