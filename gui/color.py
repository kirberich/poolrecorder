class Color(object):
    def __init__(self, r = 1, g = 1, b = 1, a = 1):
        self.r = r
        self.g = g
        self.b = b
        self.a = a

    def __repr__(self):
        return 'Color object: (%s,%s,%s,%s)' % (self.r, self.g, self.b, self.a)