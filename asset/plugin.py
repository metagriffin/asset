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

import re
import logging

import six
import pkg_resources
from aadict import aadict
import asset

#------------------------------------------------------------------------------

log = logging.getLogger(__name__)

#------------------------------------------------------------------------------
def plugins(group, spec=None):
  # TODO: share this documentation with `../doc/plugin.rst`...
  '''
  Returns a list of plugins for the specified setuptools-style
  entrypoint `group`. This is just a wrapper around
  `pkg_resources.iter_entry_points` that allows the plugins to sort
  and override themselves. The plugins have the following attributes
  of note:

  * `name` : the name of the plugin type

  * `handle` : the actual plugin symbol

  * `entrypoint` : for registered plugins, the setuptools EntryPoint
    object, otherwise ``None``

  The optional `spec` parameter controls how and what plugins are
  loaded. If it is ``None`` or the special value ``'*'``, then the
  normal plugin loading will occur, i.e. all registered plugins will
  be loaded and their self-declared ordering and dependencies will be
  applied.

  Otherwise, the `spec` is taken as a comma- or whitespace-separated
  list of plugins to load. In this mode, the `spec` can either specify
  an exact list of plugins to load, in the specified order, referred
  to as an "absolute" spec. Otherwise, it is a "relative" spec, which
  indicates that it only adjusts the standard registered plugin
  loading. A spec is a list of either absolute or relative
  instructions, and they cannot be mixed.

  In either mode, a plugin is identified either by name for registered
  plugins (e.g. ``foo``), or by fully-qualified Python module and
  symbol name for unregistered plugins
  (e.g. ``package.module.symbol``).

  Plugins in an absolute spec are loaded in the order specified and
  can be optionally prefixed with the following special characters:

  * ``'?'`` : the specified plugin should be loaded if available.  If
    it is not registered, cannot be found, or cannot be loaded, then
    it is ignored (a DEBUG log message will be emitted, however).

  Plugins in a relative spec are always prefixed with at least one of
  the following special characters:

  * ``'-'`` : removes the specified plugin; this does not affect
    plugin ordering, it only removes the plugin from the loaded
    list. If the plugin does not exist, no error is thrown.

  * ``'+'`` : adds or requires the specified plugin to the loaded
    set. If the plugin is not a named/registered plugin, then it will
    be loaded as an asset-symbol, i.e. a Python-dotted module and
    symbol name. If the plugin does not exist or cannot be loaded,
    this will throw an error. It does not affect the plugin ordering
    of registered plugins.

  * ``'/'`` : the plugin name is taken as a regular expression that
    will be used to match plugin names and it must terminate in a
    slash. Note that this must be the **last** element in the spec
    list.

  Examples:

  * ``'*'`` : load all registered plugins.

  * ``'foo,bar'`` : load the "foo" plugin, then the "bar" plugin.

  * ``'foo,?bar'`` : load the "foo" plugin and if the "bar" plugin
    exists, load it too.

  * ``'-zig'`` : load all registered plugins except the "zig" plugin.

  * ``'+pkg.foo.bar'`` : load all registered plugins and then load
    the "pkg.foo.bar" Python symbol.

  * ``'pkg.foo.bar'`` : load only the "pkg.foo.bar" Python symbol.
  '''
  spec   = _parse_spec(spec)
  plugs  = list(_get_registered_plugins(group, spec))
  plugs  += list(_get_unregistered_plugins(group, plugs, spec))
  return _sort_plugins(group, plugs, spec)

#------------------------------------------------------------------------------
# relative specs:
SPEC_ADD       = '+'
SPEC_REM       = '-'
SPEC_RE        = '/'
# absolute specs:
SPEC_SET       = ' '
SPEC_OPT       = '?'
SPEC_ALL       = '*'
_specsep_cre   = re.compile(r'(^|\s+)([-+?])\s*')
_specname_cre  = re.compile(r'^[a-zA-Z_]')
_spec_rel      = set((SPEC_ADD, SPEC_REM, SPEC_RE))
_spec_abs      = set((SPEC_SET, SPEC_OPT))

