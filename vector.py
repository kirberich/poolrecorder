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

	def abs(self):
		return math.sqrt(self.x*self.x + self.y*self.y)

	def consume_tuple(self, other):
		if isinstance(other, tuple) or isinstance(other, list):
			return V(other[0], other[1])
		return other

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
		try:
			return V(other * self.x, other * self.y)
		except:
			import pdb
			pdb.set_trace()

	def __div__(self, other):
		if not other: 
			raise Exception("Division by zero")
		other = float(other)
		return V(self.x/other, self.y/other)