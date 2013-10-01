import pygame
import cairo
import numpy
import Image

from pygame import locals as pygame_locals

from color import Color

class Event(object):
    EVENT_TYPES = ['click', 'mouse_down', 'mouse_up', 'mouse_move', 'key_down', 'key_up', 'key_press']
    def __init__(self, event_type='click', x=None, y=None, button=None, key=None):
        self.event_type = event_type
        self.x = x
        self.y = y 
        self.button = button
        self.key = key
        if not event_type in Event.EVENT_TYPES:
            raise Exception('Unsupported Event %s' % event)

    def __unicode__(self):
        return u'Event %s @(%s,%s), button %s, key %s' % (self.event_type, self.x, self.y, self.button, self.key)
    __repr__ = __unicode__

class BaseGUI(object):
    """ Very simple gui base class that takes care of pygame/cairo setup. 
        Register event handlers by adding a callable expecting an event object to BaseGUI.event_handlers
    """

    def __init__(self, width = None, height = None, caption = "DisplayTest", *args, **kwargs):
        self.pygame_setup(width, height, caption)
        self.cairo_setup()

        self.event_handlers = []
        super(BaseGUI, self).__init__(*args, **kwargs)

    def pygame_setup(self, width, height, caption, *args, **kwargs):
        pygame.init()
        if not width or not height:
            info = pygame.display.Info()
            width = info.current_w
            height = info.current_h
        self.width = width
        self.height = height

        screen = pygame.display.set_mode((width, height))#, pygame_locals.FULLSCREEN)
        pygame.display.set_caption(caption)
        self.screen = screen
        self.clock = pygame.time.Clock()
        
        background = pygame.Surface(screen.get_size())
        background.fill((255, 255, 255))
        
        screen.blit(background, (0, 0))
        pygame.display.flip()

    def cairo_setup(self):
        data = numpy.empty(self.width * self.height * 4, dtype=numpy.int8)

        self.cairo_surface = cairo.ImageSurface.create_for_data(data, cairo.FORMAT_ARGB32, self.width, self.height, self.width * 4)
        self.cairo_context = cairo.Context(self.cairo_surface)  
        self.cairo_context.set_antialias(cairo.ANTIALIAS_SUBPIXEL)
        self.cairo_context.set_line_width(1)
        self.fill(Color(1, 1, 1))

    def process_events(self):
        for e in pygame.event.get():
            mousepos = pygame.mouse.get_pos()
            x, y = int(mousepos[0]), int(mousepos[1])
            event = None

            if e.type == pygame_locals.MOUSEMOTION:
                event = Event('mouse_move', x, y)
                
            if e.type == pygame_locals.KEYDOWN:
                event = Event('key_down', x, y, key=e.unicode)

            if e.type == pygame_locals.MOUSEBUTTONDOWN:
                # Handle the special case of touchpad taps, 
                # which are just mouse_downs without the corresponding mouse_up
                pressed = pygame.mouse.get_pressed()
                if pressed[0] == pressed[1] == pressed[2] == 0:
                    event = Event('click', x, y, button=e.button)
                else:    
                    event = Event('mouse_down', x, y, button=e.button)

            if e.type == pygame_locals.MOUSEBUTTONUP:
                event = Event('mouse_up', x, y, button=e.button)

            if event:
                for handler in self.event_handlers:
                    handler(event)
                return event
        return Event()

    def set_color(self, color):
        self.cairo_context.set_source_rgba(color.r, color.g, color.b, color.a)

    def fill(self, color):
        """ Fill the entire surface with one color """
        self.set_color(color)
        self.cairo_context.paint()

    def rotate(self, angle):
        """ Rotates the transformation matrix, this only has an effect on 
            newly drawn things and is kind of useless.
        """
        self.cairo_context.rotate(self.from_degrees(angle))

    def reverse_rotate(self, angle):
        self.rotate(self.from_degrees(-angle))

    def scale(self, amount=1):
        self.cairo_context.scale(amount, amount)

    def reverse_scale(self, amount=1):
        self.scale(1.0 / amount)

    def translate(self, x, y):
        self.cairo_context.translate(x, y)

    def reverse_translate(self, x, y):
        self.translate(-x, -y)

    def transform(self, translate_x = 0, translate_y = 0, scale = 1, rotate = 0 ):
        self.translate(translate_x, translate_y)
        self.scale(scale)
        self.rotate(rotate)

    def reverse_transform(self, translate_x = 0, translate_y = 0, scale = 1, rotate = 0):
        self.rotate(-rotate)
        self.cairo_context.scale(1.0 / scale, 1.0 / scale)
        self.cairo_context.translate(translate_x * -1, translate_y * -1)

    def from_degrees(self, degrees):
        return degrees * math.pi / 180.0

    def _bgra_surf_to_rgba_string(self):
        img = Image.frombuffer('RGBA', (self.width, self.height), self.cairo_surface.get_data(), 'raw', 'BGRA', 0, 1)
        return img.tostring('raw', 'RGBA', 0, 1)

    def update(self):
        data_string = self._bgra_surf_to_rgba_string()
        pygame_surface = pygame.image.frombuffer(data_string, (self.width, self.height), 'RGBA')
        self.screen.blit(pygame_surface, (0,0)) 
        pygame.display.flip()