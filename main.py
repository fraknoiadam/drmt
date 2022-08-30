import os

#os.system("python2 compare_ilps.py +28 large_hw drmt_latencies 1")
for i in range(30):
  os.system("python2 compare_ilps.py +"+str(i)+" large_hw drmt_latencies 5")

#os.system("python2 compare_ilps.py proba2 large_hw drmt_latencies 5")
