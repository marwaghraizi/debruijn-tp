#!/bin/env python3
# -*- coding: utf-8 -*-
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#    A copy of the GNU General Public License is available at
#    http://www.gnu.org/licenses/gpl-3.0.html

"""Perform assembly based on debruijn graph."""

import argparse
import os
import sys
import networkx as nx
import matplotlib
from operator import itemgetter
import random
random.seed(9001)
from random import randint
import statistics
import textwrap
import matplotlib.pyplot as plt
matplotlib.use("Agg")

__author__ = "Marwa GHRAIZI"
__copyright__ = "Universite Paris Diderot"
__credits__ = ["Marwa GHRAIZI"]
__license__ = "GPL"
__version__ = "1.0.0"
__maintainer__ = "Marwa GHRAIZI"
__email__ = "marwaghraizi@gmail.com"
__status__ = "Developpement"

def isfile(path): # pragma: no cover
    """Check if path is an existing file.

    :param path: (str) Path to the file
    
    :raises ArgumentTypeError: If file doesn't exist
    
    :return: (str) Path 
    """
    if not os.path.isfile(path):
        if os.path.isdir(path):
            msg = "{0} is a directory".format(path)
        else:
            msg = "{0} does not exist.".format(path)
        raise argparse.ArgumentTypeError(msg)
    return path


def get_arguments(): # pragma: no cover
    """Retrieves the arguments of the program.

    :return: An object that contains the arguments
    """
    # Parsing arguments
    parser = argparse.ArgumentParser(description=__doc__, usage=
                                     "{0} -h"
                                     .format(sys.argv[0]))
    parser.add_argument('-i', dest='fastq_file', type=isfile,
                        required=True, help="Fastq file")
    parser.add_argument('-k', dest='kmer_size', type=int,
                        default=22, help="k-mer size (default 22)")
    parser.add_argument('-o', dest='output_file', type=str,
                        default=os.curdir + os.sep + "contigs.fasta",
                        help="Output contigs in fasta file (default contigs.fasta)")
    parser.add_argument('-f', dest='graphimg_file', type=str,
                        help="Save graph as an image (png)")
    return parser.parse_args()


def read_fastq(fastq_file):
    """Extract reads from fastq files.

    :param fastq_file: (str) Path to the fastq file.
    :return: A generator object that iterate the read sequences. 
    """
    with open(fastq_file, "r") as filin:
    	for line in filin:
            yield next(filin).strip()
            next(filin)
            next(filin)


def cut_kmer(read, kmer_size):
    """Cut read into kmers of size kmer_size.
    
    :param read: (str) Sequence of a read.
    :return: A generator object that iterate the kmers of of size kmer_size.
    """
    for i in range(len(read)-kmer_size+1):
        yield read[i:i+kmer_size]


def build_kmer_dict(fastq_file, kmer_size):
    """Build a dictionnary object of all kmer occurrences in the fastq file

    :param fastq_file: (str) Path to the fastq file.
    :return: A dictionnary object that identify all kmer occurrences.
    """
    kmer_dict = {}
    for read in read_fastq(fastq_file):
        for kmer in cut_kmer(read, kmer_size):
            if kmer in kmer_dict:
                kmer_dict[kmer] += 1
            else:
                kmer_dict[kmer] = 1
    return kmer_dict


def build_graph(kmer_dict):
    """Build the debruijn graph

    :param kmer_dict: A dictionnary object that identify all kmer occurrences.
    :return: A directed graph (nx) of all kmer substring and weight (occurrence).
    """
    digraph = nx.DiGraph()
    for kmer, count in kmer_dict.items():
        digraph.add_edge(kmer[:-1], kmer[1:], weight = count) 
    return digraph


def remove_paths(graph, path_list, delete_entry_node, delete_sink_node):
    """Remove a list of path in a graph. A path is set of connected node in
    the graph

    :param graph: (nx.DiGraph) A directed graph object
    :param path_list: (list) A list of path
    :param delete_entry_node: (boolean) True->We remove the first node of a path 
    :param delete_sink_node: (boolean) True->We remove the last node of a path
    :return: (nx.DiGraph) A directed graph object
    """
    if path_list:
        for path in path_list:
            if delete_entry_node == True and delete_sink_node == True:
                graph.remove_nodes_from(path)
            elif delete_entry_node == True and delete_sink_node == False:
                graph.remove_nodes_from(path[:-1])
            elif delete_entry_node == False and delete_sink_node == True:
                graph.remove_nodes_from(path[1:])
            elif delete_entry_node == False and delete_sink_node == False:
                graph.remove_nodes_from(path[1:-1])
    return graph


