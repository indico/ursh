import os
from importlib import import_module
from importlib.util import find_spec


def _get_package_root_path(import_name):
    """Get the root path of a package.

    Returns ``None`` if the specified import name is invalid or
    points to a module instead of a package.
    """
    spec = find_spec(import_name)
    if spec is None or not spec.parent:
        # no parent if it's not a package (PEP 451)
        return None
    paths = spec.submodule_search_locations
    assert len(paths) == 1
    return paths[0]


def import_all_models(package_name):
    """Import all modules inside 'models' folders of a package.

    The purpose of this is to import all SQLAlchemy models when the
    application is initialized so there are no cases where models
    end up not being imported e.g. because they are only referenced
    implicitly in a relationship instead of being imported somewhere.

    :param package_name: Top-level package name to scan for models.
    """
    package_root = _get_package_root_path(package_name)
    modules = []
    for root, dirs, files in os.walk(package_root):
        if os.path.basename(root) == 'models':
            package = os.path.relpath(root, package_root).replace(os.sep, '.')
            modules += ['{}.{}.{}'.format(package_name, package, name[:-3])
                        for name in files
                        if name.endswith('.py') and name != 'blueprint.py' and not name.endswith('_test.py')]

    for module in modules:
        import_module(module)
