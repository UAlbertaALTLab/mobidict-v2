from __future__ import annotations

import sqlite3
import os
import json

from core.typesCore import Result

from core.WordForm import rich_analyze_relaxed, strict_generator

from core.english_keyword_extraction import stem_keywords

from core.SearchRun import SearchRun
from core.WordForm import Wordform
from core.affix import to_source_language_keyword

from core.cree_lev_dist import get_modified_distance

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def fetch_results(search_run: SearchRun):
    
    # Connect to the DB
    conn = sqlite3.connect(BASE_DIR + '/../test_db.sqlite3')

    conn.row_factory = sqlite3.Row

    c = conn.cursor()
    
    fetch_results_from_target_language_keywords(search_run)

    fetch_results_from_source_language_keywords(search_run)

    # Use the spelling relaxation to try to decipher the query
    #   e.g., "atchakosuk" becomes "acâhkos+N+A+Pl" --
    #         thus, we can match "acâhkos" in the dictionary!
    fst_analyses = set(rich_analyze_relaxed(search_run.internal_query))

    fst_analyses_list = [a.tuple for a in fst_analyses]

    query_list = []
    for analyses in fst_analyses_list:
        query_list.append(json.dumps([list(analyses.prefixes), analyses.lemma, list(analyses.suffixes)], ensure_ascii=False))

    fqueryList = str(tuple(query_list))
    
    if len(query_list) == 1:
        fqueryList = fqueryList[:len(fqueryList) - 2] + ')'
    
    queryToExecute = f""" SELECT * FROM lexicon_wordform
                    WHERE raw_analysis in {fqueryList}
                """

    c.execute(queryToExecute)
    
    db_matches = c.fetchall()
    
    for wf in db_matches:
        data = dict(wf)
        finalWordFormToAdd = make_wordform_dict(data)
        search_run.add_result(
            Result(
                finalWordFormToAdd,
                source_language_match=finalWordFormToAdd.text,
                query_wordform_edit_distance=get_modified_distance(
                    finalWordFormToAdd.text, search_run.internal_query
                ),
            )
        )

        # An exact match here means we’re done with this analysis.
        fst_analyses.discard(finalWordFormToAdd.analysis)
    
    

    # fst_analyses has now been thinned by calls to `fst_analyses.remove()`
    # above; remaining items are analyses which are not in the database,
    # although their lemmas should be.
    for analysis in fst_analyses:
        # When the user query is outside of paradigm tables
        # e.g. mad preverb and reduplication: ê-mâh-misi-nâh-nôcihikocik
        # e.g. Initial change: nêpât: {'IC+nipâw+V+AI+Cnj+3Sg'}

        normatized_form_for_analysis = strict_generator().lookup(analysis.smushed())
        if len(normatized_form_for_analysis) == 0:
            print("Cannot generate normative form for the current analysis")
            continue

        # If there are multiple forms for this analysis, use the one that is
        # closest to what the user typed.
        normatized_user_query = min(
            normatized_form_for_analysis,
            key=lambda f: get_modified_distance(f, search_run.internal_query),
        )
        
        # Fetch the list of wordforms
        getWordformQuery = f""" SELECT * FROM lexicon_wordform WHERE is_lemma = 1 
                                AND text = \"{analysis.lemma}\"
                            """
        c.execute(getWordformQuery)
        
        resultsReceived = c.fetchall()
        wfListToPass = []
        
        for w in resultsReceived:
            data = dict(w)
            wfToAdd = make_wordform_dict(data)
            wfListToPass.append(wfToAdd)
        

        possible_lemma_wordforms = best_lemma_matches(
            analysis, wfListToPass
        )
        
        

        for lemma_wordform in possible_lemma_wordforms:
            inputDict = {'text': normatized_user_query, 'raw_analysis': analysis.tuple, 'lemma': lemma_wordform}
            synthetic_wordform = Wordform(
                inputDict
            )
            search_run.add_result(
                Result(
                    synthetic_wordform,
                    analyzable_inflection_match=True,
                    query_wordform_edit_distance=get_modified_distance(
                        search_run.internal_query,
                        normatized_user_query,
                    ),
                )
            )

