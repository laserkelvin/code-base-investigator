# Copyright (C) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
"""
Contains classes and functions related to parsing a file,
and building a tree of nodes from it.
"""

from os.path import splitext

from . import preprocessor  # pylint : disable=no-name-in-module

from codebasin.c_source import get_file_source

class LineGroup:
    """
    Represents a grouping of lines. It contains the extent, and the
    number of countable lines for the group.
    """

    def __init__(self):
        self.line_count = 0
        self.start_line = -1
        self.end_line = -1

    def empty(self):
        """
        Return a boolean that tells if this group contains any line
        information or not.
        """
        if (self.line_count != 0) or (self.start_line != -1) or (self.end_line != -1):
            return False
        return True

    def add_line(self, phys_int, sloc_count):
        """
        Add a line to this line group. Update the extent appropriately,
        and if it's a countable line, add it to the line count.
        """

        if self.start_line == -1 or phys_int[0] < self.start_line:
            self.start_line = phys_int[0]

        if phys_int[1]-1 > self.end_line:
            self.end_line = phys_int[1]-1

        self.line_count += sloc_count
    def reset(self):
        """
        Reset the countable group
        """
        self.line_count = 0
        self.start_line = -1
        self.end_line = -1

    def merge(self, line_group):
        """
        Merge another line group into this line group, and reset the
        other group.
        """
        self.line_count += line_group.line_count

        if self.start_line == -1:
            self.start_line = line_group.start_line
        elif line_group.start_line == -1:
            line_group.start_line = self.start_line
        self.start_line = min(self.start_line, line_group.start_line)

        self.end_line = max(self.end_line, line_group.end_line)
        line_group.reset()

class FileParser:
    """
    Contains methods for parsing an entire source file and returning a
    source tree object, along with utility methods for determining
    information about source lines and helping to build the source tree.
    """

    def __init__(self, _filename):
        self._filename = _filename

        split = splitext(_filename)
        if len(split) == 2:
            self._file_extension = split[1].lower()
        else:
            self._file_extension = None

    @staticmethod
    def handle_directive(out_tree, groups, logical_line):
        """
        Handle inserting code and directive nodes, where appropriate.
        Update the file group, and reset the code and directive groups.
        """
        # We will actually use this directive, if it is not empty
        # We need to finalize the previously started
        # CodeNode (if there was one) before processing
        # this DirectiveNode
        if not groups['code'].empty():
            FileParser.insert_code_node(out_tree, groups['code'])
            groups['file'].merge(groups['code'])

        FileParser.insert_directive_node(out_tree, groups['directive'], logical_line)

        groups['file'].merge(groups['directive'])

    @staticmethod
    def insert_code_node(tree, line_group):
        """
        Build a code node, and insert it into the source tree
        """
        new_node = preprocessor.CodeNode(
            line_group.start_line, line_group.end_line, line_group.line_count)
        tree.insert(new_node)

    @staticmethod
    def insert_directive_node(tree, line_group, logical_line):
        """
        Build a directive node by parsing a directive line, and insert a
        new directive node into the tree.
        """
        new_node = preprocessor.DirectiveParser(preprocessor.Lexer(
            logical_line, line_group.start_line).tokenize()).parse()
        new_node.start_line = line_group.start_line
        new_node.end_line = line_group.end_line
        new_node.num_lines = line_group.line_count
        tree.insert(new_node)

    def parse_file(self):
        """
        Parse the file that this parser points at, build a SourceTree
        representing this file, and return it.
        """

        out_tree = preprocessor.SourceTree(self._filename)
        file_source = get_file_source(path)
        if not file_source:
            raise RuntimeError(f"{path} doesn't appear to be a language this tool can process")
        with open(self._filename, mode='r', errors='replace') as source_file:
            previous_continue = False

            groups = {'code': LineGroup(),
                      'directive': LineGroup(),
                      'file': LineGroup()
                      }

            groups['file'].start_line = 1

            source = file_source(source_file)
            try:
                while True:
                    (phys_int, local_sloc, logical_line, line_cat) = next(source)
                    # Only follow continuation for directives
                    if line_cat == 'CPP_DIRECTIVE':
                        # Add this into the directive lines, even if it
                        # might not be a directive we count
                        groups['directive'].add_line(phys_int, local_sloc)

                        FileParser.handle_directive(out_tree, groups, logical_line)

                        # FallBack is that this line is a simple code line.
                    else:
                        groups['code'].add_line(phys_int, local_sloc)
            except StopIteration as it:
                total_sloc, physical_loc = it.value

            if not groups['code'].empty():
                groups['code'].add_line((groups['code'].start_line, physical_loc-1), 0)
                self.insert_code_node(out_tree, groups['code'])
                groups['file'].merge(groups['code'])

            out_tree.root.num_lines = groups['file'].end_line
            out_tree.root.total_sloc = groups['file'].line_count
            return out_tree
