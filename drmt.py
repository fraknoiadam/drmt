from gurobipy import *
import networkx as nx
import numpy as np
import collections
import importlib
import math
from schedule_dag import ScheduleDAG
from printers import *
from solution import Solution
from randomized_sieve import *
from sieve_rotator import *
from prmt import PrmtFineSolver
import time
import sys

RND_SIEVE_TIME = 30

class DrmtScheduleSolver:
    def __init__(self, dag, input_spec, latency_spec, seed_rnd_sieve, period_duration, minute_limit, model):
        self.G = dag
        self.input_spec = input_spec
        self.latency_spec = latency_spec
        self.seed_rnd_sieve = seed_rnd_sieve
        self.period_duration = period_duration
        self.minute_limit    = minute_limit
        self.model = model

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
        init_drmt_schedule = None
        if (self.seed_rnd_sieve):
          print ('{:*^80}'.format(' Running rnd sieve '))
          rnd_sch = rnd_sieve(self.input_spec, self.G, RND_SIEVE_TIME, self.period_duration)

          print ('{:*^80}'.format(' Running PRMT + rotator '))
          psolver = PrmtFineSolver(self.G, self.input_spec, self.latency_spec, seed_greedy=True)
          solution = psolver.solve(solve_coarse = False)
          prmt_sch = sieve_rotator(solution.ops_at_time, self.period_duration, self.latency_spec.dM, self.latency_spec.dA)

          if ((rnd_sch == None) and (prmt_sch == None)):
            print ("Both heuristics returned nothing")
            init_drmt_schedule = None
          elif ((rnd_sch == None)):
            print ("Picking output from PRMT")
            print ("Latency for PRMT ", max(prmt_sch.values()))
            init_drmt_schedule = prmt_sch
          elif ((prmt_sch == None)):
            print ("Picking output from RND sieve")
            print ("Latency for RND sieve: ", max(rnd_sch.values()))
            init_drmt_schedule = rnd_sch
          else:
            print ("Latencies, PRMT: ", max(prmt_sch.values()), " RND sieve: ", max(rnd_sch.values()))
            if (max(prmt_sch.values()) < max(rnd_sch.values())):
              print ("Picking output from PRMT")
              init_drmt_schedule = prmt_sch
            else:
              print ("Picking output from RND sieve")
              init_drmt_schedule = rnd_sch

        if (init_drmt_schedule):
          Q_MAX = int(math.ceil((1.0 * (max(init_drmt_schedule.values()) + 1)) / self.period_duration))
        else:
          # Set Q_MAX based on critical path
          cpath, cplat = self.G.critical_path()
          Q_MAX = int(math.ceil(1.5 * cplat / self.period_duration))

        print ('{:*^80}'.format(' Running DRMT ILP solver '))
        T = self.period_duration
        nodes = self.G.nodes()
        match_nodes = self.G.nodes(select='match')
        action_nodes = self.G.nodes(select='action')
        edges = self.G.edges()
        print(Q_MAX,T,len(nodes))

        m = Model()
        m.setParam("LogToConsole", 1)
        class Printing():
            def __init__(self):
                self.counter = 0
                self.time = time.time()
            def count(self): 
                self.counter += 1
                print(self.counter, time.time() - self.time)
                self.time = time.time()

        qwe = Printing()
        qwe = qwe.count

        if self.model == 1:
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

        elif self.model == 2:
          # Create variables
          # t is the start time for each DAG node in the first scheduling period
          t = m.addVars(nodes, lb=0, ub=GRB.INFINITY, vtype=GRB.INTEGER, name="t")
          qwe()
          # The quotients and remainders when dividing by T (see below)
          # qr[v, q, r] is 1 when t[v]
          # leaves a quotient of q and a remainder of r, when divided by T.
          qr  = m.addVars(list(itertools.product(nodes, range(Q_MAX), range(T))), vtype=GRB.BINARY, name="qr")
          qwe()

          # Is there any match/action from packet q in time slot r?
          # This is required to enforce limits on the number of packets that
          # can be performing matches or actions concurrently on any processor.
          any_match = m.addVars(list(itertools.product(range(Q_MAX), range(T))), vtype=GRB.BINARY, name = "any_match")
          qwe()
          any_action = m.addVars(list(itertools.product(range(Q_MAX), range(T))), vtype=GRB.BINARY, name = "any_action")
          qwe()

          # The length of the schedule
          length = m.addVar(lb=0, ub=GRB.INFINITY, vtype=GRB.INTEGER, name="length")

          # Set objective: minimize length of schedule
          m.setObjective(length, GRB.MINIMIZE)

          # Set constraints

          # The length is the maximum of all t's
          m.addConstrs((t[v]  <= length for v in nodes), "constr_length_is_max")

          # Given v, qr[v, q, r] is 1 for exactly one q, r, i.e., there's a unique quotient and remainder
          m.addConstrs((sum(qr[v, q, r] for q in range(Q_MAX) for r in range(T)) == 1 for v in nodes),\
                      "constr_unique_quotient_remainder")
          qwe()

          # This is just a way to write dividend = quotient * divisor + remainder
          m.addConstrs((t[v] == \
                        sum(q * qr[v, q, r] for q in range(Q_MAX) for r in range(T)) * T + \
                        sum(r * qr[v, q, r] for q in range(Q_MAX) for r in range(T)) \
                        for v in nodes), "constr_division")
          qwe()

          # Respect dependencies in DAG
          m.addConstrs((t[v] - t[u] >= self.G.edge[u][v]['delay'] for (u,v) in edges),\
                      "constr_dag_dependencies")
          qwe()

          # Number of match units does not exceed match_unit_limit
          # for every time step (j) < T, check the total match unit requirements
          # across all nodes (v) that can be "rotated" into this time slot.
          m.addConstrs((sum(math.ceil((1.0 * self.G.node[v]['key_width']) / self.input_spec.match_unit_size) * qr[v, q, r]\
                        for v in match_nodes for q in range(Q_MAX))\
                        <= self.input_spec.match_unit_limit for r in range(T)),\
                        "constr_match_units")
          qwe()

          # The action field resource constraint (similar comments to above)
          m.addConstrs((sum(self.G.node[v]['num_fields'] * qr[v, q, r]\
                        for v in action_nodes for q in range(Q_MAX))\
                        <= self.input_spec.action_fields_limit for r in range(T)),\
                        "constr_action_fields")
          qwe()

          # Any time slot (r) can have match or action operations
          # from only match_proc_limit/action_proc_limit packets
          # We do this in two steps.

          # First, detect if there is any (at least one) match/action operation from packet q in time slot r
          # if qr[v, q, r] = 1 for any match node, then any_match[q,r] must = 1 (same for actions)
          # Notice that any_match[q, r] may be 1 even if all qr[v, q, r] are zero
          m.addConstrs((sum(qr[v, q, r] for v in match_nodes) <= (len(match_nodes) * any_match[q, r]) \
                        for q in range(Q_MAX)\
                        for r in range(T)),\
                        "constr_any_match1");
          qwe()

          m.addConstrs((sum(qr[v, q, r] for v in action_nodes) <= (len(action_nodes) * any_action[q, r]) \
                        for q in range(Q_MAX)\
                        for r in range(T)),\
                        "constr_any_action1");
          qwe()

          # Second, check that, for any r, the summation over q of any_match[q, r] is under proc_limits
          m.addConstrs((sum(any_match[q, r] for q in range(Q_MAX)) <= self.input_spec.match_proc_limit\
                        for r in range(T)), "constr_match_proc")
          qwe()
          m.addConstrs((sum(any_action[q, r] for q in range(Q_MAX)) <= self.input_spec.action_proc_limit\
                        for r in range(T)), "constr_action_proc")
          qwe()

          print(init_drmt_schedule)
          # Seed initial values
          if init_drmt_schedule:
            for i in nodes:
              pass
              t[i].start = init_drmt_schedule[i]

        # Solve model
        m.setParam('TimeLimit', self.minute_limit * 60)
        qwe()
        m.optimize()
        qwe()
        ret = m.Status

        if (ret == GRB.INFEASIBLE):
          print ('Infeasible')
          return None
        elif ((ret == GRB.TIME_LIMIT) or (ret == GRB.INTERRUPTED)):
          if (m.SolCount == 0):
            print ('Hit time limit or interrupted, no solution found yet')
            return None
          else:
            print ('Hit time limit or interrupted, suboptimal solution found with gap ', m.MIPGap)
        elif (ret == GRB.OPTIMAL):
          print ('Optimal solution found with gap ', m.MIPGap)
        else:
          print ('Return code is ', ret)
          assert(False)

        # Construct and return schedule
        self.time_of_op = {}
        self.ops_at_time = collections.defaultdict(list)
        if self.model == 1:
          print(P,A,M)
          for v in nodes:
            for r in range(T):
              if qr[v, r].x > 0:
                print(v, r,self.G.node[v],qr[v, r].x)
          self.length = int(P.x + 1)
          assert(self.length == P.x + 1)
        else:
          self.length = int(length.x + 1)
          assert(self.length == length.x + 1)
        for v in nodes:
            tv = int(t[v].x)
            self.time_of_op[v] = tv
            self.ops_at_time[tv].append(v)

        # Compute periodic schedule to calculate resource usage
        self.compute_periodic_schedule()

        # Populate solution
        solution = Solution()
        solution.time_of_op = self.time_of_op
        solution.ops_at_time = self.ops_at_time
        solution.ops_on_ring = self.ops_on_ring
        solution.length = self.length
        solution.match_key_usage     = self.match_key_usage
        solution.action_fields_usage = self.action_fields_usage
        solution.match_units_usage   = self.match_units_usage
        solution.match_proc_usage    = self.match_proc_usage
        solution.action_proc_usage   = self.action_proc_usage
        return solution

    def compute_periodic_schedule(self):
        T = self.period_duration
        self.ops_on_ring = collections.defaultdict(list)
        self.match_key_usage = dict()
        self.action_fields_usage = dict()
        self.match_units_usage = dict()
        self.match_proc_set = dict()
        self.match_proc_usage = dict()
        self.action_proc_set = dict()
        self.action_proc_usage = dict()
        for t in range(T):
          self.match_key_usage[t]     = 0
          self.action_fields_usage[t] = 0
          self.match_units_usage[t]   = 0
          self.match_proc_set[t]      = set()
          self.match_proc_usage[t]    = 0
          self.action_proc_set[t]     = set()
          self.action_proc_usage[t]   = 0

        for v in self.G.nodes():
            k = self.time_of_op[v] / T
            r = self.time_of_op[v] % T
            self.ops_on_ring[r].append('p[%d].%s' % (k,v))
            if self.G.node[v]['type'] == 'match':
                self.match_key_usage[r] += self.G.node[v]['key_width']
                self.match_units_usage[r] += math.ceil((1.0 * self.G.node[v]['key_width'])/ self.input_spec.match_unit_size)
                self.match_proc_set[r].add(k)
                self.match_proc_usage[r] = len(self.match_proc_set[r])
            else:
                self.action_fields_usage[r] += self.G.node[v]['num_fields']
                self.action_proc_set[r].add(k)
                self.action_proc_usage[r] = len(self.action_proc_set[r])

