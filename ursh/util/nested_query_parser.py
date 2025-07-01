import re

from webargs.flaskparser import FlaskParser


class NestedQueryParser(FlaskParser):
    def load_querystring(self, req, schema):
        return _structure_dict(req.args)


# Taken from the sample custom parser on http://webargs.readthedocs.io/en/latest/advanced.html#custom-parsers
def _structure_dict(dict_):
    def structure_dict_pair(r, key, value):
        m = re.match(r'(\w+)\.(.*)', key)
        if m:
            if r.get(m.group(1)) is None:
                r[m.group(1)] = {}
            structure_dict_pair(r[m.group(1)], m.group(2), value)
        else:
            r[key] = value
    r = {}
    for k, v in dict_.items():
        structure_dict_pair(r, k, v)
    return r
