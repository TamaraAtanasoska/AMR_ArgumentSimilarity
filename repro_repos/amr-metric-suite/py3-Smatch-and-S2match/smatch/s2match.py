# -*- coding: utf-8 -*-
# !/usr/bin/env python

"""
This script computes smatch score between two AMRs.
For detailed description of smatch, see http://www.isi.edu/natural-language/amr/smatch-13.pdf

"""
import argparse

try:
    import amr_py3 as amr
except ModuleNotFoundError:
    import smatch.amr_py3 as amr
import os
import random
import sys
import time
from scipy.spatial.distance import euclidean, cosine, cityblock
import numpy as np
import math
import re

# total number of iteration in smatch computation
iteration_num = 5

# verbose output switch.
# Default false (no verbose output)
verbose = False

# single score output switch.
# Default true (compute a single score for all AMRs in two files)
single_score = True

# precision and recall output switch.
# Default false (do not output precision and recall, just output F score)
pr_flag = False

# Error log location
ERROR_LOG = sys.stderr

# Debug log location
DEBUG_LOG = sys.stderr

# dictionary to save pre-computed node mapping and its resulting triple match count
# key: tuples of node mapping
# value: the matching triple count
match_triple_dict = {}


def get_amr_line(input_f):
    """
    Read the file containing AMRs. AMRs are separated by a blank line.
    Each call of get_amr_line() returns the next available AMR (in one-line form).
    Note: this function does not verify if the AMR is valid

    """
    cur_amr = []
    has_content = False
    for line in input_f:
        line = line.strip()
        if line == "":
            if not has_content:
                # empty lines before current AMR
                continue
            else:
                # end of current AMR
                break
        if line.strip().startswith("#"):
            # ignore the comment line (starting with "#") in the AMR file
            # print(line)
            continue
        else:
            has_content = True
            cur_amr.append(line.strip())
    return "".join(cur_amr)


def load_vecs(fp):
    dic = {}
    if not fp:
        return dic
    with open(fp, "r") as f:
        for line in f:
            ls = line.split()
            word = ls[0]
            vec = np.array([float(x) for x in ls[1:]])
            dic[word] = vec
    return dic


def build_arg_parser():
    """
    Build an argument parser using argparse. Use it when python version is 2.7 or later.

    """
    parser = argparse.ArgumentParser(description="Smatch calculator -- arguments")
    parser.add_argument('-f', nargs=2, required=True, type=argparse.FileType('r'),
                        help='Two files containing AMR pairs. AMRs in each file are separated by a single blank line')
    parser.add_argument('-vectors', required=False, type=str, default="../vectors/glove.6B.100d.txt",
                        help='Filepath to Glove vectors')
    parser.add_argument('-similarityfunction', required=False, type=str, default="cosine",
                        help='similarity function')
    parser.add_argument('-cutoff', required=False, type=float, default=0.5,
                        help='only sim > cutoff taken into account')
    parser.add_argument('-diffsense', required=False, type=float, default=0.5,
                        help='coefficient of similarity when senses differ, e.g.' \
                             'hit-01 vs hit-02 ---> coef*1.0 ;;;;; hit-01 vs jump-0x ---> coef*sim(hit,jump)')
    parser.add_argument('-weighting_scheme', required=False, type=str, default='standard')
    parser.add_argument('-r', type=int, default=4, help='Restart number (Default:4)')
    parser.add_argument('-v', action='store_true', help='Verbose output (Default:false)')
    parser.add_argument('--ms', action='store_true', default=False,
                        help='Output multiple scores (one AMR pair a score)' \
                             'instead of a single document-level smatch score (Default: false)')
    parser.add_argument('-multi_token_concept_strategy', required=False, default="split", type=str,
                        help='default: \"split\"     you can also use \"None\": only direct vector lookup')
    parser.add_argument('--pr', action='store_true', default=False,
                        help="Output precision and recall as well as the f-score. Default: false")
    parser.add_argument('--do_not_mark_quotes', action='store_true',
                        help=":op1 \"David\" will be treated same as :op1 David")

    return parser


def cosine_sim(a, b):
    # cosine similarity, this is set as default.

    # Although "real" cosine similarity would be in [-1, 1] we treat everything < 0 as 0, since
    # the Smatch alignment may be ill defined when concept similarity < 0.0. 
    # An extension for future work could be to conduct the alignment on the 
    # absolute value of the similarity and perform the scoring after. This way 
    # Smatch could align "antonyms" (vectors pointing in opposite direction, cosim < 0) if needed but 
    # it would reduce the overall score, which could be desired when comparing AMRs of sentences 
    # that contain anotnyms.

    dist = cosine(a, b)
    sim = 1 - min(1, dist)
    return sim


def euclidean_sim(a, b):
    # euclidean distance, projected to similarity [0,1]
    dist = euclidean(a, b)
    sim = 1 / (math.e ** dist)
    return sim


def cityblock_sim(a, b):
    # manh distance, projected to similarity in [0, 1]
    dist = cityblock(a, b)
    sim = 1 / (math.e ** dist)
    return sim


