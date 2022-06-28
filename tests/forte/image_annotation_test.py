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
Unit tests for ImageAnnotation.
"""
import os
import unittest
import numpy as np
from typing import Dict

from numpy import array_equal
from sortedcontainers import SortedList
from forte.data.ontology.top import ImageAnnotation
from forte.data.data_pack import DataPack
from forte.data.data_store import DataStore
from forte.common import constants


class ImageAnnotationTest(unittest.TestCase):
    """
    Test ImageAnnotation related ontologies like Edge and BoundingBox.
    """

    def setUp(self):
        self.datapack = DataPack("image")
        self.line = np.zeros((6, 12))
        self.line[2, 2] = 1
        self.line[3, 3] = 1
        self.line[4, 4] = 1

        self.reference_type_attributes = {
            "forte.data.ontology.top.BoundingBox": {
                "attributes": {
                    "cx": 4,
                    "cy": 5,
                    "height": 6,
                    "width": 7,
                    "grid_height": 8,
                    "grid_width": 9,
                    "grid_cell_h_idx": 10,
                    "grid_cell_w_idx": 11
                },
                "parent_class": set(),
            },
        }

        self.base_type_attributes = {
            'forte.data.ontology.top.BoundingBox': {'parent_class': {'Box'}},
        }

        DataStore._type_attributes = self.reference_type_attributes

        # The order is [Document, Sentence]. Initialize 2 entries in each list.
        # Document entries have tid 1234, 3456.
        # Sentence entries have tid 9999, 1234567.
        # The type id for Document is 0, Sentence is 1.

        ref1 = [
            1,
            None,
            1234,
            "forte.data.ontology.top.BoundingBox",
            3,
            5,
            1,
            1,
            2,
            2,
            100,
            101
        ]
        ref2 = [
            10,
            None,
            4567,
            "forte.data.ontology.top.ImageAnnotation"
        ]

        self.datapack._data_store._DataStore__elements = {
            "forte.data.ontology.top.BoundingBox": [ref1],
            "forte.data.ontology.core.Entry": SortedList([]),
            "forte.data.ontology.top.ImageAnnotation": [ref2]
        }

        self.datapack._data_store._DataStore__tid_idx_dict = {
            1234: ["forte.data.ontology.top.BoundingBox", 0],
            4567: ["forte.data.ontology.top.ImageAnnotation", 0]
        }

    def test_entry_methods(self):
        box_type = "forte.data.ontology.top.BoundingBox"

        box_list = list(self.datapack._data_store._DataStore__elements[box_type])
        
        box_entries = list(self.datapack._data_store.all_entries(box_type))

        self.assertEqual(box_list, box_entries)
        self.assertEqual(self.datapack._data_store.num_entries(box_type), len(box_list))

    def test_delete_image_annotations(self):

        box_type = "forte.data.ontology.top.BoundingBox"
        box_list = len(list(self.datapack._data_store._DataStore__elements[box_type]))

        self.datapack._data_store.delete_entry(1234)
        self.assertEqual(
            self.datapack._data_store.num_entries(box_type),
            box_list-1
        )

        
    def test_add_image_annotation_raw(self):
        image_tid: int = self.datapack._data_store.add_entry_raw(
            type_name = "forte.data.ontology.top.BoundingBox",
            attribute_data = [25, None],
            base_class = ImageAnnotation
        )

        self.assertEqual(
            len(
                self.datapack._data_store._DataStore__elements[
                    "forte.data.ontology.top.BoundingBox"
                ]
            ),
            2,
        )


if __name__ == "__main__":
    unittest.main()