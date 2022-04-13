from nis import match
import sqlite3
import os

from typing import Dict, Iterable, List, NewType, Tuple
from collections import defaultdict
import dawg
from itertools import chain

import unicodedata
from unicodedata import normalize
from core.SearchRun import SearchRun
from core.typesCore import Result
from core.cree_lev_dist import get_modified_distance
from core.WordForm import Wordform

InternalForm = NewType("InternalForm", str)

SimplifiedForm = NewType("SimplifiedForm", str)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


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


def _reverse(text: SimplifiedForm) -> SimplifiedForm:
    return SimplifiedForm(text[::-1])


class AffixSearcher:
    """
    Enables prefix and suffix searches given a list of words and their wordform IDs.
    """

    def __init__(self, words: Iterable[Tuple[str, int]]):
        self.text_to_ids: Dict[str, List[int]] = defaultdict(list)

        words_marked_for_indexing = [
            (simplified_text, wordform_id)
            for raw_text, wordform_id in words
            if (simplified_text := self.to_simplified_form(raw_text))
        ]

        for text, wordform_id in words_marked_for_indexing:
            self.text_to_ids[self.to_simplified_form(text)].append(wordform_id)

        if True:
            self._prefixes = dawg.CompletionDAWG(
                [text for text, _ in words_marked_for_indexing]
            )
            self._suffixes = dawg.CompletionDAWG(
                [_reverse(text) for text, _ in words_marked_for_indexing]
            )

    def search_by_prefix(self, prefix: str) -> Iterable[int]:
        """
        :return: an iterable of Wordform IDs that match the prefix
        """
        term = self.to_simplified_form(prefix)
        matched_words = self._prefixes.keys(term)
        return chain.from_iterable(self.text_to_ids[t] for t in matched_words)

    def search_by_suffix(self, suffix: str) -> Iterable[int]:
        """
        :return: an iterable of Wordform IDs that match the suffix
        """
        term = self.to_simplified_form(suffix)
        matched_reversed_words = self._suffixes.keys(_reverse(term))
        return chain.from_iterable(
            self.text_to_ids[_reverse(t)] for t in matched_reversed_words
        )

    @staticmethod
    def to_simplified_form(query: str) -> SimplifiedForm:
        """
        Convert to a simplified form of the word and its orthography to facilitate affix
        search.  You SHOULD throw out diacritics, choose a Unicode Normalization form,
        and choose a single letter case here!
        """
        return SimplifiedForm(to_source_language_keyword(query.lower()))

def do_affix_search(query: InternalForm, affixes: AffixSearcher) -> Iterable[Wordform]:
    """
    Augments the given set with results from performing both a suffix and prefix search on the wordforms.
    """
    matched_ids = set(affixes.search_by_prefix(query))
    matched_ids |= set(affixes.search_by_suffix(query))
    
    conn = sqlite3.connect(BASE_DIR + '/../test_db.sqlite3')
    
    conn.row_factory = sqlite3.Row

    c = conn.cursor()
    
    subquery = make_search_query_using_set(matched_ids)
    
    queryToExecute = f""" SELECT * FROM lexicon_wordform
                    WHERE id in {subquery} """
                    
    
    c.execute(queryToExecute)                
    
    wfs = []
    
    db_matches = c.fetchall()
    
    for wf in db_matches:
        data = dict(wf)
        final_wf = make_wordform_dict(data)
        wfs.append(final_wf)

    return wfs

def make_search_query_using_set(inputSet: set) -> str:
    final_q = "("
    
    for idx, id in enumerate(inputSet):
        final_q += str(id)
        if idx != len(inputSet) - 1:
            final_q += ','
    
    final_q += ')'
    return final_q
        

def do_source_language_affix_search(search_run: SearchRun):
    matching_words = do_affix_search(
        search_run.internal_query,
        source_language_affix_searcher(),
    )
    for word in matching_words:
        search_run.add_result(
            Result(
                word,
                source_language_affix_match=True,
                query_wordform_edit_distance=get_modified_distance(
                    word.text, search_run.internal_query
                ),
            )
        )     

def do_target_language_affix_search(search_run: SearchRun):
    matching_words = do_affix_search(
        search_run.internal_query,
        target_language_affix_searcher()
    )
    for word in matching_words:
        search_run.add_result(Result(word, target_language_affix_match=True))

# This is going to help with "cache.language_affix_searcher" in the top method
# Also, wherever WordForm is used, just use a direct DB call rather


EXTRA_REPLACEMENTS = str.maketrans(
    {"ł": "l", "Ł": "L", "ɫ": "l", "Ɫ": "l", "ø": "o", "Ø": "O"}
)


def to_source_language_keyword(s: str) -> str:
    """Convert a source-language wordform to an indexable keyword

    Currently removes accents, and leading and trailing hyphens.

    There will be collisions but we could use edit distance to rank them.
    """
    s = s.lower()
    return (
        "".join(c for c in normalize("NFD", s)
                if unicodedata.combining(c) == 0)
        .translate(EXTRA_REPLACEMENTS)
        .strip("-"))


def fetch_source_language_lemmas_with_ids():
    """
    Return tuple of (text, id) pairs for all lemma Wordforms
    """
    # Slurp up all the results to prevent walking the database multiple times
    
    conn = sqlite3.connect(BASE_DIR + '/../test_db.sqlite3')

    c = conn.cursor()
    
    queryToExecute = f""" SELECT text, id FROM lexicon_wordform
                    WHERE is_lemma = 1 """
                    
    c.execute(queryToExecute)
    
    lemmas_with_ids = c.fetchall()
    
    return tuple(lemmas_with_ids)

def source_language_affix_searcher() -> AffixSearcher:
        """
        Returns the affix searcher that matches source language lemmas
        """
        return AffixSearcher(fetch_source_language_lemmas_with_ids())

def fetch_target_language_keywords_with_ids():
    """
    Return tuple of (text, Wordform ID) pairs for all target-language keywords
    """
    # Slurp up all the results to prevent walking the database multiple times
    
    conn = sqlite3.connect(BASE_DIR + '/../test_db.sqlite3')

    c = conn.cursor()
    
    queryToExecute = f""" SELECT text, wordform_id FROM lexicon_targetlanguagekeyword"""
                    
    c.execute(queryToExecute)
    
    all_results = c.fetchall()
    
    return tuple(all_results)

def target_language_affix_searcher() -> AffixSearcher:
        """
        Returns the affix searcher that matches target language keywords mined from the dictionary
        definitions
        """
        return AffixSearcher(fetch_target_language_keywords_with_ids())