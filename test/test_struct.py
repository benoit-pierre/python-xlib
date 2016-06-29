#!/usr/bin/env python2

from collections import OrderedDict
from functools import partial
import struct
import types
import re

from six import binary_type

from Xlib.protocol import rq
from . import DummyDisplay, TestCase


dummy_display = DummyDisplay()

def pack(format, *args):
    return struct.pack('=' + format, *args)

def packstr(s, padding=0):
    return s.encode() + (b'\0' * padding)


class StructTest(object):

    struct = None
    values = None
    binary = None

    def test_pack_value_dict(self):
        self.assertBinaryEqual(self.struct.pack_value(dict(self.values)), self.binary)

    def test_pack_value_tuple(self):
        self.assertBinaryEqual(self.struct.pack_value(tuple(self.values.values())), self.binary)

    def test_to_binary_args(self):
        self.assertBinaryEqual(self.struct.to_binary(*self.values.values()), self.binary)

    def test_to_binary_kwargs(self):
        self.assertBinaryEqual(self.struct.to_binary(**dict(self.values)), self.binary)

    def test_parse_binary(self):
        values, remain = self.struct.parse_binary(self.binary, dummy_display)
        self.assertEqual(values, rq.DictWrapper(dict(self.values)))
        self.assertBinaryEmpty(remain)


def _struct_test(name, fields):
    class_name = ''.join([part.capitalize() for part in re.sub(r'[^\w]+', ' ', name).split()])
    class_name += 'StructTest'
    struct_layout = []
    values = OrderedDict()
    binary = b''
    for name, rq_type, val, bin in fields:
        struct_layout.append(rq_type(name))
        if name is not None and val is not None:
            values[name] = val
        if isinstance(bin, binary_type):
            binary += bin
        elif isinstance(bin, (types.FunctionType, types.LambdaType, partial)):
            binary += bin(val)
        else:
            raise ValueError('unsupported type for binary: %s [%s]' % (str(bin), type(bin)))
    class_dict = {
        'struct': rq.Struct(*struct_layout),
        'values': values,
        'binary': binary,
    }
    globals()[class_name] = type(class_name, (StructTest, TestCase), class_dict)


_struct_test('card', (
    ('c8' , rq.Card8 , 0x42      , partial(pack, 'B')),
    ('c16', rq.Card16, 0x666     , partial(pack, 'H')),
    ('c32', rq.Card32, 0xdeadbeef, partial(pack, 'L')),
))

_struct_test('int', (
    ('i8' , rq.Int8 , -42        , partial(pack, 'b')),
    ('i16', rq.Int16, -666       , partial(pack, 'h')),
    ('i32', rq.Int32, -2147483648, partial(pack, 'l')),
))

_struct_test('list', (
    (None   , lambda name: rq.LengthOf('lc8', 1)          , None                                   , pack('B', 2)              ),
    (None   , lambda name: rq.LengthOf('lc16', 2)         , None                                   , pack('H', 3)              ),
    (None   , lambda name: rq.LengthOf('lc32', 4)         , None                                   , pack('L', 5)              ),
    ('lc8'  , lambda name: rq.List(name, rq.Card8 , pad=0), [0x42, 0xc3]                           , lambda v: pack('2B'  , *v)),
    ('lc16' , lambda name: rq.List(name, rq.Card16, pad=0), [666, 1, 60143]                        , lambda v: pack('3H'  , *v)),
    ('lc32' , lambda name: rq.List(name, rq.Card32, pad=0), [0xf02facb, 666, 1, 0x1043, 0xdeadbeef], lambda v: pack('5L'  , *v)),
))

_struct_test('list pad', (
    (None   , lambda name: rq.LengthOf('lc8', 1)          , None                                   , pack('B', 2)              ),
    (None   , lambda name: rq.LengthOf('lc16', 2)         , None                                   , pack('H', 3)              ),
    (None   , lambda name: rq.LengthOf('lc32', 4)         , None                                   , pack('L', 5)              ),
    ('lc8'  , lambda name: rq.List(name, rq.Card8 , pad=1), [0x42, 0xc3]                           , lambda v: pack('2B2x', *v)),
    ('lc16' , lambda name: rq.List(name, rq.Card16, pad=1), [666, 1, 60143]                        , lambda v: pack('3H2x', *v)),
    ('lc32' , lambda name: rq.List(name, rq.Card32, pad=1), [0xf02facb, 666, 1, 0x1043, 0xdeadbeef], lambda v: pack('5L'  , *v)),
))

