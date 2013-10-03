# Super simple vector class 
import math

class V(object):
	def __init__(self, x=0, y=0):
		self.x = float(x)
		self.y = float(y)

	def __unicode__(self):
		return "(%s, %s)" % (self.x, self.y)
	__repr__ = __unicode__

	@classmethod
	def from_tuple(cls, (x,y)):
		return V(x,y)

	@classmethod
	def intersection(cls, o1, d1, o2, d2):
		""" Find intersection of two vectors, if any """
		# o1 + l1 * d1 = o2 + l2 * d2
		# l1 * d1 - l2 * d2 = o2 - o1
		# (l1 * d1.x, l1 * d1.y) - (l2 * d2.x, l2 * d2.y) = o2 - o1

		# l1 * d1.x - l2 * d2.x = o2.x - o1.x
		# l1 * d1.x = o2.x - o1.x + l2 * d2.x
		# l1 = (o2.x - o1.x + l2 * d2.x) / d1.x

		# l1 * d1.y - l2 * d2.y = o2.y - o1.y
		# l2 * d2.y = l1 * d1.y -o 2.y + o1.y

		# l2 * d2.y 	= ((o2.x - o1.x + l2 * d2.x) / d1.x) * d1.y - o2.y + o1.y
		# 			= (o2.y - o1.x)*d1.y/d1.x + (l2 * d2.x)*d1.y/d1.x - o2.y + o1.y
		# l2 * d2.y - (l2 * d2.x)*d1.y/d1.x = (o2.y - o1.x)*d1.y/d1.x - o2.y + o1.y
		# l2 * d2.y - l2*d2.x*d1.y/d1.x 
		# l2 * (d2.y - d2.x*d1.y/d1.x) = (o2.y - o1.x)*d1.y/d1.x - o2.y + o1.y
		
		try:
			l2 = ((o2.x - o1.x)*d1.y/d1.x - o2.y + o1.y) / (d2.y - d2.x*d1.y/d1.x)
			return o2 + d2*l2
		except ZeroDivisionError:
			return None

	def abs(self):
		return math.sqrt(self.x*self.x + self.y*self.y)

	def consume_tuple(self, other):
		if isinstance(other, tuple) or isinstance(other, list):
			return V(other[0], other[1])
		return other

	def cross(self, other):
		""" cross product """
		return V(self.x*other.y - other.x*self.y)

	def __cmp__(self, other):
		other = self.consume_tuple(other)
		if self.x == other.x and self.y == other.y: return 0
		if self.abs < other.abs: return -1
		return 1

	def __nonzero__(self):
		if self.x or self.y:
			return True
		return False

	def __neg__(self):
		return V(-self.x, -self.y)

	def __add__(self, other):
		other = self.consume_tuple(other)
		return V(self.x + other.x, self.y + other.y)

	def __sub__(self, other):
		other = self.consume_tuple(other)
		return V(self.x - other.x, self.y - other.y)

	def __mul__(self, other):
		other = self.consume_tuple(other)
		if isinstance(other, V):
			return (self.x * other.x + self.y * other.y)
		return V(other * self.x, other * self.y)

	def __div__(self, other):
		if not other: 
			raise Exception("Division by zero")
		other = float(other)
		return V(self.x/other, self.y/other)