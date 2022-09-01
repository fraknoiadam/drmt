import time

class Printing():
	def __init__(self, status = 0):
		self.counter = 0
		self.time = time.time()
		self.status = status # 0: off, 1: on
	def count(self):
		if self.status == 1:
			self.counter += 1
			print(self.counter, time.time() - self.time)
			self.time = time.time()
	def turn_off(self):
		self.status = 0
	def turn_on(self):
		self.status = 1
	def start(self):
		self.start_time = time.time()
	def stop(self):
		self.result = time.time() - self.start_time