from drmt import DrmtScheduleSolver
from my_ilp import MyILP
from prmt import PrmtFineSolver
from sieve_rotator import sieve_rotator

import importlib
import sys
import networkx as nx
from schedule_dag import ScheduleDAG
from printing import Printing

if __name__ == '__main__':
	if (len(sys.argv) != 5):
		print("Usage: ", sys.argv[0], " <DAG file> <HW file> <latency file> <time limit in mins>")
		exit(1)
	elif(len(sys.argv) == 5):
		input_file   = sys.argv[1]
		hw_file      = sys.argv[2]
		latency_file = sys.argv[3]
		minute_limit = int(sys.argv[4])
	# Input specification
	input_spec = importlib.import_module(input_file, "*")
	hw_spec    = importlib.import_module(hw_file, "*")
	latency_spec_short=importlib.import_module(latency_file, "*")
	input_spec.action_fields_limit = hw_spec.action_fields_limit
	input_spec.match_unit_limit    = hw_spec.match_unit_limit
	input_spec.match_unit_size     = hw_spec.match_unit_size
	input_spec.action_proc_limit   = hw_spec.action_proc_limit
	input_spec.match_proc_limit    = hw_spec.match_proc_limit

	# Create G
	G = ScheduleDAG()
	#  print(input_spec.nodes, "\n\n", input_spec.edges, "\n\n" , latency_spec)
	nx.DiGraph.nodes(G)
	G.nodes()
	G.create_dag(input_spec.nodes, input_spec.edges, latency_spec_short)
	cpath, cplat = G.critical_path()

#=========================================================
# 	MYILP
#=========================================================
	solver = MyILP(G,input_spec, minute_limit)
	solution_myilp = solver.solve()

	if not solution_myilp.result:
		print(input_file+", MyILP: "+solution_myilp.descr)
	if solution_myilp.P == None:
		P = 20 # TODO
	else:
		P = solution_myilp.P

#=========================================================
# 	PRMT
#=========================================================
	solver = PrmtFineSolver(G, input_spec, latency_spec_short, seed_greedy = True)
	solution_prmt = solver.solve(solve_coarse = False) #What is false?

	prmt_last_good_p = None
	while P > 0:
		prmt_sch = sieve_rotator(solution_prmt.ops_at_time, P, latency_spec_short.dM, latency_spec_short.dA)
		if prmt_sch == None:
			# No solution for this P
			if prmt_last_good_p != None:
				# We have a good solution for a previous P
				break
			else:
				# Currently no good solution for any P
				P += 1
		else:
			prmt_last_good_p = P
			prmt_last_good_solution = prmt_sch
			P -= 1
#=========================================================
# 	DRMT
#=========================================================
	if solution_myilp.P == None:
		P = 20 # TODO
	else:
		P = solution_myilp.P

	while P > 0:
		solver = DrmtScheduleSolver(G, input_spec, latency_spec_short, seed_rnd_sieve = False, period_duration = P, minute_limit = minute_limit, model = 2)
		solution_drmt = solver.solve()
		if solution_drmt.success == True:
			# New solution found
			drmt_last_good_p   = P
			drmt_last_good_solution = solution_drmt
			P -= 1
		else:
			drmt_last_not_good_P = P
			drmt_last_not_good_solution = solution_drmt
			# No solution for this P
			if drmt_last_good_p != None:
				# We have a good solution for a previous P
				break
			else:
				# Currently no good solution for any P
				P += 1


	print(input_file+", MyILP: "+str(solution_myilp.P)+", PRMT: "+ str(prmt_last_good_p)+", DRMT: "+str(drmt_last_good_p))
	print("time, MyILP: "+str(solution_myilp.time)+", PRMT: "+ str(solution_prmt.time)+", DRMT: "+str(drmt_last_good_solution.time))
	print(drmt_last_not_good_P,drmt_last_not_good_solution.time)