def select_best_path(graph, path_list, path_length, weight_avg_list, 
                     delete_entry_node=False, delete_sink_node=False):
    """Select the best path between different paths

    :param graph: (nx.DiGraph) A directed graph object
    :param path_list: (list) A list of path
    :param path_length_list: (list) A list of length of each path
    :param weight_avg_list: (list) A list of average weight of each path
    :param delete_entry_node: (boolean) True->We remove the first node of a path 
    :param delete_sink_node: (boolean) True->We remove the last node of a path
    :return: (nx.DiGraph) A directed graph object
    """
    if statistics.stdev(weight_avg_list)>0:
        index_to_remove = weight_avg_list.index(max(weight_avg_list))
    elif statistics.stdev(path_length)>0:
        index_to_remove = path_length.index(max(path_length))
    else:
        index_to_remove = random.randint(0,len(path_length))
    path_list.pop(index_to_remove)
    clean_graph = remove_paths(graph, path_list, delete_entry_node, delete_sink_node)
    return clean_graph

def path_average_weight(graph, path):
    """Compute the weight of a path

    :param graph: (nx.DiGraph) A directed graph object
    :param path: (list) A path consist of a list of nodes
    :return: (float) The average weight of a path
    """
    return statistics.mean([d["weight"] for (u, v, d) in graph.subgraph(path).edges(data=True)])

def solve_bubble(graph, ancestor_node, descendant_node):
    """Explore and solve bubble issue

    :param graph: (nx.DiGraph) A directed graph object
    :param ancestor_node: (str) An upstream node in the graph 
    :param descendant_node: (str) A downstream node in the graph
    :return: (nx.DiGraph) A directed graph object
    """
    path_list = list(nx.all_simple_paths(graph, ancestor_node, descendant_node))
    path_length = [len(i) for i in path_list]
    #weight_avg_list = [statistics.mean([j[2]['weight'] for j in list(graph.subgraph(i).edges(data=True))]) for i in path_list]
    weight_avg_list = [path_average_weight(graph, path) for path in path_list]
    solved_bubble = select_best_path(graph, path_list, path_length, weight_avg_list, delete_entry_node=False, delete_sink_node=False)
    return solved_bubble

def simplify_bubbles(graph):
    """Detect and explode bubbles

    :param graph: (nx.DiGraph) A directed graph object
    :return: (nx.DiGraph) A directed graph object
    """
    bubble = False
    for node in graph.nodes():
        predecessors = list(graph.predecessors(node))
        if len(predecessors)>1:
            # getting all predecessor unique combinations
            combinations = [(predecessors[i], predecessors[j]) for i in range(len(predecessors)-1) for j in range(i+1, len(predecessors)) if i != j]
            for combination in combinations:
                ancestor = nx.lowest_common_ancestor(graph, combination[0], combination[1])
                if ancestor:
                    bubble = True
                    break
        if bubble == True:
            break
    if bubble:
        graph = simplify_bubbles(solve_bubble(graph, ancestor, node))
    return graph


            


def solve_entry_tips(graph, starting_nodes):
    """Remove entry tips

    :param graph: (nx.DiGraph) A directed graph object
    :return: (nx.DiGraph) A directed graph object
    """
    for node in graph.nodes():
        paths = []
        path_length = []
        weight_avg_list = []
        # if the node has one or less predecessors we skip it
        if len(list(graph.predecessors(node))) > 1:
            for starting_node in starting_nodes:
                if nx.has_path(graph, starting_node, node):
                    for path in nx.all_simple_paths(graph, starting_node, node):
                        paths.append(path)
                
                        path_length.append(len(path))
                        weight_avg_list.append(path_average_weight(graph, path))
            break
    if len(paths) >= 2:
        # check choose the best and call select best path with True False 
        graph = solve_entry_tips(select_best_path(graph, paths, path_length, weight_avg_list, delete_entry_node=True, delete_sink_node=False), starting_nodes)
    return graph

