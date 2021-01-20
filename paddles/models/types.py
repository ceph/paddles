import json
from copy import deepcopy
from sqlalchemy import types as SATypes


class JSONType(SATypes.TypeDecorator):
    impl = SATypes.UnicodeText

    def process_bind_param(self, value, engine):
        return json.dumps(value)

    def process_result_value(self, value, engine):
        if value:
            return json.loads(value)
        else:
            return {}  # pragma: nocover

    def copy_value(self, value):
        return deepcopy(value)
