================================
Generalized Package Asset Loader
================================

Loads resources and symbols from a python package, whether installed
as a directory, an egg, or in source form.

TL;DR
=====

Install:

.. code-block:: bash

  $ pip install asset

Load symbols (e.g. functions, class, or variables) from a package by
name:

.. code-block:: python

  import asset

  # call the 'mypackage.foo.myfunc' function
  retval = asset.symbol('mypackage.foo.myfunc')(param='value')

Load data files from a package:

.. code-block:: python

  import asset

  # load the file 'mypackage/templates/data.txt' into string
  data = asset.string('mypackage:templates/data.txt')

  # or as a file-like stream
  stream = asset.stream('mypackage:templates/data.txt')
  data   = stream.read()

Multiple files can be operated on at once by using glob-like
wildcards:

.. code-block:: python

  import asset

  # concatenate all 'css' files into one string:
  css = asset.load('mypackage:static/style/**.css').read()

  # load all '.txt' files, XML-escaping the data and wrapping
  # each file in an <node name="...">...</node> element.
  import xml.etree.ElementTree as ET
  data = ET.Element('nodes')
  for item in asset.load('asset:**.txt'):
    cur = ET.SubElement(data, 'node', name=item.name)
    cur.text = item.read()
  data = ET.tostring(data)


Details
=======

...

Note: because ``asset.load()`` does lazy-loading, it only throws a
`NoSuchAsset` exception when you actually attempt to use the
AssetGroup! If you need an immediate error, use the `peek()` method.
Note that it returns itself, so you can do something like:

.. code-block:: python

  import asset

  def my_function_that_returns_an_iterable():

    return asset.load(my_spec).peek()

    # this returns exactly the same thing as the following, but
    # throws an exception early if there are no matching assets:
    #
    #   return asset.load(my_spec)

