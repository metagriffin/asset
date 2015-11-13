# -*- coding: utf-8 -*-
#------------------------------------------------------------------------------
# file: $Id$
# auth: metagriffin <mg.github@uberdev.org>
# date: 2013/09/22
# copy: (C) Copyright 2013-EOT metagriffin -- see LICENSE.txt
#------------------------------------------------------------------------------
# This software is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This software is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see http://www.gnu.org/licenses/.
#------------------------------------------------------------------------------

import unittest
import os.path
import xml.etree.ElementTree as ET

import pxml
import six
import pkg_resources
from aadict import aadict

import asset

#------------------------------------------------------------------------------
def isEgg(pkg):
  dist = pkg_resources.get_distribution(pkg)
  return os.path.isfile(dist.location)

#------------------------------------------------------------------------------
class TestAsset(unittest.TestCase, pxml.XmlTestMixin):

  maxDiff = None

  #----------------------------------------------------------------------------
  def test_version(self):
    self.assertRegexpMatches(asset.version('pxml'), r'^\d+.\d+.\d+$')

  #----------------------------------------------------------------------------
  def test_load_multi(self):
    self.assertEqual(len(asset.load('asset:test/data/file1.nl')), 1)
    self.assertEqual(
      [str(ast) for ast in asset.load('asset:test/data/file1.nl')],
      ['asset:test/data/file1.nl'])
    self.assertEqual(
      [str(ast) for ast in asset.load('asset:test/data/**.nl')],
      ['asset:test/data/file1.nl',
       'asset:test/data/file2.nl',
       'asset:test/data/subdir/subfile1.nl'])
    self.assertEqual(
      [ast.read() for ast in asset.load('asset:test/data/**.nl')],
      [b'line-1\nline-2',
       b'line-3\n',
       b'sub-file-line-1\n'])

  #----------------------------------------------------------------------------
  def test_load_single(self):
    loaded = []
    for item in asset.load('asset:test/data/file1.nl'):
      loaded.append(item)
    self.assertEqual(len(loaded), 1)
    self.assertEqual(loaded[0].package, 'asset')
    self.assertEqual(loaded[0].name, 'test/data/file1.nl')
    with self.assertRaises(asset.NoSuchAsset) as cm:
      asset.load('asset:no-such-file.ext').peek()

  #----------------------------------------------------------------------------
  def test_load_group_read(self):
    self.assertEqual(
      asset.load('asset:test/data/file1.nl').read(), b'line-1\nline-2')
    self.assertEqual(
      asset.load('asset:test/data/file2.nl').read(), b'line-3\n')
    self.assertEqual(
      asset.load('asset:test/data/*.nl').read(), b'line-1\nline-2line-3\n')
    ag = asset.load('asset:test/data/*.nl')
    self.assertEqual(ag.readline(), b'line-1\n')
    self.assertEqual(ag.readline(), b'line-2')
    self.assertEqual(ag.readline(), b'line-3\n')

  #----------------------------------------------------------------------------
  def test_load_example(self):
    out = ET.Element('nodes')
    for item in asset.load('asset:test/data/**.nl'):
      cur = ET.SubElement(out, 'node', name=item.name)
      cur.text = item.read().decode()
    out = ET.tostring(out)
    chk = b'''\
<nodes>
  <node name="test/data/file1.nl">line-1
line-2</node>
  <node name="test/data/file2.nl">line-3
</node>
  <node name="test/data/subdir/subfile1.nl">sub-file-line-1
</node>
</nodes>
'''
    self.assertXmlEqual(out, chk)

  #----------------------------------------------------------------------------
  def test_listres(self):
    self.assertEqual(
      list(asset.listres('asset', 'test/data', showDirs=True)),
      [
        'test/data/file1.nl',
        'test/data/file2.nl',
        'test/data/subdir/',
        'test/data/subdir/subfile1.nl',
      ])

  #----------------------------------------------------------------------------
  def test_filename_egg(self):
    # NOTE: this requires that `pxml` be installed as a zipped egg, i.e.:
    #   easy_install --zip-ok pxml
    if not isEgg('pxml'):
      raise unittest.SkipTest('package "pxml" must be installed as a zipped egg')
    for item in asset.load('pxml:__init__.py'):
      self.assertIsNone(item.filename)

  #----------------------------------------------------------------------------
  def test_filename_noegg(self):
    # NOTE: this requires that `globre` be installed as an UNzipped pkg, i.e.:
    #   easy_install --always-unzip globre
    if isEgg('globre'):
      raise unittest.SkipTest('package "globre" must not be installed as a zipped egg')
    for item in asset.load('globre:__init__.py'):
      self.assertIsNotNone(item.filename)

  #----------------------------------------------------------------------------
  def test_readWithSize(self):
    self.assertEqual(
      asset.load('asset:test/data/file**').stream().read(),
      b'line-1\nline-2line-3\n')
    self.assertEqual(
      asset.load('asset:test/data/file**').stream().read(1024),
      b'line-1\nline-2line-3\n')
    stream = asset.load('asset:test/data/file**').stream()
    self.assertEqual(stream.read(5), b'line-')
    self.assertEqual(stream.read(5), b'1\nlin')
    self.assertEqual(stream.read(5), b'e-2li')
    self.assertEqual(stream.read(3), b'ne-')
    self.assertEqual(stream.read(3), b'3\n')
    self.assertEqual(stream.read(3), b'')

  #----------------------------------------------------------------------------
  def test_streamIteration(self):
    stream = asset.load('asset:test/data/file**').stream()
    self.assertEqual(stream.readline(), b'line-1\n')
    self.assertEqual(stream.readline(), b'line-2')
    self.assertEqual(stream.readline(), b'line-3\n')
    self.assertEqual(stream.readline(), b'')
    stream = asset.load('asset:test/data/file**').stream()
    chk = list(reversed([
      b'line-1\n',
      b'line-2',
      b'line-3\n',
    ]))
    for line in stream:
      self.assertEqual(line, chk.pop())

  #----------------------------------------------------------------------------
  def test_csv(self):
    import csv
    lines  = [line.decode() for line in asset.load('asset:test/data.csv').stream()]
    reader = csv.reader(lines)
    self.assertEqual(six.next(reader), ['a', 'b', 'c'])
    self.assertEqual(six.next(reader), ['1', '2', '3'])
    with self.assertRaises(StopIteration):
      six.next(reader)


