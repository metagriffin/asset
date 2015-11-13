# -*- coding: utf-8 -*-
#------------------------------------------------------------------------------
# file: $Id$
# auth: metagriffin <mg.github@uberdev.org>
# date: 2015/11/12
# copy: (C) Copyright 2015-EOT metagriffin -- see LICENSE.txt
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

# todo: this should probably be moved into a more generic, separate package...

import re

import six
import pkg_resources
from aadict import aadict

#------------------------------------------------------------------------------
def plugins(group, spec=None):
  '''
  Returns a list of plugins for the specified setuptools-style
  entrypoint `group`. This is just a wrapper around
  `pkg_resources.iter_entry_points` that allows the plugins to sort
  and override themselves. The plugins have the following attributes
  of note:

  * `name` : the name of the plugin type
  * `handle` : the actual plugin symbol
  * `entrypoint` : the setuptools EntryPoint object

  The optional `spec` parameter controls how plugins are loaded. If it
  is ``None`` or the special value ``'*'``, then the normal plugin
  loading will occur, i.e. the plugins will be allowed to specify
  their own ordering and dependencies. If `spec` starts with a forward
  slash (``'/'``) then it is taken as a regular expression that will
  be used to match plugin names and it must terminate in a
  slash. Otherwise, the `spec` is a comma-separated list of plugin
  types that will be returned in the specified order. The plugin type
  can further be prefixed with ``'!'`` to indicate that the plugin
  should NOT be loaded and with ``'?'`` to indicate that the plugin is
  optional (i.e. an error should not be raised if it cannot be
  found). If using the ``'!'`` prefix, then all components must have
  the ``'!'`` prefix.
  '''
  spec = _parse_spec(spec)
  return _sort_plugins(group, _get_unsorted_plugins(group, spec), spec)

#------------------------------------------------------------------------------
def _parse_spec(spec):
  if isinstance(spec, tuple):
    return spec
  if not spec or spec == '*':
    return ()
  if spec.startswith('/'):
    if not spec.endswith('/'):
      raise ValueError(
        'regex plugin loading specification must start and end with "/"')
    return (('/', re.compile(spec[1:-1])),)
  spec = [e.strip() for e in spec.split(',')]
  ret = []
  for item in spec:
    item = ('+', item)
    if item[1] and item[1][0] in '!?':
      item = (item[1][0], item[1][1:].strip())
    ret.append(item)
  ops = [item[0] for item in ret]
  if '!' in ops:
    if '?' in ops:
      raise ValueError(
        'invalid mixing of "!" and "?" prefixes in plugin specification')
    if '+' in ops:
      if ops[0] == '!' and set(ops[1:]) == set(['+']):
        ret = [('!', item[1]) for item in ret]
      else:
        raise ValueError(
          'invalid mixing of "!" prefixes and required plugins in plugin specification')
  return tuple(ret)

#------------------------------------------------------------------------------
def _match_spec(spec, name):
  if not spec:
    return True
  if spec[0][0] == '/':
    return bool(spec[0][1].match(name))
  for item in spec:
    if item[1] == name:
      if item[0] == '!':
        return False
      return True
  return spec[0][0] == '!'

#------------------------------------------------------------------------------
def _get_unsorted_plugins(group, spec=None):
  spec = _parse_spec(spec)
  for entrypoint in pkg_resources.iter_entry_points(group):
    plugin = aadict(
      name         = entrypoint.name,
      entrypoint   = entrypoint,
    )
    if _match_spec(spec, plugin.name):
      plugin.handle  = entrypoint.load()
      plugin.after   = getattr(plugin.handle, 'after',   None)
      plugin.before  = getattr(plugin.handle, 'before',  None)
      plugin.order   = getattr(plugin.handle, 'order',   0)
      plugin.replace = getattr(plugin.handle, 'replace', False)
      plugin.final   = getattr(plugin.handle, 'final',   False)
      yield plugin

#------------------------------------------------------------------------------
def _sort_plugins(group, plugins, spec=None):
  spec = _parse_spec(spec)
  lut = dict()
  for plugin in plugins:
    if plugin.name not in lut:
      lut[plugin.name] = []
    lut[plugin.name].append(plugin)
  # order the plugins within each named group by order/replace/final
  for name, plugs in list(lut.items()):
    plugs = sorted(plugs, key=lambda plug: plug.order)
    for idx, plug in enumerate(plugs):
      if plug.final:
        plugs = plugs[:idx + 1]
        break
    for idx, plug in enumerate(reversed(plugs)):
      if plug.replace:
        plugs = plugs[len(plugs) - idx - 1:]
    lut[name] = plugs
  # apply `spec`
  names = [name for name in sorted(lut.keys()) if _match_spec(spec, name)]
  if spec and spec[0][0] not in '/!':
    snames = []
    for item in spec:
      if item[1] in names:
        snames.append(item[1])
        continue
      if item[0] == '?':
        continue
      raise TypeError(
        '%s plugin spec %r specified unavailable dependency %r'
        % (group, spec, item[1]))
    for name in snames:
      for plug in lut[name]:
        yield plug
    return
  # order the named groups by after/before
  reqs = dict()
  for name in names:
    reqs[name] = aadict(after=[], before=[])
    for plug in lut[name]:
      if plug.after:
        reqs[name].after += plug.after.split(',')
      if plug.before:
        reqs[name].before += plug.before.split(',')
    reqs[name].after  = [aft for aft in reqs[name].after if aft]
    reqs[name].before = [bef for bef in reqs[name].before if bef]
  # simplify after/before evaluation by pushing before's into after's
  for name in names:
    for aft in reqs[name].after:
      opt = aft.startswith('?')
      if not opt and aft not in names:
        raise TypeError(
          '%s plugin type %r specified unavailable \'after\' dependency %r'
          % (group, name, aft))
    for bef in reqs[name].before:
      opt = bef.startswith('?')
      if opt:
        bef = bef[1:]
      if bef not in names:
        if not opt:
          raise TypeError(
            '%s plugin type %r specified unavailable \'before\' dependency %r'
            % (group, name, bef))
        continue
      reqs[bef].after.append(name)
  # created the ordered list obeying the 'after' rules
  snames = []
  while len(snames) < len(names):
    cur = len(snames)
    for name in names:
      if name in snames:
        continue
      ok = True
      for aft in reqs[name].after:
        opt = aft.startswith('?')
        if opt:
          aft = aft[1:]
        if aft not in snames and aft in names:
          ok = False
      if ok:
        snames.append(name)
    if len(snames) == cur:
      raise TypeError(
        '%s has cyclical dependencies in plugins %r'
        % (group, sorted(list(set(names) - set(snames))),))
  for name in snames:
    for plug in lut[name]:
      yield plug

#------------------------------------------------------------------------------
# end of $Id$
# $ChangeLog$
#------------------------------------------------------------------------------
