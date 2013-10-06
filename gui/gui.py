import pygame
import cairo
import numpy
import scipy
import random
import copy
import math

from vector import V

from color import Color, C
from base_gui import BaseGUI
from primitives import PrimitiveMixin
from elements import ElementMixin

class Gui(BaseGUI, PrimitiveMixin, ElementMixin):
    def button(self, x, y, width, height, text, fill_color=Color(0.98, 0.98, 0.98), stroke_color=Color(0.8, 0.8, 0.8), bold=False, element_id=None):
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
        return {
            'descriptor': lambda event_x, event_y: x < event_x < x+width and y < event_y < y+height,
            'bounding_box': ((x,y), (width, height))
        }

    def recording_button(self, x, y, radius, border_color=Color(0.9,0.8,0.8,1), highlight=False, active=False, element_id=None):
        radius -= 2
        if element_id:
            state = self.elements[element_id]['animation_state']
            # offset_highlight_accel = state.get('offset_highlight_accel', V(0,0))
            # offset_highlight_speed = state.get('offset_highlight_speed', V(0, 0))
            # offset_highlight_pos = state.get('offset_highlight_pos', V(0, -radius/3))

            # offset_highlight_accel += ((random.random()-0.5)/10, (random.random()-0.5)/10)
            # offset_highlight_speed += offset_highlight_accel
            # offset_highlight_pos += offset_highlight_speed

            # state['offset_highlight_accel'] = offset_highlight_accel
            # state['offset_highlight_speed'] = offset_highlight_speed
            # state['offset_highlight_pos'] = offset_highlight_pos

            self.elements[element_id]['animation_state'] = state

        # Silly animation test: Calculate mouse angle
        d = V(x,y) - self.mouse_pos
        if d.x:
            alpha = math.atan(d.y/d.x)
        else:
            alpha = math.pi/2
        if d.x > 0:
            alpha += math.pi
        off_x = radius/8*math.cos(alpha)
        off_y = radius/8*math.sin(alpha)

        radial = self.radial_gradient(x, y, r2=radius)
        self.radial_step(.5, C(1, 0, 0))

        #radial.add_color_stop_rgba(0.5, 1, 0, 0, 1)
        if highlight:
            self.radial_step(.9, C(.5, 0, 0, .8))
            self.radial_step(.98, C(1, .5, .5, .3))
        else:
            self.radial_step(.95, C(.3, 0, 0))
            self.radial_step(.98, C(.6, .2, .2, .3))

        self.draw_circle((x, y), radius, gradient=radial)
        self.draw_rect(x-radius, y-radius, radius*2, (radius), fill_color=Color(1,1,1,.1))

        # Grey border
        radial = self.radial_gradient(x, y, radius*0.95, r2=radius+2)
        self.radial_step(.5, C(.7, .8, .8, .5))
        self.radial_step(.7, C(.7, .8, .8))
        self.radial_step(.9, C(.8, .6, .6, .5))
        self.radial_step(.99, C(.8, .6, .6, .2))
        self.draw_circle((x, y), radius+2, gradient=radial)

        # White highlight
        radial = self.radial_gradient(x+off_x, y+off_y, r2=radius/2)
        self.radial_step(0, C(1,1,.6, a=.9))
        self.radial_step(.1, C(1,1,.6, a=.7))
        self.radial_step(.5, C(1,1,.6, a=.4))
        self.draw_circle((x+off_x, y+off_y), radius/2, gradient=radial)

        # Offset highlight
        if active:
            radial = self.radial_gradient(x, y, r2=radius)
            self.radial_step(0, C(1, 1, 0, .5))
            self.draw_circle((x, y), radius/2, gradient=radial)
            self.draw_circle((x, y-radius/3), radius*0.66, fill_color=Color(1,1,1,0.15))
        else:
            self.draw_circle((x, y-radius/3), radius*0.66, fill_color=Color(1,1,1,0.25))

        # Return element descriptor and bounding box
        return {
            'descriptor': lambda event_x, event_y: (event_x - x)**2 + (event_y - y)**2 < radius**2,
            'bounding_box': ((x-radius,y-radius), (radius*2, radius*2))
        }

    def redraw(self):
        self.fill(Color(1, 1, 1))
        self.redraw_elements()

