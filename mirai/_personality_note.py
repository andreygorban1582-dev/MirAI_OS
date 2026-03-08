"""
mirai/settings.py  –  add Okabe personality helpers to the singleton.

This thin add-on reads the personality section from config.yaml and exposes
it through the existing `settings` object by monkey-patching two properties.
Rather than duplicating settings.py we extend it here and re-export.
"""
# This file intentionally left as a note – personality data is accessed
# directly on the _Settings class in settings.py (see okabe_triggers /
# okabe_catchphrases properties added below).