_struct_test('fixed list', (
    ('lc8'  , lambda name: rq.FixedList(name, 2, rq.Card8 , pad=0), [0x42, 0xc3]                           , lambda v: pack('2B'  , *v)),
    ('lc16' , lambda name: rq.FixedList(name, 3, rq.Card16, pad=0), [666, 1, 60143]                        , lambda v: pack('3H'  , *v)),
    ('lc32' , lambda name: rq.FixedList(name, 5, rq.Card32, pad=0), [0xf02facb, 666, 1, 0x1043, 0xdeadbeef], lambda v: pack('5L'  , *v)),
))

_struct_test('fixed list pad', (
    ('lc8p' , lambda name: rq.FixedList(name, 2, rq.Card8 , pad=1), [0x42, 0xc3]                           , lambda v: pack('2B2x', *v)),
    ('lc16p', lambda name: rq.FixedList(name, 3, rq.Card16, pad=1), [666, 1, 60143]                        , lambda v: pack('3H2x', *v)),
    ('lc32p', lambda name: rq.FixedList(name, 5, rq.Card32, pad=1), [0xf02facb, 666, 1, 0x1043, 0xdeadbeef], lambda v: pack('5L'  , *v)),
))

_struct_test('string8', (
    (None, lambda name: rq.LengthOf('s1', 1)   , None                                , pack('B', 7) ),
    (None, lambda name: rq.LengthOf('s2', 2)   , None                                , pack('H', 13)),
    (None, lambda name: rq.LengthOf('s3', 4)   , None                                , pack('L', 34)),
    ('s1', lambda name: rq.String8(name, pad=0), "testing"                           , packstr      ),
    ('s2', lambda name: rq.String8(name, pad=0), "one two three"                     , packstr      ),
    ('s3', lambda name: rq.String8(name, pad=0), "supercalifragilisticexpialidocious", packstr      ),
))

_struct_test('string8 pad', (
    (None, lambda name: rq.LengthOf('s1', 1)   , None                                , pack('B', 7)               ),
    (None, lambda name: rq.LengthOf('s2', 2)   , None                                , pack('H', 13)              ),
    (None, lambda name: rq.LengthOf('s3', 4)   , None                                , pack('L', 34)              ),
    ('s1', lambda name: rq.String8(name, pad=1), "testing"                           , partial(packstr, padding=1)),
    ('s2', lambda name: rq.String8(name, pad=1), "one two three"                     , partial(packstr, padding=3)),
    ('s3', lambda name: rq.String8(name, pad=1), "supercalifragilisticexpialidocious", partial(packstr, padding=2)),
))

_struct_test('binary', (
    (None, lambda name: rq.LengthOf('s1', 1)  , None                                 , pack('B', 7) ),
    (None, lambda name: rq.LengthOf('s2', 2)  , None                                 , pack('H', 13)),
    (None, lambda name: rq.LengthOf('s3', 4)  , None                                 , pack('L', 34)),
    ('s1', lambda name: rq.Binary(name, pad=0), b"testing"                           , lambda v: v),
    ('s2', lambda name: rq.Binary(name, pad=0), b"one two three"                     , lambda v: v),
    ('s3', lambda name: rq.Binary(name, pad=0), b"supercalifragilisticexpialidocious", lambda v: v),
))

_struct_test('binary pad', (
    (None, lambda name: rq.LengthOf('s1', 1)  , None                                 , pack('B', 7) ),
    (None, lambda name: rq.LengthOf('s2', 2)  , None                                 , pack('H', 13)),
    (None, lambda name: rq.LengthOf('s3', 4)  , None                                 , pack('L', 34)),
    ('s1', lambda name: rq.Binary(name, pad=1), b"testing"                           , lambda v: v + b'\0' * 1),
    ('s2', lambda name: rq.Binary(name, pad=1), b"one two three"                     , lambda v: v + b'\0' * 3),
    ('s3', lambda name: rq.Binary(name, pad=1), b"supercalifragilisticexpialidocious", lambda v: v + b'\0' * 2),
))

_struct_test('fixed binary', (
    ('s1', lambda name: rq.FixedBinary(name, 7 ), b"testing"                           , lambda v: v),
    ('s2', lambda name: rq.FixedBinary(name, 13), b"one two three"                     , lambda v: v),
    ('s3', lambda name: rq.FixedBinary(name, 34), b"supercalifragilisticexpialidocious", lambda v: v),
    # Make sure fixed binary fields are handled as static fields.
    ('c8', rq.Card8, 0x42, partial(pack, 'B')),
))
