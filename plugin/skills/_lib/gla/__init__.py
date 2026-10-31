"""Shared helpers for the GLA skills and their tools.

Scripts add Skills/_lib to sys.path from their own realpath, so symlinked
skills still find it:

    sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "_lib"))
    from gla import course, slots

Needs Python 3.8+ and PyYAML.
"""
