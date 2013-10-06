import unittest
import numpy

from gui.vector import V 
import calibration 

class RecorderTests(unittest.TestCase):
	def test_calibration_transformation_matrix(self):
		test_matrix = numpy.zeros((200, 200))
		corners = {
			'top_left': V(0, 0),
			'top_right': V(199, 0),
			'bottom_left': V(0, 199),
			'bottom_right': V(199, 199)
		}
		trans = calibration.calibration_transformation_matrix(200, 200, corners)
		self.assertEquals(trans[90][90], V(90, 90))
		self.assertEquals(trans[0][0], V(0, 0))
		self.assertEquals(trans[199][199], V(199, 199))

		test_matrix = numpy.zeros((200, 200))
		corners = {
			'top_left': V(100, 0),
			'top_right': V(199, 0),
			'bottom_left': V(100, 199),
			'bottom_right': V(199, 199)
		}
		trans = calibration.calibration_transformation_matrix(200, 200, corners)
		self.assertEquals(trans[100][100], V(0, 100))
		self.assertEquals(trans[1][1], V(-199, 1))
		self.assertEquals(trans[199][199], V(199, 199))