import re
import sqlite3
import sys
import snowballstemmer
from typing import Set
from core.runner import search
from core.preferences import DisplayMode, AnimateEmoji

# def get_main_page_results_list(word):
#     # Create DB or connect to one
#     conn = sqlite3.connect("wordtest_db.db")

#     # Create a cursor
#     c = conn.cursor()

#     c.execute(""" SELECT * FROM words""")
#     res = c.fetchall()

#     # Commit our changes
#     conn.commit()

#     # Close the connection
#     conn.close()
#     return res


def get_main_page_results_list(query: str):
    # user_query is the input word from the user
    user_query = query[:]

    dict_source = None

    search_run = None

    if user_query:
        include_auto_definitions = False
        search_run = search_with_affixes(
            user_query,
            include_auto_definitions=include_auto_definitions,
        )
        
        search_results = search_run.serialized_presentation_results(
            dict_source=dict_source
        )
        
        did_search = True

        search_results = should_show_form_of(
            search_results, dict_source, include_auto_definitions
        )
    
    else:
        search_results = []
        did_search = False
    
    

    return search_results


def search_with_affixes(query: str, include_auto_definitions=False):
    """
    Search for wordforms matching:
     - the wordform text
     - the definition keyword text
     - affixes of the wordform text
     - affixes of the definition keyword text
    """

    return search(query=query, include_auto_definitions=include_auto_definitions)

def should_show_form_of(search_results, dict_source, include_auto_definitions):
    for r in search_results:
        if dict_source:
            if not r["is_lemma"]:
                for d in r["lemma_wordform"]["definitions"]:
                    for s in d["source_ids"]:
                        if s in dict_source:
                            r["show_form_of"] = True
                        elif (
                            include_auto_definitions
                            and s.replace("🤖", "") in dict_source
                        ):
                            r["show_form_of"] = True
            if "show_form_of" not in r:
                r["show_form_of"] = False
        else:
            r["show_form_of"] = True

    return search_results

if __name__ == "__main__":
    output = get_main_page_results_list(sys.argv[1])
    print(output)