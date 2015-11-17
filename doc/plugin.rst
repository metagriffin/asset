===================
Plugin Architecture
===================


Overview
========

The `asset` package enhances the `setuptools
<https://pypi.python.org/pypi/setuptools>`_ extension/plugin loading
mechanism to allow simple ordering and dependency management of
plugins.

Here is an example that calls all the plugins, with a single argument,
registered under the ``mypackage.plugins`` entrypoint group:

.. code:: python

  import logging
  import asset

  log = logging.getLogger('mypackage')
  arg = 'my-arg'

  for plugin in asset.plugins('mypackage.plugins'):
    log.debug('calling the %r plugin', plugin.name)
    plugin.handle(arg)


Plugin Structure
================

The `asset.plugins` function returns a generator of objects that have
the following attributes:

* `name`

  the name of the plugin type

* `handle`

  the actual plugin symbol

* `entrypoint`

  for registered plugins, the setuptools EntryPoint object, otherwise
  ``None``


Plugin Ordering and Dependency
==============================

Each plugin handle can have the following special attributes that
control plugin ordering and dependency management:

* `after` : comma-separated list of plugin types that this plugin
  should be loaded *after* (default is none).

* `before` : comma-separated list of plugin types that this plugin
  should be loaded *before* (default is none).

* `order` : when multiple plugins are registered for the same type,
  this specifies the numerical order of this plugin (default is 0).

* `replace` : boolean that controls whether or not this plugin should
  replace the plugins of the same type that are ordered before it,
  i.e. that have a lower `order` value (default is false).

* `final` : boolean that controls whether or not this plugin should be
  the last of the plugins of the same type, i.e. plugins that have a
  higher `order` value will be ignored (default is false).


Load Specification
==================

The `asset.plugins` function takes an optional second parameter, the
`spec`, which is a string that controls how and what plugins are
loaded.

If the `spec` is ``None`` or the special value ``'*'``, then the
normal plugin loading will occur, i.e. all registered plugins will be
loaded and their self-declared ordering and dependencies will be
applied.

Otherwise, the `spec` is taken as a comma- or whitespace-separated
list of plugins to load. In this mode, the `spec` can either specify
an exact list of plugins to load, in the specified order, referred to
as an "absolute" spec. Otherwise, it is a "relative" spec, which
indicates that it only adjusts the standard registered plugin
loading. A spec is a list of either absolute or relative instructions,
and they cannot be mixed.

In either mode, a plugin is identified either by name for registered
plugins (e.g. ``foo``), or by fully-qualified Python module and symbol
name for unregistered plugins (e.g. ``package.module.symbol``).

Plugins in an absolute spec are loaded in the order specified and can
be optionally prefixed with the following special characters:

* ``'?'`` : the specified plugin should be loaded if available. If it
  is not registered, cannot be found, or cannot be loaded, then it is
  ignored (a DEBUG log message will be emitted, however).

Plugins in a relative spec are always prefixed with at least one of
the following special characters:

* ``'-'`` : removes the specified plugin; this does not affect plugin
  ordering, it only removes the plugin from the loaded list. If the
  plugin does not exist, no error is thrown.

* ``'+'`` : adds or requires the specified plugin to the loaded
  set. If the plugin is not a named/registered plugin, then it will be
  loaded as an asset-symbol, i.e. a Python-dotted module and symbol
  name. If the plugin does not exist or cannot be loaded, this will
  throw an error. It does not affect the plugin ordering of registered
  plugins.

* ``'/'`` : the plugin name is taken as a regular expression that will
  be used to match plugin names and it must terminate in a slash. Note
  that this must be the **last** element in the spec list.

Examples:

* ``'*'`` : load all registered plugins.

* ``'foo,bar'`` : load the "foo" plugin, then the "bar" plugin.

* ``'foo,?bar'`` : load the "foo" plugin and if the "bar" plugin
  exists, load it too.

* ``'-zig'`` : load all registered plugins except the "zig" plugin.

* ``'+pkg.foo.bar'`` : load all registered plugins and then load the
  "pkg.foo.bar" Python symbol.

* ``'pkg.foo.bar'`` : load only the "pkg.foo.bar" Python symbol.


Example
=======

The following example code and entrypoint declaration registers the
entrypoint group ``package.plugins`` with the registered plugin types
``one``, ``two``, and ``three``, which will be loaded in that order:

.. code:: python

  # file: package.standard

  def one_add(value):
    return value + 1

  def two_double(value):
    return value * 2
  # specify that this plugin should be loaded after the `one` plugin
  two_double.after = 'one'

  def three_square(value):
    import math
    return math.sqrt(value)
  # specify that this plugin should be loaded after the `two` plugin
  three_square.after = 'two'

And in the package's ``setup.py`` file, you would declare:

.. code:: python

  from setuptools import setup
  setup(
    # ... other arguments ...
    entry_points = {
      'package.plugins' : [
        'one    = package.standard:one_add',
        'two    = package.standard:two_double',
        'three  = package.standard:three_square',
      ]
    }
  )

An example of actually invoking these plugins:

.. code:: python

  import asset

  value = 17

  for plugin in asset.plugins('package.plugins'):
    value = plugin.handle(value)

  # ==> `value` should now be 6
