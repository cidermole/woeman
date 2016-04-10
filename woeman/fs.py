"""
Filesystem helpers that are unit-testable without actually writing to disk.
"""

import os


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


class Filesystem(FilesystemInterface):
    """Actual runtime implementation of FilesystemInterface."""
    def symlink(self, target, linkName):
        if os.path.islink(linkName):
            os.unlink(linkName)
        os.symlink(target, linkName)

    def makedirs(self, directory):
        os.makedirs(directory)
