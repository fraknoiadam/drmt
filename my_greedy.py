import importlib
import math
import random
import sys
from printing import Printing
from randomized_sieve import random_topological_sort_recursive
from schedule_dag import ScheduleDAG
import networkx as nx

class MyGreedySolver:
  def __init__(self, G, input_spec):
    self.G = G.copy()
    self.input_spec = input_spec
  def solve(self):
    result = dict()
    action_time = set()
    match_time = set()
    i = 0
    tmp_nodes = list(self.G.nodes())
    random.shuffle(tmp_nodes)
    next_decided = False
    top_sort = random_topological_sort_recursive(self.G)

    #print(top_sort)
    #ind = self.G.nodes().index("egress_vlan_xlate_ACTION")
    #print(self.G.nodes()[ind])
    #print(self.G.in_degree("egress_vlan_xlate_ACTION"))
    #print(self.G.out_edges("egress_vlan_xlate_ACTION"))
    #print(tmp_nodes)
    rnd_nodes = {node: i for i,node in enumerate(tmp_nodes)}


    while len(self.G.nodes()) > 0:
      matchnodes_zero_indegree = [node for node in self.G.nodes() if self.G.in_degree(node) == 0 and self.G.node[node]['type'] == 'match']
      actionnodes_zero_indegree = [node for node in self.G.nodes() if self.G.in_degree(node) == 0 and self.G.node[node]['type'] == 'action']
      sum_key_width = sum(math.ceil(1.0*self.G.node[matchnodes_zero_indegree[0]]['key_width']/self.input_spec.match_unit_size) for node in matchnodes_zero_indegree)
      sum_num_fields = sum(self.G.node[node]['num_fields'] for node in actionnodes_zero_indegree)

      matchnodes_zero_indegree = sorted(matchnodes_zero_indegree, key=lambda node: (math.ceil(1.0*self.G.node[node]['key_width']/self.input_spec.match_unit_size), rnd_nodes[node]), reverse=True)

      actionnodes_zero_indegree = sorted(actionnodes_zero_indegree, key=lambda node: (self.G.node[node]['num_fields'],rnd_nodes[node]), reverse=True)

      current_match_usage = 0
      current_action_usage = 0

      # Add action nodes with zero width
      # while i%2==1 and len(actionnodes_zero_indegree) > 0 and self.G.node[actionnodes_zero_indegree[-1]]['num_fields'] == 0:
      #   #print(i,"numfields 0")
      #   action_time.add(i)
      #   result[actionnodes_zero_indegree[-1]] = i
      #   print(i,"condition",actionnodes_zero_indegree[0])
      #   self.G.remove_node(actionnodes_zero_indegree[-1])
      #   #actionnodes_zero_indegree.pop(-1)
      #         # Refresh this list
      #   actionnodes_zero_indegree = [node for node in self.G.nodes() if self.G.in_degree(node) == 0 and self.G.node[node]['type'] == 'action']
      #   actionnodes_zero_indegree = sorted(actionnodes_zero_indegree, key=lambda node: (self.G.node[node]['num_fields'],rnd_nodes[node]), reverse=True)



      if next_decided:
        next_decided = False
        M = not M
      elif sum_key_width >= 0.5*self.input_spec.match_unit_size and sum_num_fields >= 0.5*self.input_spec.action_fields_limit:
        M = random.random()*(1.0*sum_key_width/self.input_spec.match_unit_size+1.0*sum_num_fields/self.input_spec.action_fields_limit) < sum_key_width
      if sum_key_width >= 0.5*self.input_spec.match_unit_size and sum_num_fields < 0.5*self.input_spec.action_fields_limit:
        M = True
      elif sum_key_width < 0.5*self.input_spec.match_unit_size and sum_num_fields >= 0.5*self.input_spec.action_fields_limit:
        M = False
      else:
        M = random.random()*(1.0*sum_key_width/self.input_spec.match_unit_size+1.0*sum_num_fields/self.input_spec.action_fields_limit) < sum_key_width
        if sum_key_width>0 and sum_num_fields>0:
          next_decided = True
      # Add match nodes with positive width
      while M and len(matchnodes_zero_indegree) > 0:
        next_matchnode_usage = math.ceil(1.0*self.G.node[matchnodes_zero_indegree[0]]['key_width']/self.input_spec.match_unit_size)
        if current_match_usage + next_matchnode_usage <= self.input_spec.match_unit_limit:
          match_time.add(i)
          result[matchnodes_zero_indegree[0]] = i
          #print(i,"match",next_matchnode_usage,matchnodes_zero_indegree[0],self.G.node[matchnodes_zero_indegree[0]]['key_width'],self.input_spec.match_unit_size, math.ceil(1.0*self.G.node[matchnodes_zero_indegree[0]]['key_width']/self.input_spec.match_unit_size),rnd_nodes[matchnodes_zero_indegree[0]])
          current_match_usage += next_matchnode_usage
          self.G.remove_node(matchnodes_zero_indegree[0])
          matchnodes_zero_indegree.pop(0)
        else:
          break
      
      # Add action nodes with positive width
      while not M and len(actionnodes_zero_indegree) > 0:    
        #print("len",actionnodes_zero_indegree)
        curr_node = actionnodes_zero_indegree.pop(0)
        next_actionnode_usage = self.G.node[curr_node]['num_fields']
        #print(i,"action", current_action_usage + next_actionnode_usage <= self.input_spec.action_fields_limit)
        if current_action_usage + next_actionnode_usage <= self.input_spec.action_fields_limit:
          action_time.add(i)
          result[curr_node] = i
          #print(i,"action",next_actionnode_usage,curr_node)
          current_action_usage += next_actionnode_usage

          if self.G.node[curr_node]['condition']:
            # Condition node
            adjacent_nodes = self.G.successors(curr_node)
            self.G.remove_node(curr_node)
            actionnodes_zero_indegree += [node for node in adjacent_nodes if self.G.in_degree(node) == 0]
          else:
            # Real action node
            self.G.remove_node(curr_node)
        else:
          break
      #if not (current_match_usage == 0 and current_action_usage == 0):
      #print(i, current_match_usage, current_action_usage)

      i += 1
    return len(match_time),len(action_time)


if __name__ == '__main__':
  if (len(sys.argv) not in [4]):
    print("Usage: ", sys.argv[0], " <DAG file> <HW file> <latency file>")
    exit(1)
  input_file   = sys.argv[1]
  hw_file      = sys.argv[2]
  latency_file = sys.argv[3]

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
  best_sol = 100
  timer = Printing(1)
  d = dict()
  for i in range(1000):
    solver = MyGreedySolver(G, input_spec)
    solution = solver.solve()
    if max(solution) < best_sol:
      best_sol = max(solution)
      print(best_sol, timer.get_time(), i)
    if max(solution) not in d:
      d[max(solution)] = 1
    else:
      d[max(solution)] += 1
  print(timer.get_time())
  print(d)