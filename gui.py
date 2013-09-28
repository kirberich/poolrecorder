import math
import pygame
import cairo
import numpy
import scipy
import Image
import random
import copy

from pygame import locals as pygame_locals

class Color(object):
    def __init__(self, r = 1, g = 1, b = 1, a = 1):
        self.r = r
        self.g = g
        self.b = b
        self.a = a

    def __repr__(self):
        return 'Color object: (%s,%s,%s,%s)' % (self.r, self.g, self.b, self.a)

class Gui(object):
    def __init__(self, width = None, height = None, caption = "DisplayTest", textureDirectory = "textures"):
        pygame.init()
        if not width or not height:
            info = pygame.display.Info()
            width = info.current_w
            height = info.current_h
        screen = pygame.display.set_mode((width, height))#, pygame_locals.FULLSCREEN)
        pygame.display.set_caption(caption)
        
        background = pygame.Surface(screen.get_size())
        background.fill((255, 255, 255))
        
        screen.blit(background, (0, 0))
        pygame.display.flip()

        data = numpy.empty(width * height * 4, dtype=numpy.int8)

        self.cairo_surface = cairo.ImageSurface.create_for_data(data, cairo.FORMAT_ARGB32, width, height, width * 4)
        self.cairo_context = cairo.Context(self.cairo_surface)  
        self.cairo_context.set_antialias(cairo.ANTIALIAS_SUBPIXEL)
        self.cairo_context.set_line_width(1)

        self.screen = screen
        self.textureDirectory = textureDirectory
        self.width = width
        self.height = height
        self.clock = pygame.time.Clock()

        # Gui elements
        self.element_matrix = numpy.zeros((height, width))
        self.elements = {}
        self.hover_elements = {}
        self.active_elements = {}

    def add_element(self, element_id, area, base_state, hover_state=None, active_state=None, callback=None):
        """ Adds an interface element to the gui
            id: 
                Identifier for this element, needs to be an integer, unique, and equal to the values inside the area matrix
            area: 
                describes what part of the gui should trigger this element,
                this needs to be a numpy array that is 0 outside the element and element_id inside of it
            base_state, hover_state, active_state:
                drawing callables for the element's states
            callback:
                Function to call if this element has been triggered
        """
        # Replace elements in self.element_matrix with elements from area (which should be equal to element_id), where area != 0
        self.element_matrix = scipy.where(area, area, self.element_matrix)

        # Register element 
        self.elements[element_id] = {
            'area': area,
            'base_state': base_state,
            'hover_state': hover_state,
            'active_state': active_state,
            'callback': callback, 
        }

        # Draw element
        self.draw_element_state(base_state)

    def draw_element_state(self, state):
        print "draw_element_state called"
        if not state:
            print "no state"
            return
        if callable(state):
            state()
        else:
            state, args, kwargs = state
            state(*args, **kwargs)

    def element_base(self, element_id, update=True):
        if element_id in self.hover_elements:
            del self.hover_elements[element_id]

        self.draw_element_state(self.elements[element_id]['base_state'])

        if update:
            self.update()

    def element_hover(self, element_id, update=True, force=False):
        if not force and (element_id in self.hover_elements or element_id in self.active_elements):
            print "already hovering"
            return

        if element_id in self.active_elements:
            del self.active_elements[element_id]

        self.hover_elements[element_id] = self.elements[element_id]
        self.draw_element_state(self.hover_elements[element_id]['hover_state'])
        if update:
            self.update()

    def element_active(self, element_id, update=True):
        if element_id in self.active_elements:
            return

        self.active_elements[element_id] = self.elements[element_id]
        self.draw_element_state(self.active_elements[element_id]['active_state'])
        if update:
            self.update()

    def elements_reset(self):
        for element_id in copy.copy(self.hover_elements):
            self.element_base(element_id, update=False)
        self.update()

    def elements_inactive(self):
        for element_id in copy.copy(self.active_elements):
            if element_id in self.hover_elements:
                self.element_hover(element_id, update=False, force=True)
            else:
                self.element_base(element_id, update=False)
        self.update()

    def fill(self, color):
        """ Fill the entire surface with one color """
        self.set_color(color)
        self.cairo_context.paint()

    def draw_circle(self, center, radius, fill_color = None, stroke_color = None):
        """ Draw a circle at center, with a given radius and optional fill_color and stroke_color """
        (x, y) = center
        self.cairo_context.arc(x, y, radius, 0, 2 * math.pi)
        self.apply_colors(fill_color, stroke_color)
        self.cairo_context.close_path()

    def draw_rect(self, x, y, width, height, fill_color = None, stroke_color = None):
        """ Draw a rectangle with its upper left corner at x,y, size of width,height and optional fill_color and stroke_color """
        self.cairo_context.rectangle(x, y, width, height)
        self.apply_colors(fill_color, stroke_color)
        self.cairo_context.close_path()

    def draw_pixel(self, x, y, color = None):
        """ Draw a pixel. """
        self.cairo_context.rectangle(x, y, 1, 1)        
        if color: self.set_color(color)
        self.cairo_context.fill()
        self.cairo_context.new_path()

    def draw_pixels(self, pixels):
        for pixel in pixels:
            self.draw_pixel(*pixel)

    def draw_polygon(self, coordinates, fill_color = None, stroke_color = None):
        """ Draw an n-sided polygon """
        if len(coordinates) < 3: raise Exception("Polygons need to have at least three points")
        self.cairo_context.move_to( coordinates[0][0], coordinates[0][1] )
        for (x,y) in coordinates[1:]:
            self.cairo_context.line_to(x,y)
        self.apply_colors(fill_color, stroke_color)

    def draw_text(self, x, y, text, fill_color = None, stroke_color = None):
        self.cairo_context.move_to(x,y)
        self.cairo_context.text_path(text)
        self.apply_colors(fill_color, stroke_color)

    def draw_line(self, x1, y1, x2, y2, fill_color = None, stroke_color = None):
        self.cairo_context.move_to(x1, y1)
        self.cairo_context.line_to(x2, y2)
        self.apply_colors(fill_color, stroke_color)

    def draw_image(self, image):
        image = image.tostring()[::-1]
        pygame_surface = pygame.image.frombuffer(image, (self.width, self.height), 'RGB')
        pygame_surface = pygame.transform.flip(pygame_surface, True, True)
        self.screen.blit(pygame_surface, (0,0)) 

    def draw_image_slow(self, image):
        h,w = image.shape
        image = image/255.0
        for x in range(0, w):
            for y in range(0, h):
                color = Color(image[y][x], image[y][x], image[y][x])
                self.draw_pixel(x,y, color)

    def apply_colors(self, fill_color, stroke_color):
        """ Apply fill and stroke colors to the current path """
        if fill_color:
            self.set_color(fill_color)
            self.cairo_context.fill_preserve()
        if stroke_color:
            self.set_color(stroke_color)
            self.cairo_context.stroke()

        self.cairo_context.new_path()

    def set_color(self, color):
        self.cairo_context.set_source_rgba(color.r, color.g, color.b, color.a)

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

    def cairo_drawing_test(self):
        """ Just a cairo test """ 
        # Reset background
        self.cairo_context.set_source_rgba(1, 1, 1, 1)
        self.cairo_context.paint()

        self.cairo_context.set_line_width(100)
        self.cairo_context.arc(320, 240, 200, 0, 1.9 * math.pi)
     
        self.cairo_context.set_source_rgba(1, 0, 0, random.random())
        self.cairo_context.fill_preserve()
     
        self.cairo_context.set_source_rgba(0, 1, 0, 0.5)
        self.cairo_context.stroke()

    def _bgra_surf_to_rgba_string(self):
        width = self.cairo_surface.get_width()
        height = self.cairo_surface.get_height()
        img = Image.frombuffer('RGBA', (width, height), self.cairo_surface.get_data(), 'raw', 'BGRA', 0, 1)

        return img.tostring('raw', 'RGBA', 0, 1)

    def handle_events(self):
        for event in pygame.event.get():
            mousepos = pygame.mouse.get_pos()
            x, y = int(mousepos[0]), int(mousepos[1])
            element_id = self.element_matrix[y][x]
            if(pygame.mouse.get_pressed()[1] == 1):
                return ("w", x, y)

            if event.type == pygame_locals.MOUSEMOTION:
                if element_id: 
                    self.element_hover(element_id)
                else:
                    self.elements_reset()
                
            if event.type == pygame_locals.KEYDOWN:
                if(event.key == pygame_locals.K_p):
                    exit(0)
                    return ("p", x, y)
                return((event.key,-1,-1))

            if event.type == pygame_locals.MOUSEBUTTONDOWN:
                if(event.button == 1):
                    if element_id: 
                        self.element_active(element_id)
                    return ("LMBD", x, y)
                if(event.button == 3):
                    return ("RMBD", x, y)

            if event.type == pygame_locals.MOUSEBUTTONUP:
                if(event.button == 1):
                    self.elements_inactive()
                    return ("LMBU", x, y)
                if(event.button == 3):
                    return ("RMBU", x, y)

        return (None, None, None)

    def update(self):
        data_string = self._bgra_surf_to_rgba_string()
        pygame_surface = pygame.image.frombuffer(data_string, (self.width, self.height), 'RGBA')

        self.screen.blit(pygame_surface, (0,0)) 
        pygame.display.flip()