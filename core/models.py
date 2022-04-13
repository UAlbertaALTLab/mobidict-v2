from typing import List, Optional, Sequence, Tuple, Union

from typing_extensions import Literal, TypedDict

class SerializedDefinition(TypedDict):
    text: str
    source_ids: Sequence[str]
    is_auto_translation: bool


class Definition:
    
    def __init__(self, inputDict=None):
        self.text = ""
        self.raw_core_definition = None
        self.raw_semantic_definition = None
        
        if inputDict is not None:
            self.text = None if 'text' not in inputDict else inputDict['text']
            self.raw_core_definition = None if 'raw_core_definition' not in inputDict else inputDict['raw_core_definition']
            self.raw_semantic_definition = None if 'raw_semantic_definition' not in inputDict else inputDict['raw_semantic_definition']

    @property
    def core_definition(self):
        """
        Return the core definition, or the standard definition text if no
        explicit core definition has been provided.
        """
        if self.raw_core_definition is not None:
            return self.raw_core_definition
        return self.text

    @property
    def semantic_definition(self):
        """
        Return the semantic definition, or the standard definition text if no
        explicit core definition has been provided.
        """
        if self.raw_semantic_definition is not None:
            return self.raw_semantic_definition
        return self.text

    # # A definition **cites** one or more dictionary sources.
    # citations = models.ManyToManyField(DictionarySource)

    # # A definition defines a particular wordform
    # wordform = models.ForeignKey(
    #     Wordform, on_delete=models.CASCADE, related_name="definitions"
    # )

    # # If this definition is auto-generated based on a different definition,
    # # point at the source definition.
    auto_translation_source_id = None

    # Why this property exists:
    # because DictionarySource should be its own model, but most code only
    # cares about the source IDs. So this removes the coupling to how sources
    # are stored and returns the source IDs right away.
    @property
    def source_ids(self) -> list[str]:
        """
        A tuple of the source IDs that this definition cites.
        """
        return {}

    def serialize(self) -> SerializedDefinition:
        """
        :return: json parsable format
        """
        return {
            "text": self.text,
            "source_ids": self.source_ids,
            "is_auto_translation": self.auto_translation_source_id is not None,
        }

    def __str__(self):
        return self.text