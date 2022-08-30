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
	latency_spec=importlib.import_module(latency_file, "*")
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
	G.create_dag(input_spec.nodes, input_spec.edges, latency_spec)
	cpath, cplat = G.critical_path()

	solver = MyILP(G,input_spec, minute_limit)
	solution_myilp = solver.solve()

	if not solution_myilp.result:
		print(input_file+", MyILP: "+solution_myilp.descr)
	P = 20 # TODO

	solver = PrmtFineSolver(G, input_spec, latency_spec, seed_greedy = True)
	solution_prmt = solver.solve(solve_coarse = False) #What is false?

	found_solution = False
	prmt_min_P = P
	while P > 0:
		prmt_sch = sieve_rotator(solution_prmt.ops_at_time, P, latency_spec.dM, latency_spec.dA)
		if prmt_sch == None:
			# No solution for this P
			if found_solution:
				break
			else:
				prmt_min_P = P
				P += 1
		else:
			found_solution = True
			prmt_min_P = P
			P -= 1

	print(input_file+", MyILP: "+str(solution_myilp.P)+", PRMT: "+ str(prmt_min_P))