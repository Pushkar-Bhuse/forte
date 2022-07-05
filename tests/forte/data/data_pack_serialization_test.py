import json
import os
import tempfile
import unittest

from forte.data import DataPack
from forte.processors.misc import WhiteSpaceTokenizer
from ft.onto.base_ontology import Dependency, Token, EntityMention, CoreferenceGroup


class DataPackSerializationTest(unittest.TestCase):
    def setUp(self):
        # During this setup, we will add many entries
        # into some data packs and try to check serialization.
        self._data_dir = tempfile.TemporaryDirectory()

    def create_datapack(self, pack_name) -> DataPack:
        pack = DataPack(pack_name)
        pack.set_text(
            "This is a test pack . Now we are adding some text to it ."
        )

        # Create some annotations.
        tokenizer = WhiteSpaceTokenizer()
        tokenizer.process(pack)

        # # Add some link.
        # tokens = list(pack.get(Token))
        # token_this = tokens[0]
        # token_is = tokens[1]
        # Dependency(pack, token_is, token_this).dep_label = "nsubj"
        #
        # # Add some mention and coref group.
        # mention_this = EntityMention(pack, 0, 4)
        # mention_pack = EntityMention(pack, 8, 19)
        # mention_it = EntityMention(pack, 54, 56)
        #
        # CoreferenceGroup(pack, [mention_this, mention_pack, mention_it])

        pack.add_all_remaining_entries()
        return pack

    def test_datapack_format(self):
        pack1 = self.create_datapack("test_pack1")

        output_path = os.path.join(self._data_dir.name, pack1.pack_name + ".json")

        with open(output_path, "wt") as f:
            pack_json = json.loads(pack1.to_string(indent=2, json_method="jsonpickle"))
            # pack_json["py/state"]["_data_store"] = []
            f.write(pack1.to_string(indent=2, json_method="jsonpickle"))

        with open(output_path) as f:
            json_format = json.load(f)
            # This will fail since `TextPayload` is not integrated directly with DataStore.
            self.assertEqual(
                json_format["py/state"]["_data_store"]["py/state"]["entries"]["forte.data.ontology.top.TextPayload"][-1],
                "This is a test pack . Now we are adding some text to it ."
            )

    def tearDown(self):
        # self._data_dir.cleanup()
        pass
