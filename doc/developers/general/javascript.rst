.. _javascript:

==========
JavaScript
==========

JavaScript code is written in ECMAScript 2015 (ES6) and transpiled using webpack
and babel. Therefore, all non-compiled code is placed outside the static directory
into ``src/bptl/js/``.

We write modules for every component/view matching the BEM structure provides by
SASS.

Compiling ES6 to ES5::

    $ gulp js

To create a new component run ::

    $ gulp create-component --name my-compoment-name --js

To create a new view run ::

    $ gulp create-view --name my-compoment-name --js

All third party libraries should be installed using npm::

    $ npm install --save <package>

or::

    $ npn install --save-dev <package>

After installing libraries can be included using ES6 imports::

    import <package> from '<package>';

**Exceptions**

When you need to override third-party JavaScript you still need to manually place
files into ``src/bptl/static/``.
