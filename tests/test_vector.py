# Couple of tests for vector class 
import unittest

from gui.vector import V

class VectorTests(unittest.TestCase):
    def test_point_line_projection(self):
        v1 = V(1, 3)
        v2 = V(7, 5)
        p = V(5, 1)

        self.assertEquals(V.point_line_projection(v1, v2, p), V(4,4))

    def test_intersection(self):
        o1 = V(0,0)
        d1 = V(2, 1)
        o2 = V(10,0)
        d2 = V(-2,1)
        self.assertEquals(V.intersection(o1,d1,o2,d2), V(5, 2.5))