def get_best_match(instance1, attribute1, relation1,
                   instance2, attribute2, relation2,
                   prefix1, prefix2, vectors, cutoff, diffsense, simfun, mwp,
                   weighting_scheme='standard'):
    """
    Get the highest triple match number between two sets of triples via hill-climbing.
    Arguments:
        instance1: instance triples of AMR 1 ("instance", node name, node value)
        attribute1: attribute triples of AMR 1 (attribute name, node name, attribute value)
        relation1: relation triples of AMR 1 (relation name, node 1 name, node 2 name)
        instance2: instance triples of AMR 2 ("instance", node name, node value)
        attribute2: attribute triples of AMR 2 (attribute name, node name, attribute value)
        relation2: relation triples of AMR 2 (relation name, node 1 name, node 2 name)
        prefix1: prefix label for AMR 1
        prefix2: prefix label for AMR 2
    Returns:
        best_match: the node mapping that results in the highest triple matching number
        best_match_num: the highest graded triple matching number

    """
    # Compute candidate pool - all possible node match candidates.
    # In the hill-climbing, we only consider candidate in this pool to save computing time.
    # weight_dict is a dictionary that maps a pair of node
    assert weighting_scheme in ['concept', 'structure', 'standard']
    (candidate_mappings, weight_dict) = compute_pool(instance1, attribute1, relation1,
                                                     instance2, attribute2, relation2,
                                                     prefix1, prefix2, vectors, cutoff, diffsense, simfun, mwp,
                                                     weighting_scheme=weighting_scheme)

    if verbose:
        log_helper.debug("Candidate mappings:")
        log_helper.debug(candidate_mappings)
        log_helper.debug("Weight dictionary")
        log_helper.debug(weight_dict)
    best_match_num = 0
    # initialize best match mapping
    # the ith entry is the node index in AMR 2 which maps to the ith node in AMR 1
    best_mapping = [-1] * len(instance1)
    for i in range(0, iteration_num):
        if verbose:
            log_helper.debug("Iteration", i)
        if i == 0:
            # smart initialization used for the first round
            cur_mapping = smart_init_mapping(candidate_mappings, instance1, instance2)
        else:
            # random initialization for the other round
            cur_mapping = random_init_mapping(candidate_mappings)
        # compute current triple match number
        match_num = compute_match(cur_mapping, weight_dict)
        if verbose:
            log_helper.debug("Node mapping at start", cur_mapping)
            log_helper.debug("Triple match number at start:", match_num)
        while True:
            # get best gain
            (gain, new_mapping) = get_best_gain(cur_mapping, candidate_mappings, weight_dict,
                                                len(instance2), match_num)
            if verbose:
                log_helper.debug("Gain after the hill-climbing", gain)
            # hill-climbing until there will be no gain for new node mapping
            if gain <= 0.0000000001:
                break
            # otherwise update match_num and mapping
            match_num += gain
            cur_mapping = new_mapping[:]
            if verbose:
                log_helper.debug("Update triple match number to:", match_num)
                log_helper.debug("Current mapping:", cur_mapping)
        if match_num > best_match_num:
            best_mapping = cur_mapping[:]
            best_match_num = match_num
    return best_mapping, best_match_num


def maybe_get_vec(word, vecs, mwp="split"):
    v = None
    if word in vecs:
        v = np.copy(vecs[word])
    # if it's a multi-word concept and not contained in vectors
    elif "-" in word:

        # if mwp strat = split, split multi-word and sum partial tokens
        if mwp == "split":
            ws = word.split("-")
            l = []
            for w in ws:
                if w in vecs:
                    l.append(vecs[w])
            if l:
                v = np.sum(np.array(l), axis=0)
    return v


def maybe_sim(a, b, vecs, cutoff=0.5, diffsense=0.5, simfun=cosine_sim, mwp="split"):
    # if identical, return 1
    if a == b:
        return 1.00

    # in case one or two are a pred, we also keep a string without the sense

    a_wo_sense = None
    b_wo_sense = None

    # if it's a pred we remove the sense, for now
    if "-" in a and re.match(".*[0-9]+", a):
        a_wo_sense = "-".join(a.split("-")[:-1])
    if "-" in b and re.match(".*[0-9]+", b):
        b_wo_sense = "-".join(b.split("-")[:-1])

    # if preds are equal but not sense return diffsense score, e.g., hit-01 vs hit-02
    if a_wo_sense and b_wo_sense and a_wo_sense == b_wo_sense:
        return 1.00 * diffsense

    # if same string but only one is pred --> different sense of concept, e.g. hit-01 vs hit
    elif a_wo_sense and a_wo_sense == b:
        return 1.00 * diffsense

    elif b_wo_sense and b_wo_sense == a:
        return 1.00 * diffsense

    # now we know now that two concepts are different and get their vectors
    if a_wo_sense:
        a_vec = maybe_get_vec(a_wo_sense, vecs, "None")
    else:
        a_vec = maybe_get_vec(a, vecs, mwp)
    if b_wo_sense:
        b_vec = maybe_get_vec(b_wo_sense, vecs, "None")
    else:
        b_vec = maybe_get_vec(b, vecs, mwp)

    # if there is no vector, return 0
    if a_vec is None or b_vec is None:
        return 0.00

    # if it's a pred, we add the vector for the morphological 3rd person extension
    if "-" in a and a_wo_sense:
        v = maybe_get_vec(a_wo_sense + "s", vecs, mwp="None")
        if v is not None:
            a_vec += v
    if "-" in b and b_wo_sense:
        v = maybe_get_vec(b_wo_sense + "s", vecs, mwp="None")
        if v is not None:
            b_vec += v

    # similarity
    sim = simfun(a_vec, b_vec)
    if not sim:
        return 0.00

    if sim > cutoff:

        # eg. hit-01 vs punch or hit-01 vs punch-0x ---> diffsense*(sim(hit,punch))
        if bool(a_wo_sense) or bool(b_wo_sense):
            return sim * diffsense
        else:
            return sim
    else:
        return 0.00