def best_lemma_matches(analysis, possible_lemmas) -> list[Wordform]:
    """
    Return best matches between analysis and potentially matching lemmas

    The following example is in Plains Cree but the algorithm should be good
    enough for any language.

    nikîmôci-nêwokâtânân has analysis PV/kimoci+nêwokâtêw+V+AI+Ind+1Pl

    Which of the three lemmas for nêwokâtêw should that be matched to?

    Let’s take the ones with the most tags in common.

                                    Tags in common    Winner
        nêwokâtêw+N+A+Sg            0
        nêwokâtêw+V+AI+Ind+3Sg      3   +V +AI +Ind   *
        nêwokâtêw+V+II+Ind+3Sg      2   +V +Ind

    We may get better results if we have, for the wordform language, a list of
    lexical tags like +V to consider as opposed to inflectional tags like +3Sg.
    """
    possible_lemmas = possible_lemmas[:]
    if len(possible_lemmas) < 2:
        return possible_lemmas

    lemmas_with_analyses = [wf for wf in possible_lemmas if wf.analysis]

    if len(lemmas_with_analyses) == 0:
        # Cannot figure out the intersection if we have no analyses!
        return possible_lemmas

    max_tag_intersection_count = max(
        analysis.tag_intersection_count(lwf.analysis) for lwf in lemmas_with_analyses
    )
    return [
        lwf
        for lwf in possible_lemmas
        if lwf.analysis
        and analysis.tag_intersection_count(lwf.analysis) == max_tag_intersection_count
    ]


def fetch_results_from_target_language_keywords(search_run):

    stem_keys = stem_keywords(search_run.internal_query)

    # Connect to the DB
    conn = sqlite3.connect(BASE_DIR + '/../test_db.sqlite3')

    conn.row_factory = sqlite3.Row

    c = conn.cursor()

    for stemmed_keyword in stem_keys:

        queryToExecute = f""" SELECT * FROM lexicon_wordform INNER JOIN lexicon_targetlanguagekeyword
                    ON lexicon_targetlanguagekeyword.wordform_id = lexicon_wordform.id
                    WHERE lexicon_targetlanguagekeyword.text = \"{stemmed_keyword}\"
                """

        c.execute(queryToExecute)

        results = c.fetchall()
        for wordform in results:
            data = dict(wordform)

            finalWordFormToAdd = make_wordform_dict(data)

            search_run.add_result(
                Result(finalWordFormToAdd, target_language_keyword_match=[
                    stemmed_keyword])
            )

    conn.close()


inputDictTest = {'id': 1, 'x': 2, 'is_lemma': 0, 'lemma': {'id': 2, 'x': 3, 'is_lemma': 0, 'lemma': {
    'id': 3, 'x': 4, 'is_lemma': 1, 'lemma': {'id': 3, 'x': 4, 'is_lemma': 1}}}}


def make_wordform_dict(data):
    '''
    Given a dict, returns a WordForm object to be added.
    '''
    # Connect to the DB
    conn = sqlite3.connect(BASE_DIR + '/../test_db.sqlite3')

    conn.row_factory = sqlite3.Row

    c = conn.cursor()

    wfCopy = data

    while True:
        if wfCopy['is_lemma']:
            wfCopy['lemma'] = wfCopy.copy()
            break
        wfCopy['lemma'] = {}

        queryToSearch = f""" SELECT * FROM lexicon_wordform 
            WHERE id = \"{wfCopy['lemma_id']}\"
        """

        c.execute(queryToSearch)

        res = c.fetchone()
        wfFetched = dict(res)
        wfCopy['lemma'] = wfFetched
        wfCopy = wfCopy['lemma']

    # finalDictToAdd = build_nested_wordform(wfCopy)
    finalWordFormToAdd = build_nested_wordform(data)
    return finalWordFormToAdd


def build_nested_wordform(inputDict):
    inputDictCopy = inputDict

    inputDictCopy = Wordform(inputDictCopy)
    inputDictToReturn = inputDictCopy

    while True:
        if inputDictCopy.is_lemma:
            # base case
            inputDictCopy.lemma = inputDictCopy
            break
        inputDictCopy.lemma = Wordform(inputDictCopy.lemma)
        inputDictCopy = inputDictCopy.lemma
    return inputDictToReturn


def fetch_results_from_source_language_keywords(search_run):

    keyword = to_source_language_keyword(search_run.internal_query)

    conn = sqlite3.connect(BASE_DIR + '/../test_db.sqlite3')

    conn.row_factory = sqlite3.Row

    c = conn.cursor()

    queryToExecute = f""" SELECT * FROM lexicon_sourcelanguagekeyword
                    WHERE text = \"{keyword}\"
                """

    c.execute(queryToExecute)

    results = c.fetchall()

    for res in results:
        f_res = dict(res)

        queryToRun = f""" SELECT * FROM lexicon_wordform
                    WHERE id = \"{f_res['wordform_id']}\"
                """
        c.execute(queryToRun)

        wordform = c.fetchone()

        data = dict(wordform)

        finalWordFormToAdd = make_wordform_dict(data)

        search_run.add_result(
            Result(
                finalWordFormToAdd,
                source_language_keyword_match=[f_res['text']],
                query_wordform_edit_distance=get_modified_distance(
                    search_run.internal_query, finalWordFormToAdd.text
                ),
            )
        )
