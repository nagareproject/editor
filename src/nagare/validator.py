# --
# Copyright (c) 2008-2023 Net-ng.
# All rights reserved.
#
# This software is licensed under the BSD License, as described in
# the file LICENSE.txt, which you should have received as part of
# this distribution.
# --

"""Set of validating objects.

Suitable to be the validating functions of ``editor.property`` objects
"""

import re
import sys
import functools

from nagare import i18n

_L = functools.partial(i18n._L, domain='nagare')

_marker = object()


class DualCallable(type):
    """A hackish metaclass to allow both direct and deferred calls of methods.

    For compatibility with the old and new way to built a validation chain.

    Examples:
      - Old validation with direct calls: valid = lambda v: IntValidator(v).greater_than(10).to_int()
      - New validation with lazy calls: valid = IntValidator().greater_than(10)
    """

    def __new__(cls, name, bases, ns):
        """Class Initialization.

        Create a dual class too

        In:
          - ``name`` -- name of the class to create
          - ``bases`` -- base classes of the class to create
          - ``ns`` -- namespace of the class to create

        Return:
          - a new class
        """
        validator = super().__new__(cls, name, bases, ns)

        ns = {
            method_name: (
                lambda method: functools.wraps(method)(lambda self, *args, **kw: self._defer_call(method, args, kw))
            )(method)
            for method_name, method in ns.items()
            if callable(method) and not method_name.startswith('_')
        }
        ns['_dual'] = validator

        validator._dual = super().__new__(cls, name + 'Dual', (DualValidator,), ns)
        setattr(sys.modules[validator.__module__], name + 'Dual', validator._dual)

        return validator


class DualValidator:
    _dual = None

    def __init__(self):
        self._calls = []

    def _defer_call(self, method, args, kw):
        self._calls.append((method, args, kw))
        return self

    def __call__(self, value):
        validator = self._dual(value)
        for f, args, kw in self._calls:
            f(validator, *args, **kw)

        return validator()


class Validator(metaclass=DualCallable):
    """Base class for the validation objects."""

    def __new__(cls, v=_marker, *args, **kw):
        return super().__new__(cls) if v is not _marker else cls._dual()

    def __init__(self, v, strip=False, rstrip=False, lstrip=False, chars=None, msg=_L('Input must be a string')):
        """Initialization.

        This object only do conversions, possibly removing characters at the
        beginning / end of the value

        In:
          - ``v`` -- value to validate
          - ``strip`` -- remove the characters at the beginning and the end
          - ``rstrip`` -- remove the characters at the end
          - ``lstrip`` -- remove the characters at the beginning
          - ``chars`` -- list of characters to removed, spaces by default
        """
        if not isinstance(v, str):
            raise ValueError(msg)

        if strip:
            v = v.strip(chars)

        if rstrip:
            v = v.rstrip(chars)

        if lstrip:
            v = v.lstrip(chars)

        self.value = v

    def __call__(self):
        return self.value


class IntValidator(Validator):
    """Conversion and validation of integers."""

    def __init__(self, v, base=10, msg=_L('Must be an integer'), *args, **kw):
        """Initialisation.

        Check that the value is an integer

        In:
          - ``v`` -- value to validate
        """
        super(IntValidator, self).__init__(v, *args, **kw)

        try:
            self.value = int(self.value, base)
        except (ValueError, TypeError):
            raise ValueError(msg)

    to_int = Validator.__call__

    def lesser_than(self, max, msg=_L('Must be lesser than %(max)d')):
        """Check that the value is lesser than a limit.

        In:
          - ``max`` -- the limit
          - ``msg`` -- message to raise

        Return:
          - ``self``
        """
        if self.value < max:
            return self

        raise ValueError(msg % {'value': self.value, 'max': max})

    def lesser_or_equal_than(self, max, msg=_L('Must be lesser or equal than %(max)d')):
        """Check that the value is lesser or equal than a limit.

        In:
          - ``max`` -- the limit
          - ``msg`` -- message to raise

        Return:
          - ``self``
        """
        if self.value <= max:
            return self

        raise ValueError(msg % {'value': self.value, 'max': max})

    def greater_than(self, min, msg=_L('Must be greater than %(min)d')):
        """Check that the value is greater than a limit.

        In:
          - ``max`` -- the limit
          - ``msg`` -- message to raise

        Return:
          - ``self``
        """
        if self.value > min:
            return self

        raise ValueError(msg % {'value': self.value, 'min': min})

    def greater_or_equal_than(self, min, msg=_L('Must be greater or equal than %(min)d')):
        """Check that the value is greater or equal than a limit.

        In:
          - ``max`` -- the limit
          - ``msg`` -- message to raise

        Return:
          - ``self``
        """
        if self.value >= min:
            return self

        raise ValueError(msg % {'value': self.value, 'min': min})


