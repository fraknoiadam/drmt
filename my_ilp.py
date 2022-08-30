import collections
import itertools
import math
from gurobipy import GRB, Model, max_

from solution import MySolution


class MyILP:
	def __init__(self, dag, input_spec, minute_limit):
		self.G = dag
		self.input_spec = input_spec
		self.minute_limit    = minute_limit

	def solve(self):
		""" Returns the optimal schedule

		Returns
		-------
		time_of_op : dict
				Timeslot for each operation in the DAG
		ops_at_time : defaultdic
				List of operations in each timeslot
		length : int
				Maximum latency of optimal schedule
		"""

		#print ('{:*^80}'.format(' Running my ILP solver '))
		nodes = self.G.nodes()
		match_nodes = self.G.nodes(select='match')
		action_nodes = self.G.nodes(select='action')
		edges = self.G.edges()

		m = Model()
		m.setParam("LogToConsole", 0)

		T = len(nodes)
		t = m.addVars(nodes, lb=0, ub=GRB.INFINITY, vtype=GRB.INTEGER, name="t")
		qr  = m.addVars(list(itertools.product(nodes, range(T))), vtype=GRB.BINARY, name="qr")
		any_match = m.addVars(list(range(T)), vtype=GRB.BINARY, name = "any_match")
		any_action = m.addVars(list(range(T)), vtype=GRB.BINARY, name = "any_action")
		P = m.addVar(lb=0, ub=GRB.INFINITY, vtype=GRB.INTEGER, name="P")
		A = m.addVar(lb=0, ub=GRB.INFINITY, vtype=GRB.INTEGER, name="A")
		M = m.addVar(lb=0, ub=GRB.INFINITY, vtype=GRB.INTEGER, name="M")

		m.setObjective(P, GRB.MINIMIZE)

		m.addConstrs((sum(qr[v, r] for r in range(T)) == 1 for v in nodes),\
					"constr_unique_quotient_remainder")
		m.addConstrs((t[v] == \
						sum(r * qr[v, r] for r in range(T)) \
						for v in nodes), "constr_division")
		m.addConstrs((t[v] - t[u] >= int(self.G.edge[u][v]['delay'] > 0) for (u,v) in edges),\
					"constr_dag_dependencies")
		m.addConstrs((sum(math.ceil((1.0 * self.G.node[v]['key_width']) / self.input_spec.match_unit_size) * qr[v, r]\
						for v in match_nodes)\
						<= self.input_spec.match_unit_limit * any_match[r]\
						for r in range(T)),\
						"constr_match_units")
		m.addConstrs((sum(self.G.node[v]['num_fields'] * qr[v, r]\
						for v in action_nodes)\
						<= self.input_spec.action_fields_limit * any_action[r]\
						for r in range(T)),\
						"constr_action_fields")
		#m.addConstrs((sum(qr[v, r] for v in match_nodes) <= (len(match_nodes) * any_match[r]) \
		#              for r in range(T)),\
		#              "constr_any_match1");
		#m.addConstrs((sum(qr[v, r] for v in action_nodes) <= (len(action_nodes) * any_action[r]) \
		#              for r in range(T)),\
		#              "constr_any_action1");
		m.addConstr(M == sum(any_match[i] for i in range(T)), "M_constraint")
		m.addConstr(A == sum(any_action[i] for i in range(T)), "A_constraint")
		m.addConstr(P == max_(A,M), "P_constraint")

		# Solve model
		m.setParam('TimeLimit', self.minute_limit * 60)
		m.optimize()
		ret = m.Status

		solution = MySolution()
		solution.P = -1
		if (ret == GRB.INFEASIBLE):
			solution.descr = "Infeasible"
			solution.result = False
			return solution
		elif ((ret == GRB.TIME_LIMIT) or (ret == GRB.INTERRUPTED)):
			if (m.SolCount == 0):
				solution.descr = "Hit time limit or interrupted, no solution found yet"
				solution.result = False
				return solution
			else:
				solution.descr = "subopt"
				solution.result = True
				#print ('Hit time limit or interrupted, suboptimal solution found with gap ', m.MIPGap)
		elif (ret == GRB.OPTIMAL):
			solution.descr = "opt"
			solution.result = True
		else:
			print ('Return code is ', ret)
			assert(False)

		# Construct and return schedule
		self.time_of_op = {}
		self.ops_at_time = collections.defaultdict(list)
		for v in nodes:
			for r in range(T):
				if qr[v, r].x > 0:
					pass
					#print(v, r,self.G.node[v],qr[v, r].x)
			self.length = int(P.x) + 1
			assert(self.length == P.x + 1)
		for v in nodes:
			tv = int(t[v].x)
			self.time_of_op[v] = tv
			self.ops_at_time[tv].append(v)

		# Compute periodic schedule to calculate resource usage
		#self.compute_periodic_schedule()

		# Populate solution
		solution.time_of_op = self.time_of_op
		solution.ops_at_time = self.ops_at_time
		solution.length = self.length
		solution.P = int(P.x)
		solution.A = int(A.x)
		solution.M = int(M.x)

		return solution