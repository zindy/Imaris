#!/usr/bin/env python

"""Automatic replacement of imported Python modules.

The hotswap module watches the source files of imported modules which are
replaced by its new version when the respective source files change.
The need for a program restart during development of long-running programs
like GUI applications for example is reduced.

Additionally this module can be called as a wrapper script:
hotswap.py [OPTIONS] <module.py> [args]

In this case module.py is imported as module and the function
module.main() is called. Hotswapping is enabled so that changes
in the source code take effect without restarting the program.
"""

version = "0.1"
__author__ = "Michael Krause"
__email__ = "michael@krause-software.de"

#
# CREDITS
#   The idea and first implementation of the mechanism used by this module
#   was first made public by Thomas Heller in a Usenet posting
#   to comp.lang.python in 2001 (named autoreload.py).
#   Updates for new-style classes were taken from a Usenet posting
#   by Jeremy Fincher.

__all__ = ['run', 'stop', 'superreload']

import time
import os
import threading
import sys
import types
import imp
import getopt

def _get_compiled_ext():
    for ext, mode, typ in imp.get_suffixes():
        if typ == imp.PY_COMPILED:
            return ext

# the official way to get the extension of compiled files (.pyc or .pyo)
PY_COMPILED_EXT = _get_compiled_ext()

class ModuleWatcher:
    SECONDS_BETWEEN_CHECKS = 0.1
    SKIP_SYSTEM_MODULES = False
    NOTIFYFUNC = None
    VERBOSE = False
    running = 0
    def __init__(self):
        # If we don't do this, there may be tracebacks
        # when shutting down python.
        import atexit
        atexit.register(self.stop)

    def run(self, skipsystem=SKIP_SYSTEM_MODULES,
                  seconds=SECONDS_BETWEEN_CHECKS,
                  notifyfunc=NOTIFYFUNC,
                  verbose=VERBOSE):
        if self.running:
            if verbose:
                print "# hotswap already running"
            return
        self.SKIP_SYSTEM_MODULES = skipsystem
        self.SECONDS_BETWEEN_CHECKS = seconds
        self.NOTIFYFUNC = notifyfunc
        self.VERBOSE = verbose

        if self.VERBOSE:
            print "# starting hotswap seconds=%s, skipsystem=%s" \
                % (self.SECONDS_BETWEEN_CHECKS, self.SKIP_SYSTEM_MODULES)
        self.running = 1
        self.thread = threading.Thread(target=self._check_modules)
        self.thread.setDaemon(1)
        self.thread.start()

    def stop(self):
        if not self.running:
            if self.VERBOSE:
                print "# hotswap not running"
            return
        self.running = 0
        self.thread.join()
        if self.VERBOSE:
            print "# hotswap stopped"

    def _check_modules(self):
        while self.running:
            time.sleep(self.SECONDS_BETWEEN_CHECKS)
            for m in sys.modules.values():
                if not hasattr(m, '__file__'):
                    # We only check modules that have a plain file
                    # as Python source.
                    continue
                if m.__name__ == '__main__':
                    # __main__ cannot be reloaded without executing
                    # its code a second time, so we skip it.
                    continue
                file = m.__file__
                path, ext = os.path.splitext(file)

                if self.SKIP_SYSTEM_MODULES:
                    # do not check system modules
                    sysprefix = sys.prefix + os.sep
                    if file.startswith(sysprefix):
                        continue

                if ext.lower() == '.py':
                    ext = PY_COMPILED_EXT
                    file = path + PY_COMPILED_EXT

                if ext != PY_COMPILED_EXT:
                    continue

                try:
                    if os.stat(file[:-1])[8] <= os.stat(file)[8]:
                        # This module is unchanged if the .py-file
                        # is older than the compiled .pyc or .pyo file.
                        continue
                except OSError:
                    continue

                try:
                    print ">>>",m.__name__
                    superreload(m, verbose=self.VERBOSE)
                    if hasattr(m, 'onHotswap') and callable(m.onHotswap):
                        print "yeah?"
                        # The module can invalidate cached results or post
                        # redisplay operations by defining function named
                        # onHotswap that is called after a reload. 
                        m.onHotswap()
                    if callable(self.NOTIFYFUNC):
                        self.NOTIFYFUNC(module=m)
                except:
                    import traceback
                    traceback.print_exc(0)

def update_function(old, new, attrnames):
    for name in attrnames:
        try:
            setattr(old, name, getattr(new, name))
        except AttributeError:
            pass

def superreload(module,
                reload=reload,
                _old_objects = {},
                verbose=True):
    """superreload (module) -> module

    Enhanced version of the builtin reload function.
    superreload replaces the class dictionary of every top-level
    class in the module with the new one automatically,
    as well as every function's code object.
    """
    # retrieve the attributes from the module before the reload,
    # and remember them in _old_objects.
    for name, object in module.__dict__.items():
        key = (module.__name__, name)
        _old_objects.setdefault(key, []).append(object)

    if verbose:
        print "# reloading module %r" % module
    newmodule = reload(module)
    # XXX We have a problem here if importing the module fails!

    # iterate over all objects and update them
    for name, new_obj in newmodule.__dict__.items():
        # print "updating", `name`, type(new_obj), `new_obj`
        key = (newmodule.__name__, name)
        if _old_objects.has_key(key):
            for old_obj in _old_objects[key]:
                if type(old_obj) == types.TypeType and \
                   old_obj.__module__ == newmodule.__name__:
                    # New-style classes support __getattribute__, which is called
                    # on *any* attribute access, so they get updated the first
                    # time they're used after a reload.
                    # We have to pass in newvalue because of Python's scoping.
                    def updater(self, s, newvalue=new_obj):
                        # This function is to be an __getattr__ or __getattribute__.
                        try:
                            self.__class__ = newvalue
                        except:
                            try:
                                del self.__class__.__getattribute__
                            except AttributeError:
                                del self.__class__.__getattr__
                        return getattr(self, s)
                    old_obj.__getattribute__ = updater
                elif type(new_obj) == types.ClassType:
                    old_obj.__dict__.update(new_obj.__dict__)
                elif type(new_obj) == types.FunctionType:
                    update_function(old_obj,
                           new_obj,
                           "func_code func_defaults func_doc".split())
                elif type(new_obj) == types.MethodType:
                    update_function(old_obj.im_func,
                           new_obj.im_func,
                           "func_code func_defaults func_doc".split())

    return newmodule

