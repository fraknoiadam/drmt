from time import time


class Printing():
	def __init__(self):
		self.counter = 0
		self.time = time.time()
	def count(self): 
		self.counter += 1
		print(self.counter, time.time() - self.time)
		self.time = time.time()
