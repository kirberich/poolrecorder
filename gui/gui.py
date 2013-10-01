import pygame
import cairo
import numpy
import scipy
import random
import copy
import math

from color import Color
from base_gui import BaseGUI
from primitives import PrimitiveMixin
from elements import ElementMixin

class Gui(BaseGUI, PrimitiveMixin, ElementMixin):
    def button(self, x, y, width, height, text, fill_color=Color(0.98, 0.98, 0.98), stroke_color=Color(0.8, 0.8, 0.8), bold=False):
        self.draw_rect(x, y, width, height, fill_color=fill_color, stroke_color=stroke_color)
        self.draw_rect(x+1, y+1, width-2, height*0.39, fill_color=Color(1,1,1,0.3))
        font_size = 16
        text_fits = False
        offset = [0, 0]
        while not text_fits:
            self.apply_colors(Color(0.1,0.1,0.1,0.8),Color(0.1,0.1,0.1,0.8))
            self.cairo_context.set_font_size(font_size)
            self.cairo_context.select_font_face('Helvetica', cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL)
            xbearing, ybearing, text_width, text_height, xadvance, yadvance = self.cairo_context.text_extents(text)
            if text_width > width-10 or text_height > height-10:
                font_size -= 1
            else:
                text_fits = True
                offset[0] = (width - text_width) / 2
                offset[1] = (height - text_height) / 2
        self.draw_text(x+offset[0], y+height-offset[1]-2, text, fill_color=Color(0, 0, 0))

        # Return element descriptor
        return lambda event_x, event_y: x < event_x < x+width and y < event_y < y+height

    def recording_button(self, x, y, radius, border_color=Color(0.9,0.8,0.8,1), highlight=False, active=False):
        self.set_color(Color(0,0,0))
        radial = cairo.RadialGradient(x, y, 0, x, y, radius)
        radial.add_color_stop_rgba(0.5, 1, 0, 0, 1)
        if highlight:
            radial.add_color_stop_rgba(0.9, 0.5, 0, 0, 0.8)
            radial.add_color_stop_rgba(0.98, 1, 0.5, 0.5, 0.3)
        else:
            radial.add_color_stop_rgba(0.95, 0.3, 0, 0, 1)
            radial.add_color_stop_rgba(0.98, 0.6, 0.2, 0.2, 0.3)
        radial.add_color_stop_rgba(1, 1, 1, 1, 0)
        #self.cairo_context.set_source(radial)
        self.draw_circle((x, y), radius+2, fill_color=Color(0.7, 0.8, 0.8,0.5), stroke_color=border_color)
        self.draw_circle((x, y), radius, gradient=radial)
        self.draw_rect(x-radius, y-radius, radius*2, (radius), fill_color=Color(1,1,1,0.1))

        radial2 = cairo.RadialGradient(x, y, 0, x, y, radius/2)
        radial2.add_color_stop_rgba(0, 1, 1, 1, 0.9)
        radial2.add_color_stop_rgba(0.1, 1, 1, 1, 0.7)
        radial2.add_color_stop_rgba(0.5, 1, 1, 1, 0.4)
        radial2.add_color_stop_rgba(1, 1, 1, 1, 0)
        self.draw_circle((x, y), radius/2, gradient=radial2)

        if active:
            radial3 = cairo.RadialGradient(x, y, 0, x, y, radius)
            radial3.add_color_stop_rgba(0, 1, 1, 0, 0.5)
            radial3.add_color_stop_rgba(1, 1, 1, 1, 0)
            self.draw_circle((x, y), radius/2, gradient=radial3)
            self.draw_circle((x, y-radius/3), radius*0.66, fill_color=Color(1,1,1,0.15))
        else:
            self.draw_circle((x, y-radius/3), radius*0.66, fill_color=Color(1,1,1,0.25))

        # Return element descriptor
        return lambda event_x, event_y: (event_x - x)**2 + (event_y - y)**2 < radius**2

    def update(self):
        self.fill(Color(1, 1, 1))
        self.redraw_elements()

        super(Gui, self).update()