"""This module handles the conversion from the HuRIC xml format to the CoNLL 2009 format

CoNLL 2009 columns (from preprocess.py and http://ufal.mff.cuni.cz/conll2009-st/task-description.html):
0: ID         a progressive for the word starting from 1
1: FORM       the word
2: LEMMA      the lemma of the word (GOLD)
3: PLEMMA     the lemma of the word (predicted automatically)
4: POS        the Part Of Speech (GOLD)
5: PPOS       the Part Of Speech (predicted automatically)
6: FEAT       morphological features (GOLD) (not used, the sentence_ID is put there)
7: PFEAT      morphological features (predicted automatically) (not used)
8: HEAD       the parent in the dependency tree or 0 for root (GOLD)
9: PHEAD      the parent in the dependency tree or 0 for root (predicted automatically)
10: DEPREL    the syntactic relationship with HEAD (GOLD)
11: PDEPREL   the syntactic relationship with HEAD (predicted automatically)
12: FILLPRED  the Lexical Unit (lemma.POS)
13: PRED      the Frame name
14: APREDs    the Frame Element notation (IOB + S when start==end like U in BILUO)
"""
import codecs
import os.path
import sys
import xml.etree.ElementTree as ET

from collections import defaultdict

PATH_DATASETS = 'data'
PATH_CONLL = 'data/neural'


def huric_xml_to_conll(dataset_name):
    path_source = '{}/{}'.format(PATH_DATASETS, dataset_name)

    files_list = os.listdir(path_source)

    print('#files: ', len(files_list))

    results = []

    for file_name in sorted(files_list):
        file_location = '{}/{}'.format(path_source, file_name)
        with open(file_location) as file_in:
            tree = ET.parse(file_in)

        root = tree.getroot()
        command_id = root.attrib['id']

        # read the tokens, saving in a map indexed by the id
        tokens = [t.attrib for t in root.findall('tokens/token')]
        deps_by_t_id = {d.attrib['to']: d.attrib for d in root.findall('dependencies/dep')}

        for frame in root.findall('semantics/frameSemantics/frame'):
            frame_name = frame.attrib['name']
            lus = [lu.attrib['id'] for lu in frame.findall('lexicalUnit/token')]
            fe_by_t_id = defaultdict(lambda: 'O')
            for frame_element in frame.findall('frameElement'):
                fe_name = frame_element.attrib['type']
                fe_name = get_fe_framenet(fe_name)
                element_tokens = frame_element.findall('token')
                for count, token in enumerate(element_tokens):
                    prefix = 'B' if not count else 'I'
                    if len(element_tokens) == 1:
                        prefix = 'S'
                    iob_label = '{}-{}'.format(prefix, fe_name)
                    fe_by_t_id[token.attrib['id']] = iob_label
            #print(tokens, deps_by_t_id)
            conll_annotation = [
                [
                    t['id'],
                    t['surface'],
                    t['lemma'], #LEMMA
                    t['lemma'], #PLEMMA
                    t['pos'], #POS
                    t['pos'], #PPOS
                    command_id, #FEAT
                    '_', #PFEAT
                    deps_by_t_id[t['id']]['from'], #HEAD
                    deps_by_t_id[t['id']]['from'], #PHEAD
                    deps_by_t_id[t['id']]['type'], #DEPREL
                    deps_by_t_id[t['id']]['type'], #PDEPREL
                    '{}.{}'.format(get_lu_lemma(t['lemma']), get_fn_pos_by_rules(t['pos'])) if t['id'] in lus else '_', #FILLPRED
                    get_fn_frame_name(frame_name) if t['id'] in lus else '_', #PRED
                    fe_by_t_id[t['id']] #PREDs
                ]
                for t in tokens]

            results.append(conll_annotation)

    return results

def get_fn_frame_name(huric_name):
    """Map back from HuRIC to FrameNet frame names"""
    mapping = {
        'Entering': 'Arriving',
        'Following': 'Cotheme',
        'Searching': 'Scrutiny'
    }
    result = huric_name
    if huric_name in mapping:
        result = mapping[huric_name]

    return result

def get_lu_lemma(lemma):
    mapping = {
        'halfcarri': 'carry',
        'positioning': 'position',
        'reconnoiter': 'reconnoitre',
        'half-l': 'lead',
        # HuRIC
        'be': 'constitute',
        'there': 'constitute',
        'along': 'go', # go along
        'let': 'go', # let go
        'up': 'pick' # pick up
    }
    result = lemma
    if lemma in mapping:
        result = mapping[lemma]

    return result

def get_fe_framenet(fe):
    mapping = {
        'Desired_state': 'Desired_state_of_affairs',
        'Reencoding': 'Re-encoding'
    }
    result = fe
    if fe in mapping:
        result = mapping[fe]

    return result

def write_conll_samples(samples, dataset_name, mode):
    out_path = '{}/{}'.format(PATH_CONLL, dataset_name)
    # TODO divide fulltext from dev
    conll_file_loc = '{}/{}.{}.syntaxnet.conll'.format(out_path, dataset_name, mode)
    with open(conll_file_loc, 'w') as f:
        for seq in samples:
            for s in seq:
                f.write('\t'.join(s) + '\n')
            f.write('\n')

    conll_file_loc = '{}/{}.fulltext.train.syntaxnet.conll'.format(out_path, dataset_name)
    with open(conll_file_loc, 'w') as f:
        for seq in samples:
            for s in seq:
                f.write('\t'.join(s) + '\n')
            f.write('\n')

    conll_file_loc = '{}/{}.fulltext.train.syntaxnet.conll.sents'.format(out_path, dataset_name)
    with open(conll_file_loc, 'w') as f:
        for seq in samples:
            sentence = ' '.join([w[1] for w in seq])
            f.write(sentence + '\n')

def get_fn_pos_by_rules(pos):
    """
    Rules for mapping HuRIC part of speech tags into FrameNet tags
    """
    if pos == 'JJ':
        rule_pos = 'a'
    elif pos in ['NN', 'NNP', 'NNS']:
        rule_pos = 'n'
    elif pos in ['VB', 'VBD', 'VBG', 'VBN', 'VBP', 'VBZ', 'RP', 'EX']:
        rule_pos = 'v'
    else:
        raise Exception("Rule not defined for part-of-speech word", pos)
    return rule_pos

def main():
    samples = huric_xml_to_conll('framenet_subset')
    write_conll_samples(samples, 'framenet_subset', 'dev')

    samples = huric_xml_to_conll('huric_modern')
    write_conll_samples(samples, 'huric_modern', 'test')


if __name__ == '__main__':
    main()