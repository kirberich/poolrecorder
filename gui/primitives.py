import math 

from color import Color

class PrimitiveMixin(object):
    def __init__(self, *args, **kwargs):
        if not hasattr(self, 'cairo_surface') or not hasattr(self, 'cairo_context'):
            raise Exception("PrimitiveMixin needs cairo_surface and cairo_context")

        super(PrimitiveMixin, self).__init__(*args, **kwargs)

    def draw_circle(self, center, radius, fill_color = None, stroke_color = None, gradient=None):
        """ Draw a circle at center, with a given radius and optional fill_color and stroke_color """
        (x, y) = center
        self.cairo_context.arc(x, y, radius, 0, 2 * math.pi)
        if gradient:
            self.cairo_context.set_source(gradient)
            self.cairo_context.paint()
        self.apply_colors(fill_color, stroke_color)

        self.cairo_context.close_path()

    def draw_rect(self, x, y, width, height, fill_color = None, stroke_color = None):
        """ Draw a rectangle with its upper left corner at x,y, size of width,height and optional fill_color and stroke_color 
            Implementation is a wee bit silly right now, because I don't understand how cairo uses strokes
        """
        if stroke_color:
            self.cairo_context.rectangle(x, y, width, height)
            self.apply_colors(stroke_color)
            self.cairo_context.close_path()
            x += 1
            y += 1
            width -= 2
            height -=2 
            self.cairo_context.rectangle(x, y, width, height)
            self.apply_colors(Color(1,1,1))
            self.cairo_context.close_path()
        if fill_color:
            self.cairo_context.rectangle(x, y, width, height)
            self.apply_colors(fill_color)
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

    def draw_text(self, x, y, text, fill_color = None, stroke_color = None, font_size=None):
        if font_size:
            self.cairo_context.set_font_size(font_size)
        self.cairo_context.move_to(x,y)
        self.cairo_context.show_text(text)
        self.cairo_context.new_path()
        #self.apply_colors(fill_color, stroke_color)

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

    def apply_colors(self, fill_color=None, stroke_color=None):
        """ Apply fill and stroke colors to the current path """
        if fill_color:
            self.set_color(fill_color)
            self.cairo_context.fill_preserve()
        if stroke_color:
            self.set_color(stroke_color)
            self.cairo_context.stroke()

        self.cairo_context.new_path()
