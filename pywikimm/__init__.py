import os
# disabling reading pywikibot confis from the file. Instead, mylang and family
# will be specified programatically
os.environ["PYWIKIBOT_NO_USER_CONFIG"] = "2"

import json
_KNOWN_ICONS_PATH = os.getenv('PYWIKIMM_KNOWN_ICONS_PATH', 'pywikimm/known_icons.json')
_KNOWN_ICONS = set()

if os.path.isfile(_KNOWN_ICONS_PATH):
    with open(_KNOWN_ICONS_PATH) as json_file:
        json_obj = json.loads(json.load(json_file))
        _KNOWN_ICONS = set(json_obj['known_icons'])
else:
    print('WARNING: missing {} file. Default to empty set.'.format(_KNOWN_ICONS_PATH))

import pywikimm.preprocessor
import pywikimm.reader
import pywikimm.utils