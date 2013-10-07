import numpy
import scipy
import copy
import random

from base_gui import Event
from color import Color

TOUCH_FRAMES = 5

class ElementMixin(object):
    def __init__(self, *args, **kwargs):
        if not hasattr(self, 'height') or not hasattr(self, 'width') or not hasattr(self, 'event_handlers'):
            raise Exception("ElementMixin requires height and width")

        self.elements = {}
        self.hover_elements = {}
        self.touch_elements = {}
        self.active_elements = {}
        self.triggered_elements = {}
        self.elements_triggered_through_matrix = set([])

        self.event_handlers.append(self.element_handle_event)

        self.last_event_matrix = None
        self.calibration_matrix = None

        super(ElementMixin, self).__init__(*args, **kwargs)

    def element_handle_event(self, event):
        for element_id, element in self.elements.items():
            if not callable(element['descriptor']): 
                continue
            if element['descriptor'](event.x, event.y):
                self.element_trigger_event(element_id, event)
            else:
                self.element_base(element_id)

    def element_trigger_event(self, element_id, event):
        if event.event_type == 'mouse_move':
            self.element_hover(element_id)
        elif event.event_type == 'touch':
            self.element_touch(element_id)
        elif event.event_type == 'mouse_down':
            self.element_active(element_id)
        elif event.event_type in ['mouse_up', 'click']:
            self.element_trigger_active_callback(element_id)
            self.element_base(element_id)

    def update_matrix_from_bounding_box(self, matrix, element, value):
        """ Sets point in matrix inside element['bounding_box'] to value """
        box = element['bounding_box']
        x1 = box[0][0]
        y1 = box[0][1]
        x2 = box[0][0] + box[1][0]
        y2 = box[0][1] + box[1][1]
        matrix[y1:y2, x1:x2] = value
        return matrix

    def trigger_event_matrix(self, event_matrix, event_type='click'):
        """ For a binary matrix with white pixels representing event triggers,
            trigger events for every element intersecting white pixels in the matrix.

            if transformation_matrix is passed, event_matrix is transformed before being processed.
        """
        # Transform event_matrix
        if self.calibration_matrix is not None:
            event_matrix_transformed = numpy.zeros((self.height, self.width))
            raw_points = numpy.transpose(event_matrix.nonzero())
            for point in raw_points:
                transformed = self.calibration_matrix[point[0]][point[1]]
                event_matrix_transformed[transformed.y][transformed.x] = 1
        event_matrix = event_matrix_transformed

        # First set everything in event_matrix to zero that doesn't match an element's bounding box
        mask = numpy.zeros_like(event_matrix)
        for element_id, element in self.elements.items():
            mask = self.update_matrix_from_bounding_box(mask, element, 1)
        if self.last_event_matrix is not None:
            mask = mask * self.last_event_matrix
        self.last_event_matrix = event_matrix
        
        event_matrix = mask * event_matrix


        elements_to_check = copy.copy(self.elements)
        to_trigger = []
        while elements_to_check:
            event_points = numpy.transpose(event_matrix.nonzero())
            if not event_points.any():
                break
            y, x = random.choice(event_points)
            # if self.calibration_matrix is not None:
            #    transformed = self.calibration_matrix[raw_y][raw_x] 
            #    x, y = transformed.x, transformed.y
            #    #self.draw_circle((x, y), 3, stroke_color = Color(1,0,0))
            #    #self.draw_circle((raw_x, raw_y), 3, stroke_color = Color(1,1,0))
            # else:
            #    x, y = raw_x, raw_y
            #   return # DEBUGGING, don't do anything if not calibrated
            for element_id, element in elements_to_check.items():
                if element['descriptor'](x,y):
                    #print "triggering event, orig coordinates: %s, %s, transformed: %s, %s" % (raw_x, raw_y, x, y)
                    event_matrix = self.update_matrix_from_bounding_box(event_matrix, element, 0)
                    to_trigger.append(element_id)
                    del elements_to_check[element_id]
                    break
            else:
                event_matrix[y][x] = 0

        for element_id in to_trigger:
            event = Event(event_type)
            self.element_trigger_event(element_id, event)
            self.elements_triggered_through_matrix.add(element_id)

        triggered_before = list(self.elements_triggered_through_matrix)
        for element_id in triggered_before:
            if element_id not in to_trigger:
                self.element_base(element_id)
                self.elements_triggered_through_matrix.remove(element_id)

    def add_element(self, element_id, base_state, hover_state=None, active_state=None, callback=None):
        """ Adds an interface element to the gui
            id: 
                Identifier for this element, needs to be a unique integer
            base_state, hover_state, active_state:
                drawing callables for the element's states
            callback:
                Function to call if this element has been triggered
        """

        # Register element 
        self.elements[element_id] = {
            'base_state': base_state,
            'hover_state': hover_state,
            'active_state': active_state,
            'callback': callback, 
            'animation_state': {}
        }

        # Draw element and get its descriptor
        element = self.call_element_method(base_state, element_id)
        self.elements[element_id]['descriptor'] = element['descriptor']
        self.elements[element_id]['bounding_box'] = element['bounding_box']

    def redraw_elements(self):
        for element_id in self.elements:
            if element_id in self.active_elements:
                self.element_active(element_id, update=False, force=True)
            elif element_id in self.hover_elements:
                self.element_hover(element_id, update=False, force=True)
            else:
                self.element_base(element_id, update=False)
        #self.update()

    def call_element_method(self, method, element_id=None):
        if not method:
            print "no method"
            return
        if callable(method):
            if element_id:
                return method(element_id=element_id)
            return method()
        else:
            method, args, kwargs = method
            if element_id:
                kwargs['element_id'] = element_id
            return method(*args, **kwargs)

    def element_base(self, element_id, update=True):
        """ Set and draw the base state of an element 
            Also returns the element_descriptor necessary to detect interaction with this element
        """
        if element_id in self.hover_elements:
            del self.hover_elements[element_id]
        if element_id in self.touch_elements:
            del self.touch_elements[element_id]
        if element_id in self.active_elements:
            del self.active_elements[element_id]
        if element_id in self.triggered_elements:
            del self.triggered_elements[element_id]

        element_descriptor = self.call_element_method(self.elements[element_id]['base_state'], element_id)

        if update:
            self.update()

        return element_descriptor

    def element_hover(self, element_id, update=True, force=False):
        if not force and (element_id in self.hover_elements or element_id in self.active_elements):
            return

        if element_id in self.active_elements:
            del self.active_elements[element_id]

        self.hover_elements[element_id] = self.elements[element_id]
        self.call_element_method(self.hover_elements[element_id]['hover_state'], element_id)
        if update:
            self.update()

    def element_touch(self, element_id, update=True, force=False):
        if not force and element_id in self.triggered_elements:
            return
        if not element_id in self.touch_elements:
            self.touch_elements[element_id] = 1
        else:
            self.touch_elements[element_id] += 1

        if self.touch_elements[element_id] > TOUCH_FRAMES:
            del self.touch_elements[element_id]
            self.element_active(element_id)
            self.element_trigger_active_callback(element_id)
        else:
            self.element_hover(element_id)

    def element_active(self, element_id, update=True, force=False):
        if not force and element_id in self.active_elements:
            return

        self.active_elements[element_id] = self.elements[element_id]
        self.call_element_method(self.active_elements[element_id]['active_state'], element_id)
        if update:
            self.update()

    def elements_reset(self):
        update = False
        for element_id in copy.copy(self.hover_elements):
            self.element_base(element_id, update=False)
            update=True

        if update: 
            self.update()

    def elements_inactive(self):
        for element_id in copy.copy(self.active_elements):
            if element_id in self.hover_elements:
                self.element_hover(element_id, update=False, force=True)
            else:
                self.element_base(element_id, update=False)
        self.update()

    def element_trigger_active_callback(self, element_id):
        self.triggered_elements[element_id] = element_id
        self.call_element_method(self.elements[element_id]['callback'])
