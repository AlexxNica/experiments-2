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

"""A single value (with multiple layers possibly) in the config."""

import collections


class SettingValue:

    """Base class for setting values.

    Intended to be subclassed by config value "types".

    Attributes:
        typ: A BaseType subclass instance.
        value: (readonly property) The currently valid, most important value.
        advanced: Whether to hide the config by default.
        _values: An OrderedDict with the values on different layers, with the
                 most significant layer first.
    """

    def __init__(self, typ, default=None, advanced=False):
        """Constructor.

        Args:
            typ: The BaseType to use.
            default: Raw value to set.
        """
        self.typ = typ
        self.advanced = advanced
        self._values = collections.OrderedDict.fromkeys(
            ['temp', 'conf', 'default'])
        self._values['default'] = default

    def __str__(self):
        """Get raw string value."""
        return self.value

    @property
    def value(self):
        """Get the currently valid value."""
        return self.get_first_value()

    @property
    def default(self):
        """Get the default value."""
        return self._values['default']

    @property
    def values(self):
        """Readonly property for _values."""
        return self._values

    def getlayers(self, startlayer):
        """Get a dict of values starting with startlayer.

        Args:
            startlayer: The first layer to include.
        """
        idx = list(self._values.keys()).index(startlayer)
        d = collections.OrderedDict(list(self._values.items())[idx:])
        return d

    def get_first_value(self, startlayer=None):
        """Get the first valid value starting from startlayer.

        Args:
            startlayer: The first layer to include.
        """
        if startlayer is None:
            d = self._values
        else:
            d = self.getlayers(startlayer)
        for val in d.values():
            if val is not None:
                return val
        else:  # pylint: disable=useless-else-on-loop
            raise ValueError("No valid config value found!")

    def transformed(self):
        """Get the transformed value."""
        v = self.value
        return self.typ.transform(v)

    def setv(self, layer, value, interpolated):
        """Set the value on a layer.

        Args:
            layer: The layer to set the value on, an element name of the
                   ValueLayers dict.
            value: The value to set.
            interpolated: The interpolated value, for typechecking.
        """
        self.typ.validate(interpolated)
        self._values[layer] = value