def maybe_has_sim(a, b, sim_dict, vecs={}, cutoff=0.5, diffsense=0.5, simfun=cosine_sim, mwp="split"):
    # maybe we have the computed similarities already?
    if a + "_" + b in sim_dict:
        return sim_dict[a + "_" + b]

    if b + "_" + a in sim_dict:
        return sim_dict[b + "_" + a]
    else:
        # compute similarity and save
        s = maybe_sim(a, b, vecs, cutoff=cutoff, diffsense=diffsense, simfun=simfun, mwp="split")
        if verbose:
            log_helper.debug("Similarity", a, b, s)
        sim_dict[a + "_" + b] = s
        sim_dict[b + "_" + a] = s
        return s


def compute_pool(instance1, attribute1, relation1,
                 instance2, attribute2, relation2,
                 prefix1, prefix2, vectors, cutoff=0.5, diffsense=0.5, simfun=cosine_sim, mwp="split",
                 weighting_scheme='standard'):
    """
    compute all possible node mapping candidates and their weights (the graded triple matching number gain resulting from
    mapping one node in AMR 1 to another node in AMR2)

    Arguments:
        instance1: instance triples of AMR 1
        attribute1: attribute triples of AMR 1 (attribute name, node name, attribute value)
        relation1: relation triples of AMR 1 (relation name, node 1 name, node 2 name)
        instance2: instance triples of AMR 2
        attribute2: attribute triples of AMR 2 (attribute name, node name, attribute value)
        relation2: relation triples of AMR 2 (relation name, node 1 name, node 2 name
        prefix1: prefix label for AMR 1
        prefix2: prefix label for AMR 2
    Returns:
      candidate_mapping: a list of candidate nodes.
                       The ith element contains the node indices (in AMR 2) the ith node (in AMR 1) can map to.
                       (resulting in non-zero triple match)
      weight_dict: a dictionary which contains the matching triple number for every pair of node mapping. The key
                   is a node pair. The value is another dictionary. key {-1} is triple match resulting from this node
                   pair alone (instance triples and attribute triples), and other keys are node pairs that can result
                   in relation triple match together with the first node pair.


    """
    assert weighting_scheme in ['concept', 'structure', 'standard']
    candidate_mapping = []
    weight_dict = {}
    sim_dict = {}
    for i in range(0, len(instance1)):
        # each candidate mapping is a set of node indices
        candidate_mapping.append(set())
        for j in range(0, len(instance2)):

            # if both triples are instance triples and have the same value
            """
            if instance1[i][0].lower() == instance2[j][0].lower() \
                    and instance1[i][2].lower() == instance2[j][2].lower():
                # get node index by stripping the prefix
                node1_index = int(instance1[i][1][len(prefix1):])
                node2_index = int(instance2[j][1][len(prefix2):])
                candidate_mapping[node1_index].add(node2_index)
                node_pair = (node1_index, node2_index)
                # use -1 as key in weight_dict for instance triples and attribute triples
                # use -1 as key in weight_dict for instance triples and attribute triples
                if node_pair in weight_dict:
                    weight_dict[node_pair][-1] += 1
                else:
                    weight_dict[node_pair] = {}
                    weight_dict[node_pair][-1] = 1
            """

            # if both triples are instance triples then we asses the similarity of their value
            if instance1[i][0].lower() == instance2[j][0].lower():
                value_1 = instance1[i][2].lower()
                value_2 = instance2[j][2].lower()
                similarity = maybe_has_sim(value_1, value_2, sim_dict, vecs=vectors,
                                           cutoff=cutoff, diffsense=diffsense,
                                           simfun=simfun, mwp=mwp)
                if weighting_scheme == 'concept':
                    similarity *= 3
                elif weighting_scheme == 'structure':
                    similarity *= 0.3333
                # get node index by stripping the prefix
                node1_index = int(instance1[i][1][len(prefix1):])
                node2_index = int(instance2[j][1][len(prefix2):])
                candidate_mapping[node1_index].add(node2_index)
                node_pair = (node1_index, node2_index)
                # use -1 as key in weight_dict for instance triples and attribute triples
                if node_pair in weight_dict:
                    weight_dict[node_pair][-1] += similarity
                else:
                    weight_dict[node_pair] = {}
                    weight_dict[node_pair][-1] = similarity
    for i in range(0, len(attribute1)):
        for j in range(0, len(attribute2)):
            # if both attribute relation triple have the same relation name and value
            if attribute1[i][0].lower() == attribute2[j][0].lower() \
                    and attribute1[i][2].lower() == attribute2[j][2].lower():
                node1_index = int(attribute1[i][1][len(prefix1):])
                node2_index = int(attribute2[j][1][len(prefix2):])
                candidate_mapping[node1_index].add(node2_index)
                node_pair = (node1_index, node2_index)
                # use -1 as key in weight_dict for instance triples and attribute triples
                if node_pair in weight_dict:
                    weight_dict[node_pair][-1] += 1
                else:
                    weight_dict[node_pair] = {}
                    weight_dict[node_pair][-1] = 1
            # if it's (top, x, conceptA) and (top, y, conceptB) and conceptA != conceptB --> similarity
            elif attribute1[i][0].lower() == attribute2[j][0].lower() == "top":
                value_1 = attribute1[i][2].lower()
                value_2 = attribute2[j][2].lower()
                similarity = maybe_has_sim(value_1, value_2, sim_dict, vecs=vectors,
                                           cutoff=cutoff, diffsense=diffsense, simfun=simfun, mwp=mwp)
                # get node index by stripping the prefix
                node1_index = int(attribute1[i][1][len(prefix1):])
                node2_index = int(attribute2[j][1][len(prefix2):])
                candidate_mapping[node1_index].add(node2_index)
                node_pair = (node1_index, node2_index)
                # use -1 as key in weight_dict for attribute triples and attribute triples
                if node_pair in weight_dict:
                    weight_dict[node_pair][-1] += similarity
                else:
                    weight_dict[node_pair] = {}
                    weight_dict[node_pair][-1] = similarity
    for i in range(0, len(relation1)):
        for j in range(0, len(relation2)):
            # if both relation share the same name
            if relation1[i][0].lower() == relation2[j][0].lower():
                node1_index_amr1 = int(relation1[i][1][len(prefix1):])
                node1_index_amr2 = int(relation2[j][1][len(prefix2):])
                node2_index_amr1 = int(relation1[i][2][len(prefix1):])
                node2_index_amr2 = int(relation2[j][2][len(prefix2):])
                # add mapping between two nodes
                candidate_mapping[node1_index_amr1].add(node1_index_amr2)
                candidate_mapping[node2_index_amr1].add(node2_index_amr2)
                node_pair1 = (node1_index_amr1, node1_index_amr2)
                node_pair2 = (node2_index_amr1, node2_index_amr2)
                if node_pair2 != node_pair1:
                    # update weight_dict weight. Note that we need to update both entries for future search
                    # i.e weight_dict[node_pair1][node_pair2]
                    #     weight_dict[node_pair2][node_pair1]
                    if node1_index_amr1 > node2_index_amr1:
                        # swap node_pair1 and node_pair2
                        node_pair1 = (node2_index_amr1, node2_index_amr2)
                        node_pair2 = (node1_index_amr1, node1_index_amr2)
                    if node_pair1 in weight_dict:
                        if node_pair2 in weight_dict[node_pair1]:
                            weight_dict[node_pair1][node_pair2] += 1
                        else:
                            weight_dict[node_pair1][node_pair2] = 1
                    else:
                        weight_dict[node_pair1] = {}
                        weight_dict[node_pair1][-1] = 0
                        weight_dict[node_pair1][node_pair2] = 1
                    if node_pair2 in weight_dict:
                        if node_pair1 in weight_dict[node_pair2]:
                            weight_dict[node_pair2][node_pair1] += 1
                        else:
                            weight_dict[node_pair2][node_pair1] = 1
                    else:
                        weight_dict[node_pair2] = {}
                        weight_dict[node_pair2][-1] = 0
                        weight_dict[node_pair2][node_pair1] = 1
                else:
                    # two node pairs are the same. So we only update weight_dict once.
                    # this generally should not happen.
                    if node_pair1 in weight_dict:
                        weight_dict[node_pair1][-1] += 1
                    else:
                        weight_dict[node_pair1] = {}
                        weight_dict[node_pair1][-1] = 1
    return candidate_mapping, weight_dict


