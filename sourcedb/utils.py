# Taken from Python 2.7
import sys

def _resolve_name(name, package, level):
    """Return the absolute name of the module to be imported."""
    if not hasattr(package, 'rindex'):
        raise ValueError("'package' not set to a string")
    dot = len(package)
    for x in xrange(level, 1, -1):
        try:
            dot = package.rindex('.', 0, dot)
        except ValueError:
            raise ValueError("attempted relative import beyond top-level "
                              "package")
    return "%s.%s" % (package[:dot], name)


def import_module(name, package=None):
    """Import a module.

    The 'package' argument is required when performing a relative import. It
    specifies the package to use as the anchor point from which to resolve the
    relative import to an absolute import.

    """
    if name.startswith('.'):
        if not package:
            raise TypeError("relative imports require the 'package' argument")
        level = 0
        for character in name:
            if character != '.':
                break
            level += 1
        name = _resolve_name(name[level:], package, level)
    __import__(name)
    return sys.modules[name]
# End 2.7 backport.

def load_class(dotted_path):
    """Loads and returns a class definition provided a dotted path
    specification the last part of the dotted path is the class name
    and there is at least one module name preceding the class name.
    """

    try:
        module, classname = dotted_path.rsplit('.', 1)
        mod = import_module(module)
        return getattr(mod, classname)
    except (AttributeError, ImportError), e:
        raise ImportError("Could not import '%s' (Is it on sys.path? "
                          "Does it have syntax errors?): %s" % (dotted_path, e))
