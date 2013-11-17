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

# possible demarkation PACKAGE:RESOURCE:
#
# mypkg:foo/bar/zig.html
# mypkg.foo.bar|zig
# mypkg.foo.bar#zig
# mypkg.foo.bar@zig
# mypkg.foo.bar+zig
# mypkg.foo.bar=zig
# mypkg.foo.bar%zig
# mypkg.foo.bar^zig
# mypkg.foo.bar&zig
# mypkg.foo.bar*zig
# mypkg.foo.bar-zig
#
# mypkg.foo.bar?zig
# mypkg.foo.bar/zig
# mypkg.foo.bar!zig
#
# mypkg.foo.bar>zig
# mypkg.foo.bar$zig
# mypkg.foo.bar$zig

import re, os, pkg_resources, functools, six
import globre

from .symbol import symbol

#------------------------------------------------------------------------------
class NoSuchAsset(Exception): pass

#------------------------------------------------------------------------------
class AssetGroupStream(object):
  # TODO: implement all expected file-like methods...
  def __init__(self, group):
    self.group  = group
    self.assets = iter(group)
    self._cur   = None
  def read(self):
    # todo: make sure this works with binary/text content... ugh.
    ret = '' if self._cur is None else self._cur.read()
    ret += ''.join([ast.read() for ast in self.assets])
    return ret
  def readline(self):
    if self._cur is None:
      try:
        self._cur = self.assets.next()
      except StopIteration:
        return ''
    while 1:
      ret = self._cur.readline()
      if ret:
        return ret
      try:
        self._cur = self.assets.next()
      except StopIteration:
        return ''

#------------------------------------------------------------------------------
class AssetGroup(object):
  # TODO: implement all expected file-like methods...
  def __init__(self, package, package_dir, regex, spec):
    # todo: remove `package_dir` -- it should be inferred...
    self.package = package
    self.pkgdir  = package_dir
    self.regex   = regex
    self.spec    = spec
    self._fp     = None
  def peek(self):
    for pkg, res in self.resources():
      return self
  def resources(self):
    count = 0
    for resource in listres(self.package, self.pkgdir):
      if not self.regex.match(resource):
        continue
      count += 1
      yield (self.package, resource)
    if count <= 0:
      raise NoSuchAsset('No asset matched "%s"' % (self.spec,))
  def __len__(self):
    return len(list(self.resources()))
  def __iter__(self):
    for pkg, res in self.resources():
      yield Asset(self, pkg, res)
  def stream(self):
    return AssetGroupStream(self)
  def _stream(self):
    if self._fp is None:
      self._fp = self.stream()
    return self._fp
  def read(self):
    return self._stream().read()
  def readline(self):
    return self._stream().readline()

#------------------------------------------------------------------------------
class AssetStream(object):
  # TODO: implement all expected file-like methods...
  def __init__(self, stream, asset):
    self.stream = stream
    self.asset  = asset
  def read(self):
    return self.stream.read()
  def readline(self):
    return self.stream.readline()

#------------------------------------------------------------------------------
class Asset(object):
  # todo: should all returned streams be "AssetStream"s that provide
  #       a .asset attribute, like TransformerStream does?
  # TODO: implement all expected file-like methods...
  def __init__(self, group, package, name):
    self.group   = group
    self.package = package
    self.name    = name
    self._fp     = None
  def __str__(self):
    return '%s:%s' % (self.package, self.name)
  def stream(self):
    return AssetStream(
      pkg_resources.resource_stream(self.package, self.name), self)
  def _stream(self):
    if self._fp is None:
      self._fp = self.stream()
    return self._fp
  def read(self):
    return self._stream().read()
  def readline(self):
    return self._stream().readline()
  # compatibility with AssetGroup() API...
  def peek(self):
    if pkg_resources.resource_exists(self.package, self.name):
      return self
    raise NoSuchAsset('No asset matched "%s:%s"' % (self.package, self.name))
  def resources(self):
    self.peek()
    yield (self.package, self.name)
  def __len__(self):
    self.peek()
    return 1
  def __iter__(self):
    self.peek()
    yield self

defaultExclude = ('.svn', '.git', '.rcs')

#------------------------------------------------------------------------------
def listres(pkgname, pkgdir,
            recursive=True, depthFirst=False,
            exclude=defaultExclude, showDirs=False,
            ):
  reslist = [os.path.join(pkgdir, cur)
             for cur in pkg_resources.resource_listdir(pkgname, pkgdir)
             if cur not in exclude]
  dirs = []
  for cur in sorted(reslist):
    if pkg_resources.resource_isdir(pkgname, cur):
      if showDirs:
        yield cur + '/'
      if recursive:
        if depthFirst:
          for subcur in listres(pkgname, cur):
            yield subcur
        else:
          dirs.append(cur)
    else:
      yield cur
  for cur in dirs:
    for subcur in listres(pkgname, cur):
      yield subcur

#------------------------------------------------------------------------------
def load(pattern, *args, **kw):
  '''
  Given a package asset-spec glob-pattern `pattern`, returns an
  :class:`AssetGroup` object, which in turn can act as a generator of
  :class:`Asset` objects that match the pattern.

  Example:

  .. code-block:: python

    import asset

    # concatenate all 'css' files into one string:
    css = asset.load('mypackage:static/style/**.css').read()

  '''

  spec = pattern

  if ':' not in pattern:
    raise ValueError('`pattern` must be in the format "PACKAGE:GLOB"')

  pkgname, pkgpat = pattern.split(':', 1)
  pkgdir, pattern = globre.compile(pkgpat, split_prefix=True, flags=globre.EXACT)

  if pkgdir:
    idx = pkgdir.rfind('/')
    pkgdir = pkgdir[:idx] if idx >= 0 else ''

  group = AssetGroup(pkgname, pkgdir, pattern, spec)
  if globre.iswild(pkgpat):
    return group
  return Asset(group, pkgname, pkgpat)

#------------------------------------------------------------------------------
# end of $Id$
#------------------------------------------------------------------------------
