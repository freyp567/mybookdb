# adapted from django-yarn 
import os
import subprocess
from fnmatch import fnmatch

from django.contrib.staticfiles import utils as django_utils
from django.contrib.staticfiles.finders import FileSystemFinder
from django.core.files.storage import FileSystemStorage
from django.conf import settings

import logging
LOGGER = logging.getLogger(name='mybookdb.finders')

from collections import OrderedDict

LOGGER.info("using yarn finder")

def yarn_add():
    yarn_executable_path = getattr(settings, 'YARN_EXECUTABLE_PATH', 'yarn')
    command = [yarn_executable_path, 'add', '--prefix=' + get_yarn_root_path()]
    LOGGER.info("yarn exec: %s", command)
    proc = subprocess.Popen(
        command,
        env={'PATH': os.environ.get('PATH')},
    )
    proc.wait()


def get_yarn_root_path():
    return getattr(settings, 'YARN_ROOT_PATH', '.')


def flatten_patterns(patterns):
    if patterns is None:
        return None
    return [
        os.path.join(module, module_pattern)
        for module, module_patterns in patterns.items()
        for module_pattern in module_patterns
    ]


def fnmatch_sub(directory, pattern):
    """
    Match a directory against a potentially longer pattern containing
    wildcards in the path components. fnmatch does the globbing, but there
    appears to be no built-in way to match only the beginning of a pattern.
    """
    length = len(directory.split(os.sep))
    components = pattern.split(os.sep)[:length]
    return fnmatch(directory, os.sep.join(components))


def may_contain_match(directory, patterns):
    return any(fnmatch_sub(directory, pattern) for pattern in patterns)


def get_files(storage, match_patterns='*', ignore_patterns=None, location=''):
    if ignore_patterns is None:
        ignore_patterns = []
    if match_patterns is None:
        match_patterns = []

    if not os.path.isdir(storage.path(location)):
        return

    LOGGER.debug("yarn get_files: %s", location)
    directories, files = storage.listdir(location)
    for fn in files:
        if django_utils.matches_patterns(fn, ignore_patterns):
            continue
        if location:
            fn = os.path.join(location, fn)
        if not django_utils.matches_patterns(fn, match_patterns):
            continue
        LOGGER.info("yarn file: %s", fn)
        yield fn
    for dir in directories:
        if django_utils.matches_patterns(dir, ignore_patterns):
            continue
        if location:
            dir = os.path.join(location, dir)
        LOGGER.debug("yarn subdir: %s", dir)
        if may_contain_match(dir, match_patterns) or django_utils.matches_patterns(dir, match_patterns):
            for fn in get_files(storage, match_patterns, ignore_patterns, dir):
                yield fn


class YarnFinder(FileSystemFinder):
    def __init__(self, apps=None, *args, **kwargs):
        self.node_modules_path = get_yarn_root_path()
        self.destination = getattr(settings, 'YARN_STATIC_FILES_PREFIX', '')
        self.cache_enabled = getattr(settings, 'YARN_FINDER_USE_CACHE', True)
        self.cached_list = None

        self.match_patterns = flatten_patterns(getattr(settings, 'YARN_FILE_PATTERNS', None)) or ['*']
        self.locations = [(self.destination, os.path.join(self.node_modules_path, 'node_modules'))]
        self.storages = OrderedDict()

        filesystem_storage = FileSystemStorage(location=self.locations[0][1])
        filesystem_storage.prefix = self.locations[0][0]
        self.storages[self.locations[0][1]] = filesystem_storage

    def find(self, path, all=False):
        relpath = os.path.relpath(path, self.destination)
        if not django_utils.matches_patterns(relpath, self.match_patterns):
            return []
        return super(YarnFinder, self).find(path, all=all)

    def list(self, ignore_patterns=None):  # TODO should be configurable, add setting
        """List all files in all locations."""
        if self.cache_enabled:
            if self.cached_list is None:
                self.cached_list = list(self._make_list_generator(ignore_patterns))
            return self.cached_list
        return self._make_list_generator(ignore_patterns)

    def _make_list_generator(self, ignore_patterns=None):
        for prefix, root in self.locations:
            storage = self.storages[root]
            for path in get_files(storage, self.match_patterns, ignore_patterns):
                yield path, storage
