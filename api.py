import threading
import os
import datetime

from twisted.web import http
from twisted.web.http import HTTPChannel
from twisted.internet import reactor, defer

from urlparse import urlparse, parse_qs


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
            if self.api.video_locked: 
                self.write("Content-Type image/gif\n")
                f = open("shoo.gif", "r")
                content = f.read()
            else:
                content = self.get_frame()
                self.write("Content-Type: image/jpg\n")
            self.write("Content-Length: %s\n\n" % (len(content)))
            self.write(content)
            self.write("--%s\n" % (boundary))
            yield self.wait(3 if self.api.video_locked else 0.05)

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

        file_name = candidates[-1]
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
            elif command == "videos":
                pass
            elif command == "lock":
                self.lock_video()
                return self.simple_render("locked")
            elif command == "unlock":
                if self.unlock_video():
                    return self.simple_render("Unlocked.")
                else:
                    return self.simple_render("Wrong password.")
            elif command == "active":
                if self.api.recorder.motion_detector.recent_motion():
                    return self.simple_render("true")
                else:
                    return self.simple_render("false")
        except Exception, e:
            return self.simple_render(e.message)

        return self.not_found()

    def lock_video(self):
        seconds = int(self.args['seconds'][0]) if 'seconds' in self.args else None
        password = self.args['password'][0] if 'password' in self.args else None
        self.api.video_locked = True
        self.api.unlock_at = datetime.datetime.now() + datetime.timedelta(seconds=seconds) if seconds else None
        self.api.lock_password = password
        if seconds:
            d = defer.Deferred()
            reactor.callLater(seconds, self.unlock_video, None)
            return d

    def unlock_video(self, *args, **kwargs):
        password = self.args['password'][0] if 'password' in self.args else None
        if not self.api.lock_password or password == self.api.lock_password:
            self.api.video_locked = False
            return True
        return False


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
        self.video_locked = False
        self.lock_password = None
        self.unlock_at = None

        reactor.listenTCP(8080, StreamFactory())
        t = threading.Thread(target=reactor.run)
        t.daemon = True
        t.start()

    def trigger(self, event):
        self.events.append(event)