def smart_init_mapping(candidate_mapping, instance1, instance2):
    """
    Initialize mapping based on the concept mapping (smart initialization)
    Arguments:
        candidate_mapping: candidate node match list
        instance1: instance triples of AMR 1
        instance2: instance triples of AMR 2
    Returns:
        initialized node mapping between two AMRs

    """
    random.seed()
    matched_dict = {}
    result = []
    # list to store node indices that have no concept match
    no_word_match = []
    for i, candidates in enumerate(candidate_mapping):
        if len(candidates) == 0:
            # no possible mapping
            result.append(-1)
            continue
        # node value in instance triples of AMR 1
        value1 = instance1[i][2]
        for node_index in candidates:
            value2 = instance2[node_index][2]
            # find the first instance triple match in the candidates
            # instance triple match is having the same concept value
            if value1 == value2:
                if node_index not in matched_dict:
                    result.append(node_index)
                    matched_dict[node_index] = 1
                    break
        if len(result) == i:
            no_word_match.append(i)
            result.append(-1)
    # if no concept match, generate a random mapping
    for i in no_word_match:
        candidates = list(candidate_mapping[i])
        while len(candidates) > 0:
            # get a random node index from candidates
            rid = random.randint(0, len(candidates) - 1)
            if candidates[rid] in matched_dict:
                candidates.pop(rid)
            else:
                matched_dict[candidates[rid]] = 1
                result[i] = candidates[rid]
                break
    return result


def random_init_mapping(candidate_mapping):
    """
    Generate a random node mapping.
    Args:
        candidate_mapping: candidate_mapping: candidate node match list
    Returns:
        randomly-generated node mapping between two AMRs

    """
    # if needed, a fixed seed could be passed here to generate same random (to help debugging)
    random.seed()
    matched_dict = {}
    result = []
    for c in candidate_mapping:
        candidates = list(c)
        if len(candidates) == 0:
            # -1 indicates no possible mapping
            result.append(-1)
            continue
        found = False
        while len(candidates) > 0:
            # randomly generate an index in [0, length of candidates)
            rid = random.randint(0, len(candidates) - 1)
            # check if it has already been matched
            if candidates[rid] in matched_dict:
                candidates.pop(rid)
            else:
                matched_dict[candidates[rid]] = 1
                result.append(candidates[rid])
                found = True
                break
        if not found:
            result.append(-1)
    return result


