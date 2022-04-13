import re

from core.affix import (
    do_source_language_affix_search,
    do_target_language_affix_search
)
from core.SearchRun import SearchRun
# from CreeDictionary.API.search.espt import EsptSearch
from core.lookup import fetch_results
# from CreeDictionary.API.search.query import CvdSearchType
# from CreeDictionary.API.search.types import Result
# from CreeDictionary.API.search.util import first_non_none_value

CREE_LONG_VOWEL = re.compile("[êîôâēīōā]")


def search(
    *, query: str, include_affixes=True, include_auto_definitions=False
) -> SearchRun:
    """
    Perform an actual search, using the provided options.

    This class encapsulates the logic of which search methods to try, and in
    which order, to build up results in a SearchRun.
    """
    search_run = SearchRun(
        query=query, include_auto_definitions=include_auto_definitions
    )

    # if search_run.query.espt:
    #     espt_search = EsptSearch(search_run)
    #     espt_search.analyze_query()

    fetch_results(search_run)
    

    if (
        True
        and include_affixes
    ):
        do_source_language_affix_search(search_run)
        do_target_language_affix_search(search_run)
    

    if False:
        if cvd_search_type.should_do_search() and not is_almost_certainly_cree(
            search_run
        ):
            do_cvd_search(search_run)

    return search_run