_watcher = ModuleWatcher()

run = _watcher.run
stop = _watcher.stop

def modulename(path):
    return os.path.splitext(path)[0].replace(os.sep, '.')

def importmodule(filename):
    """Returns the imported module of this source file. 

    This function tries to find this source file as module
    on the Python path, so that its typical module name is used.
    If this does not work, the directory of this file is inserted
    at the beginning of sys.path and the import is attempted again.
    """
    sourcefile = os.path.abspath(filename)
    modfile = os.path.basename(sourcefile)
    # Given an absolute filename of a python source file,
    # we need to find it on the Python path to calculate its
    # proper module name.
    candidates = []
    for p in sys.path:
        pdir = p + os.sep
        checkfile = os.path.join(p, modfile)
        if os.path.normcase(sourcefile).startswith(os.path.normcase(pdir)):
            relmodfile = sourcefile[len(pdir):]
            candidates.append((len(relmodfile), relmodfile))
    if candidates:
        # Pick the most specific module path from all candidates
        candidates.sort()
        modname = modulename(candidates[0][1])
    else:
        modname = modulename(os.path.basename(sourcefile))
    try:
        # In case the source file was in the Python path
        # it can be imported now.
        module = __import__(modname, globals(), locals(), [])
    except ImportError, e:
        failed_modname = str(e).split()[-1]
        if str(e).split()[-1] == modname:
            # The ImportError wasn't caused by some nested import
            # but our module was not found, so we add the source files
            # directory to the path and import it again.
            modname = modulename(os.path.basename(sourcefile))
            sys.path.insert(0, os.path.dirname(sourcefile))
            module = __import__(modname, globals(), locals(), [])
        else:
            import traceback
            tb = sys.exc_traceback
            if tb:
                tb = tb.tb_next
            traceback.print_exception(sys.exc_type, sys.exc_value, tb)
            # The module to be imported could be found but raised an
            # ImportError itself.
            raise e

    # We have to deal module nesting like logging.handlers
    # before calling the modules main function.
    components = modname.split('.')
    for comp in components[1:]:
        module = getattr(module, comp)
    return module

#----------------------------------------------------------------------------

class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg

def usage(argv0):
    print >>sys.stderr, """Usage: %s [OPTIONS] <module.py>
Import module and call module.main() with hotswap enabled.
Subsequent modifications in module.py and other source files of
modules being used are monitored periodically and put into effect
without restarting the program.

Options:
-h, --help                Display this help then exit.
-w, --wait                Wait number of seconds between checks. [0.1]
-s, --skipsystem          Skip check of system modules beneath (%s). [False]
-v, --verbose             Display diagnostic messages. [False]
""" % (argv0, sys.prefix)

#----------------------------------------------------------------------------

def main(argv=None):
    if argv is None:
        argv = sys.argv

    wait = ModuleWatcher.SECONDS_BETWEEN_CHECKS
    skipsystem = ModuleWatcher.SKIP_SYSTEM_MODULES
    verbose = ModuleWatcher.VERBOSE
    # parse command line arguments
    try:
        try:
            opts, args = getopt.getopt(argv[1:], "hw:sv",
                                       ["help", "wait",
                                        "skipsystem", "verbose"])
        except getopt.error, msg:
             raise Usage(msg)

        for o, a in opts:
            if o in ("-h", "--help"):
                usage(argv[0])
                return 0
            if o in ("-w", "--wait"):
                try:
                    wait = float(a)
                except ValueError:
                    raise Usage("Parameter -w/--wait expects a float value")
            if o in ("-s", "--skipsystem"):
                skipsystem = True
            if o in ("-v", "--verbose"):
                verbose = True

    except Usage, err:
        print >>sys.stderr, "%s:" % argv[0],
        print >>sys.stderr, err.msg
        print >>sys.stderr, "for help use --help"
        return 2

    # Remove hotswap options from arguments
    if args:
        del argv[1:-len(args)]
    else:
        del argv[1:]

    if len(argv) <= 1:
        usage(argv[0])
        sys.exit(1)

    firstarg = argv[1]
    sourcefile = os.path.abspath(firstarg)
    if not os.path.isfile(sourcefile):
        print "%s: File '%s' does not exist." % (os.path.basename(argv[0]),
                                                      sourcefile)
        sys.exit(1)
    try:
        module = importmodule(sourcefile)
    except ImportError, e:
        print "%s: Unable to import '%s' as module: %s" % (os.path.basename(argv[0]),
                                                          sourcefile, e)
        sys.exit(1)

    # Remove hotswap.py from arguments that argv looks as
    # if no additional wrapper was present.
    del argv[0]

    # Start hotswapping
    run(skipsystem=skipsystem,
        seconds=wait,
        verbose=verbose)

    # Run the Python source file with hotswapping enabled. 
    module.main()

if __name__ == '__main__':
    main()
