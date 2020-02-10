"""
A broken line looks like:

  metadata {"uuid":"dc77ee5b-ffe6-45c5-b7e ...

A correct line looks like

  {"uuid":"dc77ee5b-ffe6-45c5-b7e ...

"""

import json
import logging
import re


logger = logging.getLogger(__name__)
json_extract_re = re.compile(rb'^(.+?)\{(.+)\}(.?)$')


def json_fixer(line, iteration=0):
    """A naive JSON line fixer.

    This function may be easily optimized if needed,
    by replacing json.loads() with regexp-based matching.
    """
    ret = None

    try:
        json.loads(line)
    except (TypeError, ValueError, IndexError):
        # Never attempt fixing JSON more than once.
        if iteration == 0:
            json_extracted = json_extract_re.search(line)
            if json_extracted:
                ret = json_fixer(
                    b'{' + json_extracted.groups()[1] + b'}\n',
                    iteration=1,
                )
        elif iteration == 1:
            # Probably there is no closing "}
            ret = json_fixer(line + b'"}', iteration=2)
        else:
            logger.warning('Skipping irrecoverable line: %s', line)

    else:
        ret = line

    return ret