def compute_match(mapping, weight_dict):
    """
    Given a node mapping, compute match number based on weight_dict.
    Args:
    mappings: a list of node index in AMR 2. The ith element (value j) means node i in AMR 1 maps to node j in AMR 2.
    Returns:
    matching triple number
    Complexity: O(m*n) , m is the node number of AMR 1, n is the node number of AMR 2

    """
    # If this mapping has been investigated before, retrieve the value instead of re-computing.
    if verbose:
        log_helper.debug("Computing match for mapping")
        log_helper.debug(mapping)
    if tuple(mapping) in match_triple_dict:
        if verbose:
            log_helper.debug("saved value", match_triple_dict[tuple(mapping)])
        return match_triple_dict[tuple(mapping)]
    match_num = 0
    # i is node index in AMR 1, m is node index in AMR 2
    for i, m in enumerate(mapping):
        if m == -1:
            # no node maps to this node
            continue
        # node i in AMR 1 maps to node m in AMR 2
        current_node_pair = (i, m)
        if current_node_pair not in weight_dict:
            continue
        if verbose:
            log_helper.debug("node_pair", current_node_pair)
        for key in weight_dict[current_node_pair]:
            if key == -1:
                # matching triple resulting from instance/attribute triples
                match_num += weight_dict[current_node_pair][key]
                if verbose:
                    log_helper.debug("instance/attribute match", weight_dict[current_node_pair][key])
            # only consider node index larger than i to avoid duplicates
            # as we store both weight_dict[node_pair1][node_pair2] and
            #     weight_dict[node_pair2][node_pair1] for a relation
            elif key[0] < i:
                continue
            elif mapping[key[0]] == key[1]:
                match_num += weight_dict[current_node_pair][key]
                if verbose:
                    log_helper.debug("relation match with", key, weight_dict[current_node_pair][key])
    if verbose:
        log_helper.debug("match computing complete, result:", match_num)
    # update match_triple_dict
    match_triple_dict[tuple(mapping)] = match_num
    return match_num


def move_gain(mapping, node_id, old_id, new_id, weight_dict, match_num):
    """
    Compute the triple match number gain from the move operation
    Arguments:
        mapping: current node mapping
        node_id: remapped node in AMR 1
        old_id: original node id in AMR 2 to which node_id is mapped
        new_id: new node in to which node_id is mapped
        weight_dict: weight dictionary
        match_num: the original triple matching number
    Returns:
        the triple match gain number (might be negative)

    """
    # new node mapping after moving
    new_mapping = (node_id, new_id)
    # node mapping before moving
    old_mapping = (node_id, old_id)
    # new nodes mapping list (all node pairs)
    new_mapping_list = mapping[:]
    new_mapping_list[node_id] = new_id
    # if this mapping is already been investigated, use saved one to avoid duplicate computing
    if tuple(new_mapping_list) in match_triple_dict:
        return match_triple_dict[tuple(new_mapping_list)] - match_num
    gain = 0
    # add the triple match incurred by new_mapping to gain
    if new_mapping in weight_dict:
        for key in weight_dict[new_mapping]:
            if key == -1:
                # instance/attribute triple match
                gain += weight_dict[new_mapping][-1]
            elif new_mapping_list[key[0]] == key[1]:
                # relation gain incurred by new_mapping and another node pair in new_mapping_list
                gain += weight_dict[new_mapping][key]
    # deduct the triple match incurred by old_mapping from gain
    if old_mapping in weight_dict:
        for k in weight_dict[old_mapping]:
            if k == -1:
                gain -= weight_dict[old_mapping][-1]
            elif mapping[k[0]] == k[1]:
                gain -= weight_dict[old_mapping][k]
    # update match number dictionary
    match_triple_dict[tuple(new_mapping_list)] = match_num + gain
    return gain


def swap_gain(mapping, node_id1, mapping_id1, node_id2, mapping_id2, weight_dict, match_num):
    """
    Compute the triple match number gain from the swapping
    Arguments:
    mapping: current node mapping list
    node_id1: node 1 index in AMR 1
    mapping_id1: the node index in AMR 2 node 1 maps to (in the current mapping)
    node_id2: node 2 index in AMR 1
    mapping_id2: the node index in AMR 2 node 2 maps to (in the current mapping)
    weight_dict: weight dictionary
    match_num: the original matching triple number
    Returns:
    the gain number (might be negative)

    """
    new_mapping_list = mapping[:]
    # Before swapping, node_id1 maps to mapping_id1, and node_id2 maps to mapping_id2
    # After swapping, node_id1 maps to mapping_id2 and node_id2 maps to mapping_id1
    new_mapping_list[node_id1] = mapping_id2
    new_mapping_list[node_id2] = mapping_id1
    if tuple(new_mapping_list) in match_triple_dict:
        return match_triple_dict[tuple(new_mapping_list)] - match_num
    gain = 0
    new_mapping1 = (node_id1, mapping_id2)
    new_mapping2 = (node_id2, mapping_id1)
    old_mapping1 = (node_id1, mapping_id1)
    old_mapping2 = (node_id2, mapping_id2)
    if node_id1 > node_id2:
        new_mapping2 = (node_id1, mapping_id2)
        new_mapping1 = (node_id2, mapping_id1)
        old_mapping1 = (node_id2, mapping_id2)
        old_mapping2 = (node_id1, mapping_id1)
    if new_mapping1 in weight_dict:
        for key in weight_dict[new_mapping1]:
            if key == -1:
                gain += weight_dict[new_mapping1][-1]
            elif new_mapping_list[key[0]] == key[1]:
                gain += weight_dict[new_mapping1][key]
    if new_mapping2 in weight_dict:
        for key in weight_dict[new_mapping2]:
            if key == -1:
                gain += weight_dict[new_mapping2][-1]
            # to avoid duplicate
            elif key[0] == node_id1:
                continue
            elif new_mapping_list[key[0]] == key[1]:
                gain += weight_dict[new_mapping2][key]
    if old_mapping1 in weight_dict:
        for key in weight_dict[old_mapping1]:
            if key == -1:
                gain -= weight_dict[old_mapping1][-1]
            elif mapping[key[0]] == key[1]:
                gain -= weight_dict[old_mapping1][key]
    if old_mapping2 in weight_dict:
        for key in weight_dict[old_mapping2]:
            if key == -1:
                gain -= weight_dict[old_mapping2][-1]
            # to avoid duplicate
            elif key[0] == node_id1:
                continue
            elif mapping[key[0]] == key[1]:
                gain -= weight_dict[old_mapping2][key]
    match_triple_dict[tuple(new_mapping_list)] = match_num + gain
    return gain


