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