if __name__ == "__main__":
  # Cmd line args
  if (len(sys.argv) != 7):
    print ("Usage: ", sys.argv[0], " <DAG file> <HW file> <latency file> <time limit in mins>")
    exit(1)
  elif (len(sys.argv) == 7):
    input_file   = sys.argv[1]
    hw_file      = sys.argv[2]
    latency_file = sys.argv[3]
    minute_limit = int(sys.argv[4])
    model = int(sys.argv[5])
    P = int(sys.argv[6])
  with open('results/'+input_file+'_'+latency_file+'_'+str(model)+'_'+str(P)+'.txt', 'w') as f:
    print(input_file, hw_file, latency_file, minute_limit, model, P)
    original_stdout = sys.stdout
    sys.stdout = f

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

    print ('{:*^80}'.format(' Input DAG '))
    tpt_upper_bound = print_problem(G, input_spec)
    tpt_lower_bound = 0.0067/2 # Just for kicks
    print ('\n\n')

    # Try to max. throughput
    # We do this by min. the period
    period_lower_bound = P#int(math.ceil((1.0) / tpt_upper_bound))
    period_upper_bound = P#int(math.ceil((1.0) / tpt_lower_bound))
    period = period_upper_bound
    last_good_solution = None
    last_good_period   = None
    print ('Searching between limits ', period_lower_bound, ' and ', period_upper_bound, ' cycles')
    low = period_lower_bound
    high = period_upper_bound
    while (low <= high):
      assert(low > 0)
      assert(high > 0)
      period = int(math.ceil((low + high)/2.0))
      print('\n')
      print ('period =', period, ' cycles')
      print ('{:*^80}'.format(' Scheduling DRMT '))
      solver = DrmtScheduleSolver(G, input_spec, latency_spec,\
                                  seed_rnd_sieve = True, period_duration = period, minute_limit = minute_limit, model = model)
      solution = solver.solve()
      if (solution):
        last_good_period   = period
        last_good_solution = solution
        high = period - 1
      else:
        low  = period + 1

    if (last_good_solution == None):
      print ("Best throughput so far is below ", tpt_lower_bound, " packets/cycle.")
      exit(1)

    print ('\nBest achieved throughput = 1 packet every %d cycles' % (last_good_period))
    print ('Schedule length (thread count) = %d cycles' % last_good_solution.length)
    print ('Critical path length = %d cycles' % cplat)

    print ('\n\n')

    print ('{:*^80}'.format(' First scheduling period on one processor'))
    print (timeline_str(last_good_solution.ops_at_time, white_space=0, timeslots_per_row=4),'\n\n')

    print ('{:*^80}'.format(' Steady state on one processor'))
    print ('{:*^80}'.format('p[u] is packet from u scheduling periods ago'))
    print (timeline_str(last_good_solution.ops_on_ring, white_space=0, timeslots_per_row=4), '\n\n')

    print_resource_usage(input_spec, last_good_solution)
