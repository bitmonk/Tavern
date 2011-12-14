#
#   Errors
#

import sys
from Cython.Utils import open_new_file
from . import DebugFlags
from . import Options


class PyrexError(Exception):
    pass

class PyrexWarning(Exception):
    pass


def context(position):
    source = position[0]
    assert not (isinstance(source, str) or isinstance(source, str)), (
        "Please replace filename strings with Scanning.FileSourceDescriptor instances %r" % source)
    try:
        F = source.get_lines()
    except UnicodeDecodeError:
        # file has an encoding problem
        s = "[unprintable code]\n"
    else:
        s = ''.join(F[max(0, position[1]-6):position[1]])
        s = '...\n%s%s^\n' % (s, ' '*(position[2]-1))
    s = '%s\n%s%s\n' % ('-'*60, s, '-'*60)
    return s

def format_position(position):
    if position:
        return "%s:%d:%d: " % (position[0].get_error_description(),
                                position[1], position[2])
    return ''

def format_error(message, position):
    if position:
        pos_str = format_position(position)
        cont = context(position)
        message = '\nError compiling Cython file:\n%s\n%s%s' % (cont, pos_str, message or '')
    return message

class CompileError(PyrexError):

    def __init__(self, position = None, message = ""):
        self.position = position
        self.message_only = message
        self.reported = False
    # Deprecated and withdrawn in 2.6:
    #   self.message = message
        Exception.__init__(self, format_error(message, position))

class CompileWarning(PyrexWarning):

    def __init__(self, position = None, message = ""):
        self.position = position
    # Deprecated and withdrawn in 2.6:
    #   self.message = message
        Exception.__init__(self, format_position(position) + message)

class InternalError(Exception):
    # If this is ever raised, there is a bug in the compiler.

    def __init__(self, message):
        self.message_only = message
        Exception.__init__(self, "Internal compiler error: %s"
            % message)

class AbortError(Exception):
    # Throw this to stop the compilation immediately.

    def __init__(self, message):
        self.message_only = message
        Exception.__init__(self, "Abort error: %s" % message)

class CompilerCrash(CompileError):
    # raised when an unexpected exception occurs in a transform
    def __init__(self, pos, context, message, cause, stacktrace=None):
        if message:
            message = '\n' + message
        else:
            message = '\n'
        self.message_only = message
        if context:
            message = "Compiler crash in %s%s" % (context, message)
        if stacktrace:
            import traceback
            message += (
                '\n\nCompiler crash traceback from this point on:\n' +
                ''.join(traceback.format_tb(stacktrace)))
        if cause:
            if not stacktrace:
                message += '\n'
            message += '%s: %s' % (cause.__class__.__name__, cause)
        CompileError.__init__(self, pos, message)

class NoElementTreeInstalledException(PyrexError):
    """raised when the user enabled options.gdb_debug but no ElementTree
    implementation was found
    """

listing_file = None
num_errors = 0
echo_file = None

def open_listing_file(path, echo_to_stderr = 1):
    # Begin a new error listing. If path is None, no file
    # is opened, the error counter is just reset.
    global listing_file, num_errors, echo_file
    if path is not None:
        listing_file = open_new_file(path)
    else:
        listing_file = None
    if echo_to_stderr:
        echo_file = sys.stderr
    else:
        echo_file = None
    num_errors = 0

def close_listing_file():
    global listing_file
    if listing_file:
        listing_file.close()
        listing_file = None

def report_error(err):
    if error_stack:
        error_stack[-1].append(err)
    else:
        global num_errors
        # See Main.py for why dual reporting occurs. Quick fix for now.
        if err.reported: return
        err.reported = True
        try: line = "%s\n" % err
        except UnicodeEncodeError:
            # Python <= 2.5 does this for non-ASCII Unicode exceptions
            line = format_error(getattr(err, 'message_only', "[unprintable exception message]"),
                                getattr(err, 'position', None)) + '\n'
        if listing_file:
            try: listing_file.write(line)
            except UnicodeEncodeError:
                listing_file.write(line.encode('ASCII', 'replace'))
        if echo_file:
            try: echo_file.write(line)
            except UnicodeEncodeError:
                echo_file.write(line.encode('ASCII', 'replace'))
        num_errors = num_errors + 1
        if Options.fast_fail:
            raise AbortError("fatal errors")

def error(position, message):
    #print "Errors.error:", repr(position), repr(message) ###
    if position is None:
        raise InternalError(message)
    err = CompileError(position, message)
    if DebugFlags.debug_exception_on_error: raise Exception(err) # debug
    report_error(err)
    return err

LEVEL=1 # warn about all errors level 1 or higher

def message(position, message, level=1):
    if level < LEVEL:
        return
    warn = CompileWarning(position, message)
    line = "note: %s\n" % warn
    if listing_file:
        listing_file.write(line)
    if echo_file:
        echo_file.write(line)
    return warn

def warning(position, message, level=0):
    if level < LEVEL:
        return
    if Options.warning_errors and position:
        return error(position, message)
    warn = CompileWarning(position, message)
    line = "warning: %s\n" % warn
    if listing_file:
        listing_file.write(line)
    if echo_file:
        echo_file.write(line)
    return warn

_warn_once_seen = {}
def warn_once(position, message, level=0):
    if level < LEVEL or message in _warn_once_seen:
        return
    warn = CompileWarning(position, message)
    line = "warning: %s\n" % warn
    if listing_file:
        listing_file.write(line)
    if echo_file:
        echo_file.write(line)
    _warn_once_seen[message] = True
    return warn


# These functions can be used to momentarily suppress errors.

error_stack = []

def hold_errors():
    error_stack.append([])

def release_errors(ignore=False):
    held_errors = error_stack.pop()
    if not ignore:
        for err in held_errors:
            report_error(err)

def held_errors():
    return error_stack[-1]


# this module needs a redesign to support parallel cythonisation, but
# for now, the following works at least in sequential compiler runs

def reset():
    _warn_once_seen.clear()
    del error_stack[:]