#------------------------------------------------------------------------------
def _parse_spec(spec):
  if isinstance(spec, tuple):
    return spec
  wspec = spec.strip() if spec else None
  if not wspec or wspec == SPEC_ALL:
    return ()
  respec = None
  if wspec.endswith('/'):
    if len(wspec.split('/')) <= 2:
      raise ValueError(
        'regex plugin loading expression must start and end with "/"')
    wspec, respec = wspec.split('/', 1)
    respec = respec[:-1]
    if wspec.strip() \
        and not ( wspec.strip().endswith(',') or wspec != wspec.rstrip() ):
      raise ValueError(
        'regex plugin loading expression must start and end with "/"')
  wspec = wspec.replace(',', ' ')
  wspec = _specsep_cre.sub(r' \2', wspec)
  wspec = [e.strip() for e in wspec.split()]
  ret = []
  for item in wspec:
    if not item.strip():
      continue
    item = (SPEC_SET, item)
    if item[1] and item[1][0] in (SPEC_ADD, SPEC_REM, SPEC_OPT):
      item = (item[1][0], item[1][1:].strip())
    if item[1] and item[1][0] in (SPEC_RE,):
      raise ValueError(
        'regex plugin loading expression must start and end with "/"')
    if not _specname_cre.match(item[1]):
      raise ValueError(
        'invalid plugin name in specification expression: %r' % (item[1],))
    ret.append(item)
  if respec:
    ret.append((SPEC_RE, re.compile(respec)))
  ops = set([item[0] for item in ret])
  rel = ops & _spec_rel
  abs = ops & _spec_abs
  if bool(ops & rel) and bool(ops & abs):
    raise ValueError(
      'invalid mixing of relative (%r) and absolute (%r) prefixes in plugin specification'
      % (list(rel), list(abs)))
  return tuple(ret)

#------------------------------------------------------------------------------
def _match_spec(spec, name):
  if not spec:
    return True
  for idx, item in enumerate(spec):
    if item[0] == SPEC_RE:
      if item[1].match(name):
        return True
      if ( idx + 1 ) >= len(spec):
        return False
      continue
    if item[1] != name:
      continue
    if item[0] == SPEC_REM:
      return False
    return True
  if spec[0][0] in _spec_rel:
    return True
  return False

#------------------------------------------------------------------------------
def _decorate_plugin(plugin):
  plugin.after   = getattr(plugin.handle, 'after',   None)
  plugin.before  = getattr(plugin.handle, 'before',  None)
  plugin.order   = getattr(plugin.handle, 'order',   0)
  plugin.replace = getattr(plugin.handle, 'replace', False)
  plugin.final   = getattr(plugin.handle, 'final',   False)

#------------------------------------------------------------------------------
def _get_registered_plugins(group, spec=None):
  spec = _parse_spec(spec)
  for entrypoint in pkg_resources.iter_entry_points(group):
    plugin = aadict(
      name         = entrypoint.name,
      entrypoint   = entrypoint,
    )
    if _match_spec(spec, plugin.name):
      plugin.handle  = entrypoint.load()
      _decorate_plugin(plugin)
      yield plugin

#------------------------------------------------------------------------------
def _load_asset_plugin(spec):
  plugin = aadict(
    name         = spec,
    entrypoint   = None,
    handle       = asset.symbol(spec),
  )
  _decorate_plugin(plugin)
  return plugin

#------------------------------------------------------------------------------
def _get_unregistered_plugins(group, plugins, spec=None):
  spec = _parse_spec(spec)
  names = [plug.name for plug in plugins]
  for item in spec:
    if item[0] in (SPEC_REM, SPEC_RE) or item[1] in names:
      continue
    try:
      yield _load_asset_plugin(item[1])
    except Exception:
      if item[0] in (SPEC_OPT,):
        log.debug('could not load optional plugin %r', item[1])
        continue
      raise ValueError('could not load plugin %r' % (item[1],))

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
  if spec and spec[0][0] not in _spec_rel:
    snames = []
    for item in spec:
      if item[1] in names:
        snames.append(item[1])
        continue
      if item[0] == SPEC_OPT:
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
        reqs[name].after += [p.strip() for p in plug.after.split(',')]
      if plug.before:
        reqs[name].before += [p.strip() for p in plug.before.split(',')]
    reqs[name].after  = [aft for aft in reqs[name].after if aft]
    reqs[name].before = [bef for bef in reqs[name].before if bef]
  # simplify after/before evaluation by pushing before's into after's
  for name in names:
    for aft in reqs[name].after:
      opt = aft.startswith(SPEC_OPT)
      if not opt and aft not in names:
        raise TypeError(
          '%s plugin type %r specified unavailable \'after\' dependency %r'
          % (group, name, aft))
    for bef in reqs[name].before:
      opt = bef.startswith(SPEC_OPT)
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
        opt = aft.startswith(SPEC_OPT)
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
def plugin(group, name, after=None, before=None, order=None, replace=None, final=None):
  def _wrapper(func):
    func.plugin_group = group
    func.plugin_name  = name
    if after is not None:
      func.after = after
    if before is not None:
      func.before = before
    if order is not None:
      func.order = order
    if replace is not None:
      func.replace = replace
    if final is not None:
      func.final = final
    return func
  return _wrapper

#------------------------------------------------------------------------------
# end of $Id$
# $ChangeLog$
#------------------------------------------------------------------------------
