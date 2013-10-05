import numpy
import scipy
import copy
import random

from base_gui import Event

class ElementMixin(object):
    def __init__(self, *args, **kwargs):
        if not hasattr(self, 'height') or not hasattr(self, 'width') or not hasattr(self, 'event_handlers'):
            raise Exception("ElementMixin requires height and width")

        self.elements = {}
        self.hover_elements = {}
        self.active_elements = {}

        self.event_handlers.append(self.element_handle_event)

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

    def trigger_event_matrix(self, event_matrix, transformation_matrix=None, event_type='click'):
        """ For a binary matrix with white pixels representing event triggers,
            trigger events for every element intersecting white pixels in the matrix.

            if transformation_matrix is passed, event_matrix is transformed before being processed.
        """
        # First set everything in event_matrix to zero that doesn't match an element's bounding box
        mask = numpy.zeros_like(event_matrix)
        for element_id, element in self.elements.items():
            mask = self.update_matrix_from_bounding_box(mask, element, 1)
        event_matrix = mask * event_matrix

        elements_to_check = copy.copy(self.elements)
        to_trigger = []
        while elements_to_check:
            event_points = numpy.transpose(event_matrix.nonzero())
            if not event_points.any():
                break
            y, x = random.choice(event_points)
            for element_id, element in elements_to_check.items():
                if element['descriptor'](x,y):
                    event_matrix = self.update_matrix_from_bounding_box(event_matrix, element, 1)
                    to_trigger.append(element_id)
                    del elements_to_check[element_id]
                    break

        for element_id in to_trigger:
            event = Event(event_type)
            self.element_trigger_event(element_id, event)

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
        if element_id in self.active_elements:
            del self.active_elements[element_id]

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
        self.call_element_method(self.elements[element_id]['callback'])