#------------------------------------------------------------------------------
class TestPlugins(unittest.TestCase):

  maxDiff = None

  #----------------------------------------------------------------------------
  def test_plugin_sorting_intra(self):
    from .plugin import _sort_plugins
    self.assertEqual(
      list(_sort_plugins('myext', [
        aadict(name='foo', after=None, before=None, order=8, replace=False, final=True),
        aadict(name='foo', after=None, before=None, order=2, replace=False, final=False),
        aadict(name='foo', after=None, before=None, order=9, replace=False, final=False),
        aadict(name='foo', after=None, before=None, order=5, replace=True,  final=False),
      ])), [
        aadict(name='foo', after=None, before=None, order=5, replace=True,  final=False),
        aadict(name='foo', after=None, before=None, order=8, replace=False, final=True),
      ])

  #----------------------------------------------------------------------------
  def test_plugin_sorting_inter(self):
    from .plugin import _sort_plugins
    self.assertEqual(
      list(_sort_plugins('myext', [
        aadict(name='a', after=None,  before=None, order=8, replace=False, final=False),
        aadict(name='b', after=None,  before=None, order=9, replace=False, final=False),
        aadict(name='b', after=None,  before=None, order=2, replace=False, final=True),
        aadict(name='a', after='b',   before=None, order=5, replace=False, final=True),
        aadict(name='c', after=None,  before='a',  order=0, replace=False, final=False),
      ])), [
        aadict(name='b', after=None,  before=None, order=2, replace=False, final=True),
        aadict(name='c', after=None,  before='a',  order=0, replace=False, final=False),
        aadict(name='a', after='b',   before=None, order=5, replace=False, final=True),
      ])

  #----------------------------------------------------------------------------
  def test_plugin_sorting_spec_valid(self):
    from .plugin import _sort_plugins
    self.assertEqual(
      list(_sort_plugins('myext', [
        aadict(name='a', after=None,  before=None, order=8, replace=False, final=False),
        aadict(name='b', after=None,  before=None, order=9, replace=False, final=False),
        aadict(name='b', after=None,  before=None, order=2, replace=False, final=True),
        aadict(name='a', after='b',   before=None, order=5, replace=False, final=True),
        aadict(name='c', after=None,  before='a',  order=0, replace=False, final=False),
      ], 'c,b,a')), [
        aadict(name='c', after=None,  before='a',  order=0, replace=False, final=False),
        aadict(name='b', after=None,  before=None, order=2, replace=False, final=True),
        aadict(name='a', after='b',   before=None, order=5, replace=False, final=True),
      ])
    self.assertEqual(
      list(_sort_plugins('myext', [
        aadict(name='a', after=None,  before=None, order=8, replace=False, final=False),
        aadict(name='b', after=None,  before=None, order=9, replace=False, final=False),
        aadict(name='b', after=None,  before=None, order=2, replace=False, final=True),
        aadict(name='a', after='b',   before=None, order=5, replace=False, final=True),
        aadict(name='c', after=None,  before='a',  order=0, replace=False, final=False),
      ], '!c')), [
        aadict(name='b', after=None,  before=None, order=2, replace=False, final=True),
        aadict(name='a', after='b',   before=None, order=5, replace=False, final=True),
      ])

  #----------------------------------------------------------------------------
  def test_plugin_sorting_spec_invalid(self):
    from .plugin import _sort_plugins
    with self.assertRaises(TypeError) as cm:
      list(_sort_plugins('myext', [
        aadict(name='a', after=None,  before=None, order=8, replace=False, final=False),
        aadict(name='b', after=None,  before=None, order=9, replace=False, final=False),
        aadict(name='b', after=None,  before=None, order=2, replace=False, final=True),
        aadict(name='a', after='b',   before=None, order=5, replace=False, final=True),
        aadict(name='c', after=None,  before='a',  order=0, replace=False, final=False),
      ], '!c,b'))
    self.assertEqual(
      str(cm.exception),
      "myext plugin type 'a' specified unavailable 'after' dependency 'b'")

  #----------------------------------------------------------------------------
  def test_plugin_sorting_unavailable(self):
    from .plugin import _sort_plugins
    with self.assertRaises(TypeError) as cm:
      list(_sort_plugins('myext', [
        aadict(name='bar', after='foo', before=None, order=0, replace=False, final=False),
      ]))
    self.assertEqual(
      str(cm.exception),
      "myext plugin type 'bar' specified unavailable 'after' dependency 'foo'")
    with self.assertRaises(TypeError) as cm:
      list(_sort_plugins('myext', [
        aadict(name='bar', after=None, before='foo', order=0, replace=False, final=False),
      ]))
    self.assertEqual(
      str(cm.exception),
      "myext plugin type 'bar' specified unavailable 'before' dependency 'foo'")
    with self.assertRaises(TypeError) as cm:
      list(_sort_plugins('myext', [
        aadict(name='foo', after=None, before='bar', order=0, replace=False, final=False),
        aadict(name='bar', after=None, before='foo', order=0, replace=False, final=False),
      ]))
    self.assertEqual(
      str(cm.exception),
      "myext has cyclical dependencies in plugins ['bar', 'foo']")

  #----------------------------------------------------------------------------
  def test_plugin_spec_valid(self):
    import re
    from .plugin import _parse_spec
    self.assertEqual(_parse_spec(None), ())
    self.assertEqual(_parse_spec('*'), ())
    self.assertEqual(_parse_spec('!foo,bar'), (('!', 'foo'), ('!', 'bar')))
    self.assertEqual(_parse_spec('!foo,!bar'), (('!', 'foo'), ('!', 'bar')))
    self.assertEqual(_parse_spec(' ! foo, ! bar'), (('!', 'foo'), ('!', 'bar')))
    self.assertEqual(_parse_spec('foo,?bar'), (('+', 'foo'), ('?', 'bar')))
    self.assertEqual(_parse_spec('foo,?bar'), (('+', 'foo'), ('?', 'bar')))
    self.assertEqual(
      _parse_spec('/(foo|bar)/'),
      (('/', re.compile('(foo|bar)')),))

  #----------------------------------------------------------------------------
  def test_plugin_spec_invalid(self):
    from .plugin import _parse_spec
    with self.assertRaises(ValueError) as cm:
      _parse_spec('foo,!bar')
    self.assertEqual(
      str(cm.exception),
      'invalid mixing of "!" prefixes and required plugins in plugin specification')
    with self.assertRaises(ValueError) as cm:
      _parse_spec('!foo,?bar')
    self.assertEqual(
      str(cm.exception),
      'invalid mixing of "!" and "?" prefixes in plugin specification')
    with self.assertRaises(ValueError) as cm:
      _parse_spec('/foo')
    self.assertEqual(
      str(cm.exception),
      'regex plugin loading specification must start and end with "/"')

  #----------------------------------------------------------------------------
  def test_plugin_spec_match(self):
    from .plugin import _parse_spec, _match_spec
    self.assertTrue(_match_spec(_parse_spec('*'), 'foo'))
    self.assertTrue(_match_spec(_parse_spec('/foo/'), 'foo'))
    self.assertTrue(_match_spec(_parse_spec('/(foo|bar)/'), 'foo'))
    self.assertTrue(_match_spec(_parse_spec('/(foo|bar)/'), 'bar'))
    self.assertTrue(_match_spec(_parse_spec('foo,?bar'), 'foo'))
    self.assertTrue(_match_spec(_parse_spec('foo,?bar'), 'bar'))
    self.assertTrue(_match_spec(_parse_spec('!foo'), 'bar'))
    self.assertFalse(_match_spec(_parse_spec('!foo'), 'foo'))
    self.assertFalse(_match_spec(_parse_spec('foo,?bar'), 'zog'))


#------------------------------------------------------------------------------
# end of $Id$
#------------------------------------------------------------------------------
