"""
Filesystem helpers that are unit-testable without actually writing to disk.
"""

import os
from os import path

from jinja2.exceptions import TemplateNotFound


class FilesystemInterface:
    """
    Abstract interface without actual implementations.
    """
    def symlink(self, target, linkName):
        """
        ln -sf target linkName
        :param target: path the symlink will point to
        :param linkName: the symlink that will be created
        """
        pass

    def makedirs(self, directory):
        """
        mkdir -p directory
        :param directory: path to the directory with potentially missing parent directories
        """
        pass

    def replaceFileContents(self, fileName, newContents):
        """
        Only replace fileName with newContents if the contents differ from what the file currently contains.
        This avoids changing mtime of the file and thus avoids re-running bricks which haven't actually changed.
        """
        pass


class Filesystem(FilesystemInterface):
    """Actual runtime implementation of FilesystemInterface."""
    def symlink(self, target, linkName):
        if os.path.islink(linkName):
            os.unlink(linkName)
        os.symlink(target, linkName)

    def makedirs(self, directory):
        if not os.path.isdir(directory):
            os.makedirs(directory)

    def replaceFileContents(self, fileName, newContents):
        if os.path.exists(fileName):
            with open(fileName) as fi:
                oldContents = fi.read()
            if oldContents == newContents:
                # no need to update the file
                return

        # create directory if necessary
        if not os.path.exists(os.path.dirname(fileName)):
            os.makedirs(os.path.dirname(fileName))

        with open(fileName, 'w') as fo:
            fo.write(newContents)


class MockFilesystem(FilesystemInterface):
    """Mock implementation of FilesystemInterface that keeps track of calls."""
    def __init__(self):
        self.symlinks = {}  # dict: symlinks[linkName] = target
        self.dirs = set()   # set([dirs...])
        self.files = {}     # dict: files[fileName] = contents

    def symlink(self, target, linkName):
        self.symlinks[linkName] = target

    def makedirs(self, directory):
        self.dirs.add(directory)

    def replaceFileContents(self, fileName, newContents):
        self.files[fileName] = newContents


def normalize_symlinks(symlinks):
    """
    Normalize a dict of symlinks with relative symlink paths to become absolute paths.
    :param symlinks: dict: symlinks[linkName] = target
    """
    def normalize(linkName, target):
        if target.startswith('/'):
            return target  # do not change absolute paths
        return os.path.normpath(os.path.join(os.path.dirname(linkName), target))  # normalize relative paths
    return {linkName: normalize(linkName, target) for linkName, target in symlinks.items()}


# override of the jinja2.loaders version
def unsafe_jinja_split_template_path(template):
    """Split a path into segments and skip jinja2 sanity check for testing."""
    pieces = []
    for piece in template.split('/'):
        if path.sep in piece \
           or (path.altsep and path.altsep in piece):
            # or piece == path.pardir:  # allows '..' in the path, contrary to jinja2 default implementation
            raise TemplateNotFound(template)
        elif piece and piece != '.':
            pieces.append(piece)
    return pieces
