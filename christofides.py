import networkx as nx
import numpy as np
from itertools import combinations


def create_graph(sub_matrix):
    G = nx.Graph()
    for i in sub_matrix.index:
        for j in sub_matrix.columns:
            if i != j:
                G.add_edge(i, j, weight=sub_matrix.loc[i, j])
    return G


def solve_tsp_christofides(sub_matrix):
    G = create_graph(sub_matrix)
    # Create a minimum spanning tree
    MSTree = nx.minimum_spanning_tree(G)

    # Find vertices with odd degree in MST
    odd_degree_nodes = [v for v, d in MSTree.degree() if d % 2 != 0]

    # Create a subgraph with only the odd degree nodes
    odd_node_subgraph = G.subgraph(odd_degree_nodes)

    # Find minimum weight perfect matching on the subgraph
    odd_matching = nx.algorithms.matching.min_weight_matching(odd_node_subgraph, weight='weight')

    # Combine the edges of MST and the matching
    multigraph = nx.MultiGraph(MSTree)
    multigraph.add_edges_from(odd_matching)

    # Ensure multigraph is Eulerian
    if not nx.is_eulerian(multigraph):
        raise nx.NetworkXError("Multigraph is not Eulerian, algorithm cannot proceed.")

    # Find an Eulerian tour
    eulerian_tour = list(nx.eulerian_circuit(multigraph))

    # Convert the Eulerian tour to a Hamiltonian circuit
    # Make sure all nodes are included at least once
    hamiltonian_circuit = []
    visited = set()
    for u, v in eulerian_tour:
        if u not in visited:
            hamiltonian_circuit.append(u)
            visited.add(u)
        if v not in visited:
            hamiltonian_circuit.append(v)
            visited.add(v)

    # Ensure that the starting node is the same as the ending node
    if hamiltonian_circuit[0] != hamiltonian_circuit[-1]:
        hamiltonian_circuit.append(hamiltonian_circuit[0])

    return hamiltonian_circuit