def get_best_gain(mapping, candidate_mappings, weight_dict, instance_len, cur_match_num):
    """
    Hill-climbing method to return the best gain swap/move can get
    Arguments:
    mapping: current node mapping
    candidate_mappings: the candidates mapping list
    weight_dict: the weight dictionary
    instance_len: the number of the nodes in AMR 2
    cur_match_num: current triple match number
    Returns:
    the best gain we can get via swap/move operation

    """
    largest_gain = 0
    # True: using swap; False: using move
    use_swap = True
    # the node to be moved/swapped
    node1 = None
    # store the other node affected. In swap, this other node is the node swapping with node1. In move, this other
    # node is the node node1 will move to.
    node2 = None
    # unmatched nodes in AMR 2
    unmatched = set(range(0, instance_len))
    # exclude nodes in current mapping
    # get unmatched nodes
    for nid in mapping:
        if nid in unmatched:
            unmatched.remove(nid)
    for i, nid in enumerate(mapping):
        # current node i in AMR 1 maps to node nid in AMR 2
        for nm in unmatched:
            if nm in candidate_mappings[i]:
                # remap i to another unmatched node (move)
                # (i, m) -> (i, nm)
                if verbose:
                    log_helper.debug("Remap node", i, "from ", nid, "to", nm)
                mv_gain = move_gain(mapping, i, nid, nm, weight_dict, cur_match_num)
                if verbose:
                    log_helper.debug("Move gain:", mv_gain)
                    new_mapping = mapping[:]
                    new_mapping[i] = nm
                    new_match_num = compute_match(new_mapping, weight_dict)
                    if new_match_num != cur_match_num + mv_gain:
                        log_helper.error(mapping, new_mapping)
                        log_helper.error("Inconsistency in computing: move gain", cur_match_num, mv_gain, \
                                         new_match_num)
                if mv_gain > largest_gain:
                    largest_gain = mv_gain
                    node1 = i
                    node2 = nm
                    use_swap = False
    # compute swap gain
    for i, m in enumerate(mapping):
        for j in range(i + 1, len(mapping)):
            m2 = mapping[j]
            # swap operation (i, m) (j, m2) -> (i, m2) (j, m)
            # j starts from i+1, to avoid duplicate swap
            if verbose:
                log_helper.debug("Swap node", i, "and", j)
                log_helper.debug("Before swapping:", i, "-", m, ",", j, "-", m2)
                log_helper.debug(mapping)
                log_helper.debug("After swapping:", i, "-", m2, ",", j, "-", m)
            sw_gain = swap_gain(mapping, i, m, j, m2, weight_dict, cur_match_num)
            if verbose:
                log_helper.debug("Swap gain:", sw_gain)
                new_mapping = mapping[:]
                new_mapping[i] = m2
                new_mapping[j] = m
                log_helper.debug(new_mapping)
                new_match_num = compute_match(new_mapping, weight_dict)
                """
                #commented out because soft gain
                if new_match_num != cur_match_num + sw_gain:
                    log_helper.error( new_match_num, cur_match_num, sw_gain
                    log_helper.error( match, new_match
                    log_helper.error( "Inconsistency in computing: swap gain", cur_match_num, sw_gain, new_match_num
                """
            if sw_gain > largest_gain:
                largest_gain = sw_gain
                node1 = i
                node2 = j
                use_swap = True
    # generate a new mapping based on swap/move
    cur_mapping = mapping[:]
    if node1 is not None:
        if use_swap:
            if verbose:
                log_helper.debug("Use swap gain")
            temp = cur_mapping[node1]
            cur_mapping[node1] = cur_mapping[node2]
            cur_mapping[node2] = temp
        else:
            if verbose:
                log_helper.debug("Use move gain")
            cur_mapping[node1] = node2
    else:
        if verbose:
            log_helper.debug("no move/swap gain found")
    if verbose:
        log_helper.debug("Original mapping", mapping)
        log_helper.debug("Current mapping", cur_mapping)
    return largest_gain, cur_mapping


def print_alignment(mapping, instance1, instance2):
    """
    print the alignment based on a node mapping
    Args:
        match: current node mapping list
        instance1: nodes of AMR 1
        instance2: nodes of AMR 2

    """
    result = []
    for i, m in enumerate(mapping):
        if m == -1:
            result.append(instance1[i][1] + "(" + instance1[i][2] + ")" + "-Null")
        else:
            result.append(instance1[i][1] + "(" + instance1[i][2] + ")" + "-"
                          + instance2[m][1] + "(" + instance2[m][2] + ")")
    return " ".join(result)


