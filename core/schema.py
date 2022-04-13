from typing import TypedDict, List, Sequence

class SerializedDefinition(TypedDict):
    text: str
    source_ids: Sequence[str]
    is_auto_translation: bool

class SerializedWordform(TypedDict):
    id: int
    text: str
    inflectional_category: str
    pos: str
    analysis: str
    is_lemma: bool
    as_is: bool
    lemma: int  # the id of the lemma

    # ---- calculated properties ----
    lemma_url: str

    # ---- informational properties ----
    inflectional_category_plain_english: str
    inflectional_category_linguistic: str
    wordclass_emoji: str
    wordclass: str

    # ---- foreign keys ----
    definitions: List[SerializedDefinition]