class StringValidator(Validator):
    """Conversion and validation of string."""

    to_string = Validator.__call__

    def to_int(self, base=10):
        """Return the value, converted to an integer.

        In:
          - ``base`` -- base for the conversion

        Return:
          - the integer value
        """
        self.value = int(self.value, base=base)
        return self.value

    def not_empty(self, msg=_L("Can't be empty")):
        """Check that the value is not empty.

        In:
          - ``msg`` -- message to raise

        Return:
          - ``self``
        """
        if len(self.value) != 0:
            return self

        raise ValueError(msg)

    def match(self, r, msg=_L('Incorrect format')):
        """Check that the value respects a format given as a regexp.

        In:
          - ``r`` -- the regexp
          - ``msg`` -- message to raise

        Return:
          - ``self``
        """
        if re.match(r, self.value):
            return self

        raise ValueError(msg % {'value': self.value})

    def shorter_than(self, max, msg=_L('Length must be shorter than %(max)d characters')):
        """Check that the value is shorter than a limit.

        In:
          - ``max`` -- the limit
          - ``msg`` -- message to raise

        Return:
          - ``self``
        """
        if len(self.value) < max:
            return self

        raise ValueError(msg % {'value': self.value, 'max': max})

    def shorter_or_equal_than(self, max, msg=_L('Length must be shorter or equal than %(max)d characters')):
        """Check that the value is shorter or equal than a limit.

        In:
          - ``max`` -- the limit
          - ``msg`` -- message to raise

        Return:
          - ``self``
        """
        if len(self.value) <= max:
            return self

        raise ValueError(msg % {'value': self.value, 'max': max})

    def length_equal(self, v, msg=_L('Length must be %(len)d characters')):
        """Check that the value has an exact length.

        In:
          - ``v`` -- the length
          - ``msg`` -- message to raise

        Return:
          - ``self``
        """
        if len(self.value) == v:
            return self

        raise ValueError(msg % {'value': self.value, 'len': v})

    def longer_than(self, min, msg=_L('Length must be longer than %(min)d characters')):
        """Check that the value is longer than a limit.

        In:
          - ``min`` -- the limit
          - ``msg`` -- message to raise

        Return:
          - ``self``
        """
        if len(self.value) > min:
            return self

        raise ValueError(msg % {'value': self.value, 'min': min})

    def longer_or_equal_than(self, min, msg=_L('Length must be longer or equal than %(min)d characters')):
        """Check that the value is longer or equal than a limit.

        In:
          - ``min`` -- the limit
          - ``msg`` -- message to raise

        Return:
          - ``self``
        """
        if len(self.value) >= min:
            return self

        raise ValueError(msg % {'value': self.value, 'min': min})

    def isalnum(self, msg=_L('Some characters are not alphanumeric')):
        if self.value.isalnum():
            return self

        raise ValueError(msg % {'value': self.value})

    def isalpha(self, msg=_L('Some characters are not alphabetic')):
        if self.value.isalpha():
            return self

        raise ValueError(msg % {'value': self.value})

    def isdigit(self, msg=_L('Some characters are not digits')):
        if self.value.isdigit():
            return self

        raise ValueError(msg % {'value': self.value})

    def islower(self, msg=_L('Some characters are not lowercase')):
        if self.value.islower():
            return self

        raise ValueError(msg % {'value': self.value})

    def isupper(self, msg=_L('Some characters are not uppercase')):
        if self.value.isupper():
            return self

        raise ValueError(msg % {'value': self.value})

    def isspace(self, msg=_L('Some characters are not whitespace')):
        if self.value.isspace():
            return self

        raise ValueError(msg % {'value': self.value})


# Aliases
to_int = IntValidator
to_string = StringValidator
