# vim: ft=python fileencoding=utf-8 sts=4 sw=4 et:

# Copyright 2014 Florian Bruhin (The Compiler) <mail@qutebrowser.org>
#
# This file is part of qutebrowser.
#
# qutebrowser is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# qutebrowser is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with qutebrowser.  If not, see <http://www.gnu.org/licenses/>.

"""Our own fork of shlex.split with some added and removed features."""

from qutebrowser.utils import log


class ShellLexer:

    """A lexical analyzer class for simple shell-like syntaxes.

    Based on Python's shlex, but cleaned up, removed some features, and added
    some features useful for qutebrowser.

    Attributes:
        FIXME
    """

    def __init__(self, s):
        self.string = s
        self.whitespace = ' \t\r'
        self.quotes = '\'"'
        self.escape = '\\'
        self.escapedquotes = '"'
        self.keep = False
        self.placeholder = False

    def reset(self):
        self.quoted = False
        self.escapedstate = ' '
        self.token = ''
        self.state = ' '

    def __iter__(self):
        """Read a raw token from the input stream."""
        self.reset()
        for nextchar in self.string:
            log.shlexer.vdebug("in state {!r} I see character: {!r}".format(
                self.state, nextchar))
            if self.state == ' ':
                if self.keep and not self.placeholder:
                    self.token += nextchar
                if nextchar in self.whitespace:
                    if self.placeholder:
                        self.token += nextchar
                    log.shlexer.vdebug("I see whitespace in whitespace state")
                    if self.token or self.quoted:
                        yield self.token
                        self.reset()
                elif nextchar in self.escape:
                    self.escapedstate = 'a'
                    self.state = nextchar
                elif nextchar in self.quotes:
                    if self.placeholder:
                        self.token += nextchar
                    self.state = nextchar
                else:
                    if self.placeholder:
                        self.token = '{}'
                    else:
                        self.token = nextchar
                    self.state = 'a'
            elif self.state in self.quotes:
                self.quoted = True
                if nextchar == self.state:
                    if self.placeholder:
                        self.token += '{}'
                    if self.keep:
                        self.token += nextchar
                    self.state = 'a'
                elif (nextchar in self.escape and
                        self.state in self.escapedquotes):
                    if self.keep and not self.placeholder:
                        self.token += nextchar
                    self.escapedstate = self.state
                    self.state = nextchar
                elif not self.placeholder:
                    self.token += nextchar
            elif self.state in self.escape:
                # In posix shells, only the quote itself or the escape
                # character may be escaped within quotes.
                if (self.escapedstate in self.quotes and
                        nextchar != self.state and
                        nextchar != self.escapedstate and not self.keep):
                    self.token += self.state
                if not self.placeholder:
                    self.token += nextchar
                self.state = self.escapedstate
            elif self.state == 'a':
                if nextchar in self.whitespace:
                    log.shlexer.vdebug("shlex: I see whitespace in word state")
                    self.state = ' '
                    if self.token or self.quoted:
                        yield self.token
                        self.reset()
                    if self.keep:
                        yield nextchar
                elif nextchar in self.quotes:
                    if self.keep:
                        self.token += nextchar
                    self.state = nextchar
                elif nextchar in self.escape:
                    if self.keep and not self.placeholder:
                        self.token += nextchar
                    self.escapedstate = 'a'
                    self.state = nextchar
                elif not self.placeholder:
                    self.token += nextchar
        if self.state in self.escape and not self.keep:
            self.token += self.state
        if self.token or self.quoted:
            yield self.token


def split(s, keep=False, placeholder=False):
    """Split a string via ShellLexer.

    Args:
        keep: Whether to keep are special chars in the split output.
        placeholder: Whether to generate placeholder strings.
    """
    lexer = ShellLexer(s)
    if placeholder:
        lexer.placeholder = True
        lexer.keep = True
    else:
        lexer.keep = keep
    tokens = list(lexer)
    if not tokens:
        return []
    out = []
    spaces = ""

    log.shlexer.vdebug("{!r} -> {!r}".format(s, tokens))

    for t in tokens:
        if t.isspace():
            spaces += t
        else:
            out.append(spaces + t)
            spaces = ""
    if spaces:
        out.append(spaces)

    return out
