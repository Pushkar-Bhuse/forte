# Copyright 2022 The Forte Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
This Processor focuses on calling data augmentation ops
to generate texts similar to those in the input pack
and create a new pack with them.
"""
from abc import ABC
from collections import defaultdict
from typing import List, Tuple, Dict, DefaultDict, Union, cast
from forte.common.configuration import Config
from forte.common.resources import Resources
from forte.data.data_pack import DataPack
from forte.data.multi_pack import MultiPack
from forte.data.ontology.core import Entry, BaseLink
from forte.data.ontology.top import (
    MultiPackLink,
    MultiPackGroup,
)
from forte.processors.base import MultiPackProcessor
from forte.utils.utils import create_class_with_kwargs

__all__ = ["ParentDataAugmentProcessor", "BaseDataAugmentOpProcessor"]


class ParentDataAugmentProcessor(MultiPackProcessor, ABC):
    r"""
    The base class of processors that augment data.
    This processor instantiates replacement ops where specific
    data augmentation algorithms are implemented. The data augmentation ops
    will run the algorithms and the processor will create Forte
    data structures based on the augmented inputs.
    """


class BaseDataAugmentOpProcessor(ParentDataAugmentProcessor):
    r"""
    This is a Base Data Augmentation Op Processor that instantiates
    data augmentation ops into Forte Data Structures to be used. It can
    handle augmentations of multiple ontologies simultaneously and copy
    all existing tokens from source data pack to augmented data pack.
    """

    def __init__(self):
        super().__init__()

        self.new_data_packs: DefaultDict[int, DataPack] = defaultdict()
        self._data_pack_map: Dict[int, int] = {}
        self._entry_maps: Dict[int, Dict[int, int]] = {}

    def initialize(self, resources: Resources, configs: Config):
        super().initialize(resources, configs)

    def _copy_multi_pack_link_or_group(
        self, entry: Union[MultiPackLink, MultiPackGroup], multi_pack: MultiPack
    ) -> bool:
        r"""
        This function copies a MultiPackLink/MultiPackGroup in the multipack.
        It could be used in tasks such as text generation, where
        MultiPackLink is used to align the source and target.

        Args:
            entry: The MultiPackLink/MultiPackGroup to copy.
            multi_pack: The multi_pack contains the input entry.

        Returns:
            A bool value indicating whether the copy happens.
        """
        # The entry should be either MultiPackLink or MultiPackGroup.
        is_link: bool = isinstance(entry, BaseLink)
        children: List[Entry]
        if is_link:
            children = [entry.get_parent(), entry.get_child()]  # type: ignore
        else:
            children = entry.get_members()  # type: ignore

        # Get the copied children entries.
        new_children: List[Entry] = []
        for child_entry in children:
            child_pack: DataPack = child_entry.pack
            child_pack_pid: int = child_pack.pack_id
            # The new pack should be present.
            if (
                child_pack_pid not in self._data_pack_map
                or child_pack_pid not in self._entry_maps
            ):
                return False
            new_child_pack: DataPack = multi_pack.get_pack_at(
                multi_pack.get_pack_index(self._data_pack_map[child_pack_pid])
            )
            # The new child entry should be present.
            if child_entry.tid not in self._entry_maps[child_pack_pid]:
                return False
            new_child_tid: int = self._entry_maps[child_pack_pid][
                child_entry.tid
            ]
            new_child_entry: Entry = new_child_pack.get_entry(new_child_tid)
            new_children.append(new_child_entry)

        # Create the new entry and add to the multi pack.
        new_entry: Entry
        if is_link:
            entry = cast(MultiPackLink, entry)

            new_link_parent, new_link_child = new_children

            new_entry = type(entry)(
                multi_pack, new_link_parent, new_link_child  # type: ignore
            )
        else:
            entry = cast(MultiPackGroup, entry)
            new_entry = type(entry)(multi_pack, new_children)  # type: ignore
        multi_pack.add_entry(new_entry)
        return True

    def _clear_states(self):
        r"""
        This function clears the states. It should be
        called after processing a multipack.
        """
        self.replacement_op.clear_states()
        self._data_pack_map.clear()
        self._entry_maps.clear()

    def _augment(
        self, input_pack: MultiPack, aug_pack_names: List[str]
    ) -> bool:
        r"""
        This function calls the data augmentation ops and
        modifies the input in-place. The subclasses should override
        this function to implement other data augmentation methods, such
        as Easy Data Augmentation.

        Args:
            input_pack: The input MultiPack.
            aug_pack_names: The packs names for DataPacks to be augmented.

        Returns:
            A boolean value indicating if the data augmentation was
            sucessful or not.
        """
        try:
            self.replacement_op = create_class_with_kwargs(
                self.configs["data_aug_op"],
                class_args={"configs": self.configs["data_aug_op_config"]},
            )

            for pack_name in aug_pack_names:
                data_pack: DataPack = input_pack.get_pack(pack_name)
                augmented_data_pack = self.replacement_op.perform_augmentation(
                    data_pack
                )
                self.new_data_packs[data_pack.pack_id] = augmented_data_pack

            (
                self._data_pack_map,
                self._entry_maps,
            ) = self.replacement_op.get_maps()
            return True
        except:
            return False

    def _process(self, input_pack: MultiPack):
        # Get the pack names for augmentation.
        aug_pack_names: List[str] = []

        # Check if the DataPack exists.
        for pack_name in self.configs["augment_pack_names"].keys():
            if pack_name in input_pack.pack_names:
                aug_pack_names.append(pack_name)

        if len(self.configs["augment_pack_names"].keys()) == 0:
            # Augment all the DataPacks if not specified.
            aug_pack_names = list(input_pack.pack_names)

        success = self._augment(input_pack, aug_pack_names)

        if not success:
            raise ValueError(
                "There was a problem encountered when performing the augmentation in {}".format(
                    self.configs["data_aug_op"]
                )
            )

        new_packs: List[Tuple[str, DataPack]] = []

        for aug_pack_name in aug_pack_names:
            new_pack_name: str = self.configs["augment_pack_names"].get(
                aug_pack_name, "augmented_" + aug_pack_name
            )
            data_pack = input_pack.get_pack(aug_pack_name)

            new_packs.append(
                (new_pack_name, self.new_data_packs[data_pack.pack_id])
            )

        for new_pack_name, new_pack in new_packs:
            input_pack.add_pack_(new_pack, new_pack_name)

        # Copy the MultiPackLinks/MultiPackGroups
        for mpl in input_pack.get(MultiPackLink):
            self._copy_multi_pack_link_or_group(mpl, input_pack)
        for mpg in input_pack.get(MultiPackGroup):
            self._copy_multi_pack_link_or_group(mpg, input_pack)

        # Must be called after processing each multipack
        # to reset internal states.
        self._clear_states()

    @classmethod
    def default_configs(cls):
        """
        Returns:
            A dictionary with the default config for this processor.
        Following are the keys for this dictionary:
            - type:
                Should not modify this field, in order to use the kwargs.
            - data_aug_op:
                The data augmentation Op for the processor.
                It should be a full qualified class name.
                Example:
                    "forte.processors.data_augment.algorithms.
                    text_replacement_op.TextReplacementOp"
            - data_aug_op_config:
                The configuration for data augmentation Op.
                Example:
                    .. code-block:: python
                        'data_aug_op_config': {
                            'lang': 'en',
                            'use_gpu': False,
                            'other_entry_policy': {
                                'ft.onto.base_ontology.Document': 'auto_align',
                                'ft.onto.base_ontology.Sentence': 'auto_align',
                            }
                        }
            - augment_pack_names:
                A dict specifies the DataPacks to augment and their output
                names. It should be key-value pairs where the key is the
                input DataPack name, and the value is the output DataPack
                name after augmentation.
                If empty, all the DataPacks will be augmented, and the output
                names will be automatically generated by prepending
                an `'augmented_'` prefix.
                Example:
                    .. code-block:: python
                        'data_aug_op_config': {
                            'src': 'aug_src',
                            'tgt': 'aug_tgt'
                        }
        """
        return {
            "type": "data_augmentation_op",
            "data_aug_op": "",
            "data_aug_op_config": {},
            "augment_pack_names": {},
            "@no_typecheck": [
                "data_aug_op_config",
                "augment_pack_names",
            ],
        }
