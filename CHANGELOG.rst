=========
ChangeLog
=========


v0.6.11
=======

* Added `Asset.count()` helper function (alias to ``len(Asset)``)
* Added `Asset.exists()` helper function (non-exception-based version of
  ``Asset.peek()``)


v0.6.10
=======

* Added plugin loading error logging
* Fixed symbol loading bug when using ':' separator


v0.6.9
======

* Added `PluginSet.select(name)` plugin selection method.


v0.6.8
======

* Enhanced return value from `asset.plugins` to be a first-class
  object (`PluginSet`) that has aggregate plugin operation methods
  `PluginSet.handle` and `PluginSet.filter`.


v0.6.7
======

* Added initial implementation of `asset.plugin` helper decorator


v0.6.6
======

* Corrected regex negative handling


v0.6.5
======

* Updated `asset.plugins` to support loading of unregistered plugins
* Changed ``'!'`` `asset.plugins` prefix to ``'-'``


v0.6.4
======

* Added `asset.plugins` plugin loading mechanism that supports simple
  ordering and overriding of plugins


v0.6.3
======

* Added check for egg vs. not-egg in unit tests


v0.6.2
======

* Removed distribute dependency (thanks jlec)


v0.6.1
======

* Added Python 3 support


v0.6
====

* Added more standard file object compatibility (stream iteration,
  reading with size, and closing)


v0.0.5
======

* Promoted to "stable" development status
* First tagged release
* Added `asset.version()` helper function
