'''
Solving Traveling Salesman Problem using A* algorithm
## Pritam Kumar Sahoo ##
'''

from collections import defaultdict
import heapq
import sys


def add_new_edge(graph, node1, node2, cost):
	'''
	Adding a new edge to the graph
	Parameters:
		graph : The actual graph :: {'node11' : [(node2, cost2), (node3, cost3), ... ], 'node12' : [ ... ], ...}
		node1 : Source node of the edge
		node2 : Destination node of the edge
		cost  : Cost to travel from node1 to node2
	'''

	graph[node1][node2] = cost
	graph[node2][node1] = cost


def choose_min_key_for_mst(node_dict):
	'''
	Returns the key with minimum value
	Parameters:
		node_dict : The input dictionary
	'''
	ret_key, min_val = None, sys.maxsize

	for node, val in node_dict.items():
		if min_val > val[1]:
			min_val = val[1]
			ret_key = node

	return ret_key if ret_key is not None else list(node_dict.keys())[0]


def find_MST(graph, nodes=None):
	'''
	Find the minimum spanning tree of a given graph, considering only specific nodes
	Parameters:
		graph : The actual graph
		nodes : List of nodes to be considered in the MST, by default All.
	''' 
	MST = list()
	NOT_MST = None
	INFINITY = sys.maxsize

	# Intializing Non MST dictionary :: {node : (source, cost from source to node), ... }
	if nodes is None:
		NOT_MST = { node : (-1, INFINITY) for node in graph.keys()}
	else:
		NOT_MST = { node : (-1, INFINITY) for node in nodes}

	while len(NOT_MST) != 0:
		# Find the key with manimum value
		min_key = choose_min_key_for_mst(NOT_MST)

		# Adding the node to the MST list and removing from Non MST (ret[0] contains the source)
		ret = NOT_MST.pop(min_key)
		MST.append((ret[0], min_key))

		# Updating the source and cost from source of neighbour nodes of the returned key
		for neighbour, val in graph[min_key].items():
			if NOT_MST.get(neighbour, None) is not None:
				NOT_MST[neighbour] = (min_key, val)

	MST.pop(0)
	return MST


def find_optimal_tsp_path(graph):
	'''
	Finds the optimal tour (min-cost tour) given the consition that each node has to visited only once
	Parameters:
		graph : The actual graph
	Returns:
		The optimal path (In form of a list)
	'''
	fringe_list, expanded_list = [], dict()

	# Fringe List stores nodes generated and not yet expanded :: [(f-value, g-value, node, parent node), ... ]
	# Expanded List stored nodes which has been expanded :: {'node': 'parent node along the tree', ... }
	fringe_list.append((0, 0, list(graph.keys())[0], '#'))
	heapq.heapify(fringe_list)

	path_found = False
	while not path_found:
		smallest_f_value = heapq.nsmallest(1, fringe_list)[0]
		g_value, node, p_node = smallest_f_value[1], smallest_f_value[2], smallest_f_value[3]

		heapq.heappop(fringe_list)
		expanded_list[node] = p_node

		parent_nodes, temp_node = [node], node
		while expanded_list[temp_node] != '#':
			parent_nodes.append(expanded_list[temp_node])
			temp_node = expanded_list[temp_node]

		if len(parent_nodes) == len(graph):
			return (parent_nodes[::-1])
		else:
			unvisited_nodes = list(set(graph.keys()).difference(set(parent_nodes)))
			mst_path = find_MST(graph, unvisited_nodes)

			h_value = 0
			for n1, n2 in mst_path:
				h_value = h_value + graph[n1][n2]

			for neighbour, true_val in graph[node].items():
				if expanded_list.get(neighbour, None) is None:
					f_value = h_value + true_val + g_value
					heapq.heappush(fringe_list, (f_value, true_val + g_value, neighbour, node))



if __name__ == '__main__':
	'''
	Main Function
	'''
	graph = defaultdict(dict)
	graph_input = None
	graph_input = [('A', 'B', 20), ('B', 'D', 34), ('C', 'D', 12), ('A', 'C', 42), ('A', 'D', 35), ('B', 'C', 30)]

	# Creating the graph
	if graph_input is not None:
		for n1, n2, c in graph_input:
			add_new_edge(graph, n1, n2, c)

	else:
		print("Enter source, dest, cost (Put a '/' as EOF) : ")
		line = input()
		while line != '/':
			elem = line.split()
			add_new_edge(graph, elem[0], elem[1], int(elem[2]))
			line = input()

	if len(graph) != 0:
		# Solving the TSP Problem
		optimal_tsp = find_optimal_tsp_path(graph)
		print("\nOptimal TSP : \n\n", optimal_tsp, "\n")
	else:
		print("Graph is empty")