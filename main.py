import os

os.system("python2 drmt.py switch_egress large_hw drmt_latencies 60 1 11")
os.system("python2 drmt.py switch_egress large_hw drmt_latencies 60 2 11")
os.system("python2 drmt.py switch_egress large_hw drmt_latencies 60 2 12")
os.system("python2 drmt.py switch_egress large_hw drmt_latencies 60 2 13")
os.system("python2 drmt.py switch_egress large_hw drmt_latencies 60 2 14")

os.system("python2 drmt.py switch_ingress large_hw drmt_latencies 60 1 17")
os.system("python2 drmt.py switch_ingress large_hw drmt_latencies 60 2 17")
os.system("python2 drmt.py switch_ingress large_hw drmt_latencies 60 2 18")
os.system("python2 drmt.py switch_ingress large_hw drmt_latencies 60 2 19")
os.system("python2 drmt.py switch_ingress large_hw drmt_latencies 60 2 20")

os.system("python2 drmt.py switch_combined large_hw drmt_latencies 60 1 21")
os.system("python2 drmt.py switch_combined large_hw drmt_latencies 60 2 21")
os.system("python2 drmt.py switch_combined large_hw drmt_latencies 60 2 22")
os.system("python2 drmt.py switch_combined large_hw drmt_latencies 60 2 23")
os.system("python2 drmt.py switch_combined large_hw drmt_latencies 60 2 24")