def solve_out_tips(graph, ending_nodes):
    """Remove out tips

    :param graph: (nx.DiGraph) A directed graph object
    :return: (nx.DiGraph) A directed graph object
    """
    for node in graph.nodes():
        paths = []
        path_length = []
        weight_avg_list = []
        # if the node has one or less predecessors we skip it
        if len(list(graph.successors(node))) > 1:
            for ending_node in ending_nodes:
                if nx.has_path(graph, node, ending_node):
                    for path in nx.all_simple_paths(graph, node, ending_node):
                        paths.append(path)
                
                        path_length.append(len(path))
                        weight_avg_list.append(path_average_weight(graph, path))
            break
    if len(paths) >= 2:
        # check choose the best and call select best path with True False 
        graph = solve_out_tips(select_best_path(graph, paths, path_length, weight_avg_list, delete_entry_node=False, delete_sink_node=True), ending_nodes)
    return graph


def get_starting_nodes(graph):
    """Get nodes without predecessors

    :param graph: (nx.DiGraph) A directed graph object
    :return: (list) A list of all nodes without predecessors
    """
    starting_nodes = []
    for node in graph.nodes():
        # if the list of predecessors if empty it means it's a starting node
        # method 2: or check if in_degree of a node is empty
        if not list(graph.predecessors(node)):
            starting_nodes.append(node)

    return starting_nodes

def get_sink_nodes(graph):
    """Get nodes without successors

    :param graph: (nx.DiGraph) A directed graph object
    :return: (list) A list of all nodes without successors
    """
    sink_nodes = []
    for node in graph.nodes():
        # if the list of predecessors if empty it means it's a starting node
        # method 2: or check if in_degree of a node is empty
        if not list(graph.successors(node)):
            sink_nodes.append(node)

    return sink_nodes

def get_contigs(graph, starting_nodes, ending_nodes):
    """Extract the contigs from the graph

    :param graph: (nx.DiGraph) A directed graph object 
    :param starting_nodes: (list) A list of nodes without predecessors
    :param ending_nodes: (list) A list of nodes without successors
    :return: (list) List of [contiguous sequence and their length]
    """
    contig_list = []
    for starting_node in starting_nodes:
        for ending_node in ending_nodes:
            if nx.has_path(graph, starting_node, ending_node):
                for path in nx.all_simple_paths(graph, starting_node, ending_node):
                    sequence = str(path[0])
                    for node in path[1:]:
                        sequence += node[-1]
                    info = (sequence, len(sequence))
                    contig_list.append(info)
    return contig_list
                



def save_contigs(contigs_list, output_file):
    """Write all contigs in fasta format

    :param contig_list: (list) List of [contiguous sequence and their length]
    :param output_file: (str) Path to the output file
    """
    with open(output_file, "w") as filout:
        for i, (seq, length) in enumerate(contigs_list):
            filout.write(f">contig_{i} len={length}\n")
            wrapped_sequence = textwrap.fill(seq, width=80)
            filout.write(wrapped_sequence + "\n")


def draw_graph(graph, graphimg_file): # pragma: no cover
    """Draw the graph

    :param graph: (nx.DiGraph) A directed graph object
    :param graphimg_file: (str) Path to the output file
    """                                   
    fig, ax = plt.subplots()
    elarge = [(u, v) for (u, v, d) in graph.edges(data=True) if d['weight'] > 3]
    #print(elarge)
    esmall = [(u, v) for (u, v, d) in graph.edges(data=True) if d['weight'] <= 3]
    #print(elarge)
    # Draw the graph with networkx
    #pos=nx.spring_layout(graph)
    pos = nx.random_layout(graph)
    nx.draw_networkx_nodes(graph, pos, node_size=6)
    nx.draw_networkx_edges(graph, pos, edgelist=elarge, width=6)
    nx.draw_networkx_edges(graph, pos, edgelist=esmall, width=6, alpha=0.5, 
                           edge_color='b', style='dashed')
    #nx.draw_networkx(graph, pos, node_size=10, with_labels=False)
    # save image
    plt.savefig(graphimg_file)


#==============================================================
# Main program
#==============================================================
def main(): # pragma: no cover
    """
    Main program function
    """
    # Get arguments

    random.seed(1)
    args = get_arguments()
    dict_kmer = build_kmer_dict(args.fastq_file, args.kmer_size)
    graph = build_graph(dict_kmer)
    start_nodes = get_starting_nodes(graph)
    end_nodes = get_sink_nodes(graph)
    contigs = get_contigs(graph, start_nodes, end_nodes)
    save_contigs(contigs, args.output_file)
    graph = simplify_bubbles(graph)

    # Fonctions de dessin du graphe
    # A decommenter si vous souhaitez visualiser un petit 
    # graphe
    # Plot the graph
    # if args.graphimg_file:
    #     draw_graph(graph, args.graphimg_file)


if __name__ == '__main__': # pragma: no cover
    main()