def compute_f(match_num, test_num, gold_num):
    """
    Compute the f-score based on the matching triple number,
                                 triple number of AMR set 1,
                                 triple number of AMR set 2
    Args:
        match_num: matching triple number
        test_num:  triple number of AMR 1 (test file)
        gold_num:  triple number of AMR 2 (gold file)
    Returns:
        precision: match_num/test_num
        recall: match_num/gold_num
        f_score: 2*precision*recall/(precision+recall)
    """
    if test_num == 0 or gold_num == 0:
        return 0.00, 0.00, 0.00
    # print match_num, test_num
    # print match_num, gold_num
    precision = (0.000 + match_num) / (test_num + 0.000)
    recall = (0.000 + match_num) / (gold_num + 0.000)
    if (precision + recall) != 0:
        f_score = 2 * precision * recall / (precision + recall)
        if verbose:
            log_helper.debug("F-score:", f_score)
        return precision, recall, f_score
    else:
        if verbose:
            log_helper.debug("F-score:", "0.0")
        return precision, recall, 0.00


def get_sim_fun(string):
    if string == "cosine":
        return cosine_sim

    if string == "euclidean":
        return euclidean_sim

    if string == "cityblock":
        return cityblock_sim


def main(arguments):
    """
    Main function of smatch score calculation

    """
    global verbose
    global iteration_num
    global single_score
    global pr_flag
    global match_triple_dict
    # set the iteration number
    # total iteration number = restart number + 1
    iteration_num = arguments.r + 1
    if arguments.ms:
        single_score = False
    if arguments.v:
        verbose = True
    if arguments.pr:
        pr_flag = True
    # matching triple number
    total_match_num_soft = 0
    # triple number in test file
    total_test_num = 0
    # triple number in gold file
    total_gold_num = 0
    # sentence number
    sent_num = 1
    # Read amr pairs from two files
    vectors = load_vecs(arguments.vectors)
    simfun = get_sim_fun(arguments.similarityfunction)
    while True:
        cur_amr1 = get_amr_line(args.f[0])
        cur_amr2 = get_amr_line(args.f[1])
        if cur_amr1 == "" and cur_amr2 == "":
            break
        if cur_amr1 == "":
            log_helper.error("Error: File 1 has less AMRs than file 2")
            log_helper.error("Ignoring remaining AMRs")
            break
        if cur_amr2 == "":
            log_helper.error("Error: File 2 has less AMRs than file 1")
            log_helper.error("Ignoring remaining AMRs")
            break
        amr1 = amr.AMR.parse_AMR_line(cur_amr1, arguments.do_not_mark_quotes)
        amr2 = amr.AMR.parse_AMR_line(cur_amr2, arguments.do_not_mark_quotes)
        if not amr1 or not amr2:
            print("Smatch score F1: NA_WRONG_AMR")
            continue
        prefix1 = "a"
        prefix2 = "b"
        # Rename node to "a1", "a2", .etc
        amr1.rename_node(prefix1)
        # Renaming node to "b1", "b2", .etc
        amr2.rename_node(prefix2)
        (instance1, attributes1, relation1) = amr1.get_triples()
        (instance2, attributes2, relation2) = amr2.get_triples()
        if verbose:
            # print parse results of two AMRs
            log_helper.debug("AMR pair", sent_num)
            log_helper.debug("============================================")
            log_helper.debug("AMR 1 (one-line):", cur_amr1)
            log_helper.debug("AMR 2 (one-line):", cur_amr2)
            log_helper.debug("Instance triples of AMR 1:", len(instance1))
            log_helper.debug(instance1)
            log_helper.debug("Attribute triples of AMR 1:", len(attributes1))
            log_helper.debug(attributes1)
            log_helper.debug("Relation triples of AMR 1:", len(relation1))
            log_helper.debug(relation1)
            log_helper.debug("Instance triples of AMR 2:", len(instance2))
            log_helper.debug(instance2)
            log_helper.debug("Attribute triples of AMR 2:", len(attributes2))
            log_helper.debug(attributes2)
            log_helper.debug("Relation triples of AMR 2:", len(relation2))
            log_helper.debug(relation2)
        (best_mapping, best_match_num_soft) = get_best_match(instance1, attributes1, relation1,
                                                             instance2, attributes2, relation2,
                                                             prefix1, prefix2, vectors, arguments.cutoff,
                                                             arguments.diffsense, simfun,
                                                             arguments.multi_token_concept_strategy,
                                                             weighting_scheme=arguments.weighting_scheme)
        if verbose:
            log_helper.debug("best match number", best_match_num_soft)
            log_helper.debug("best node mapping", best_mapping)
            log_helper.debug("Best node mapping alignment:", print_alignment(best_mapping, instance1, instance2))
        test_triple_num = len(instance1) + len(attributes1) + len(relation1)
        gold_triple_num = len(instance2) + len(attributes2) + len(relation2)
        if not single_score:
            # if each AMR pair should have a score, compute and output it here
            (precision, recall, best_f_score) = compute_f(best_match_num_soft,
                                                          test_triple_num,
                                                          gold_triple_num)
            # print "Sentence", sent_num
            if pr_flag:
                print("Precision: %.3f" % precision)
                print("Recall: %.3f" % recall)
            #            print "Smatch score: %.3f" % best_f_score
            print("Smatch score F1 %.3f" % best_f_score)
        total_match_num_soft += best_match_num_soft
        total_test_num += test_triple_num
        total_gold_num += gold_triple_num
        # clear the matching triple dictionary for the next AMR pair
        match_triple_dict.clear()
        sent_num += 1
    if verbose:
        log_helper.debug("Total match number, total triple number in AMR 1, and total triple number in AMR 2:")
        log_helper.debug(total_match_num_soft, total_test_num, total_gold_num)
        log_helper.debug("---------------------------------------------------------------------------------")
    # output document-level smatch score (a single f-score for all AMR pairs in two files)
    if single_score:
        (precision, recall, best_f_score) = compute_f(total_match_num_soft, total_test_num, total_gold_num)
        if pr_flag:
            print("Precision: %.3f" % precision)
            print("Recall: %.3f" % recall)
    print("Document F-score: %.3f, %.4f" % (best_f_score, best_f_score))
    args.f[0].close()
    args.f[1].close()


# code necessary for Marco Damonte's subtask metric like reentrancies
def compute_s2match_from_two_lists(list1, list2
                                   , vectorpath="../vectors/glove.6B.100d.txt", simfun="cosine"
                                   , cutoff=0.5, diffsense=0.5, mwp="split"):
    def parse_relations(rels, v2c):
        var_list = []
        conc_list = []
        for r in rels:
            if str(r[1]) not in var_list and str(r[1]) != "TOP" and r[1] in v2c:
                var_list.append(str(r[1]))
                conc_list.append(str(v2c[r[1]]))
            if str(r[2]) not in var_list and r[2] in v2c:
                var_list.append(str(r[2]))
                conc_list.append(str(v2c[r[2]]))
        k = 0
        rel_dict = [] * len(var_list)
        att_dict = [] * len(var_list)
        for v in var_list:
            rel_dict.append({})
            att_dict.append({})
            for i in rels:
                if str(i[1]) == str(v) and i[2] in v2c:
                    rel_dict[k][str(i[2])] = i[0]
                    att_dict[k][i[0]] = str(v2c[i[2]])
            k += 1
        return amr.AMR(var_list, conc_list, rel_dict, att_dict)

    global verbose
    global iteration_num
    global single_score
    global pr_flag
    global match_triple_dict
    simfun = get_sim_fun(simfun)
    # set the iteration number
    # total iteration number = restart number + 1
    iteration_num = 5
    # if arguments.ms:
    #    single_score = False
    # if arguments.v:
    #    verbose = True
    # if arguments.pr:
    pr_flag = True
    # matching triple number
    total_match_num_soft = 0
    # triple number in test file
    total_test_num = 0
    # triple number in gold file
    total_gold_num = 0
    # sentence number
    sent_num = 1
    vectors = load_vecs(vectorpath)
    for l1, l2 in zip(list1, list2):
        lst_amr1, dic_amr1 = l1
        lst_amr2, dic_amr2 = l2
        amr1 = parse_relations(lst_amr1, dic_amr1)
        amr2 = parse_relations(lst_amr2, dic_amr2)
        prefix1 = "a"
        prefix2 = "b"
        # Rename node to "a1", "a2", .etc
        amr1.rename_node(prefix1)
        # Renaming node to "b1", "b2", .etc
        amr2.rename_node(prefix2)
        (instance1, attributes1, relation1) = amr1.get_triples()
        (instance2, attributes2, relation2) = amr2.get_triples()
        if verbose:
            # print parse results of two AMRs
            log_helper.debug("AMR pair", sent_num)
            log_helper.debug("============================================")
            log_helper.debug("AMR 1 (one-line):", cur_amr1)
            log_helper.debug("AMR 2 (one-line):", cur_amr2)
            log_helper.debug("Instance triples of AMR 1:", len(instance1))
            log_helper.debug(instance1)
            log_helper.debug("Attribute triples of AMR 1:", len(attributes1))
            log_helper.debug(attributes1)
            log_helper.debug("Relation triples of AMR 1:", len(relation1))
            log_helper.debug(relation1)
            log_helper.debug("Instance triples of AMR 2:", len(instance2))
            log_helper.debug(instance2)
            log_helper.debug("Attribute triples of AMR 2:", len(attributes2))
            log_helper.debug(attributes2)
            log_helper.debug("Relation triples of AMR 2:", len(relation2))
            log_helper.debug(relation2)
        (best_mapping, best_match_num_soft) = get_best_match(instance1, attributes1, relation1,
                                                             instance2, attributes2, relation2,
                                                             prefix1, prefix2, vectors, cutoff, diffsense, simfun, mwp)
        if verbose:
            log_helper.debug("best match number", best_match_num_soft)
            log_helper.debug("best node mapping", best_mapping)
            log_helper.debug("Best node mapping alignment:", print_alignment(best_mapping, instance1, instance2))
        test_triple_num = len(instance1) + len(attributes1) + len(relation1)
        gold_triple_num = len(instance2) + len(attributes2) + len(relation2)
        if not single_score:
            # if each AMR pair should have a score, compute and output it here
            (precision, recall, best_f_score) = compute_f(best_match_num_soft,
                                                          test_triple_num,
                                                          gold_triple_num)
            # print "Sentence", sent_num
            if pr_flag:
                print("Precision: %.3f" % precision)
                print("Recall: %.3f" % recall)
            #            print "Smatch score: %.3f" % best_f_score
            print("Smatch score F1 %.3f" % best_f_score)
        total_match_num_soft += best_match_num_soft
        total_test_num += test_triple_num
        total_gold_num += gold_triple_num
        # clear the matching triple dictionary for the next AMR pair
        match_triple_dict.clear()
        sent_num += 1
    if verbose:
        log_helper.debug("Total match number, total triple number in AMR 1, and total triple number in AMR 2:")
        log_helper.debug(total_match_num_soft, total_test_num, total_gold_num)
        log_helper.debug("---------------------------------------------------------------------------------")
    # output document-level smatch score (a single f-score for all AMR pairs in two files)
    return compute_f(total_match_num_soft, total_test_num, total_gold_num)


if __name__ == "__main__":
    parser = None
    args = None
    # only support python version 2.5 or later
    parser = build_arg_parser()
    args = parser.parse_args()
    from helpers import LogHelper

    if args.v:
        ll = 1
    else:
        ll = 5
    log_helper = LogHelper(ll)
    main(args)
