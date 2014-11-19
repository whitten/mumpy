"""MUMPY Language Components

The functions and objects in this file represent various functional parts
of the MUMPS language (such as expressions and commands). The parser
pieces all of these parts together into larger components and then
executes them. In that way, each component is designed to work together
to achieve the actions dictated by the M standard.

Licensed under a BSD license. See LICENSE for more information.

Author: Christopher Rink"""
__author__ = 'christopher'
import datetime
import random
import string
import os
import time
import traceback
import blist
import mumpy


# Date and time values are pre-calculated since they won't change
_horolog_origin = datetime.datetime(1840, 12, 31)
_horolog_midnight = datetime.time()


###################
# COMMAND FUNCTIONS
# Command functions execute the actions given by a MUMPS keyword command
# such as 'w' (write). Each matches the signature func(args, env). They
# return one of the following values:
# - None :: the command has finished and execution should continue
# - True :: the command was conditional (IF, ELSE) and execution can continue
# - False :: the command was conditional (IF, ELSE) and execution should stop
# - MUMPSNone() :: a scope change command (i.e. QUIT) is returning nothing
# - MUMPSExpression() :: a scope change command is returning a value
###################
def new_var(args, env):
    """New the variables given in the argument list."""
    for var in args:
        env.new(var)
    return None


def do_cmd(args, env):
    """Perform a subroutine call."""
    for sub in args:
        sub.execute()
    return None


def halt(args, env):
    """Quit from the MUMPy environment."""
    raise SystemExit(0)


def hang(args, env):
    """Sleep the system for the given number of seconds."""
    for slp in args:
        time.sleep(slp)
    return None


def if_cmd(args, env):
    """Process an IF MUMPS command."""
    for expr in args:
        if not expr:
            env.set("$T", mumps_false())
            return False
    env.set("$T", mumps_true())
    return True


def if_no_args(args, env):
    """Process an argumentless IF MUMPS command."""
    if env.get("$T").equals(mumps_true()):
        return True
    return False


def else_cmd(args, env):
    """Process a MUMPS ELSE command."""
    if env.get("$T").equals(mumps_false()):
        return True
    return False


def kill(args, env):
    """Kill the variables given in the argument list."""
    for var in args:
        env.kill(var)
    return None


def kill_all(args, env):
    """Kill all the symbols in the environment."""
    env.kill_all()
    return None


def quit_cmd(args, env):
    """Quit from the current scope."""
    # Quits from a DO block should have no argument
    if args is None:
        return MUMPSNone()

    # Check for multiple quit arguments
    if len(args) > 1:
        raise MUMPSSyntaxError("QUIT commands cannot have multiple arguments",
                               err_type="INVALID ARGUMENTS")

    # Return the evaluated expression otherwise
    return str(args[0])


def open_dev(args, env):
    """Open the devices given in the argument list."""
    for arg in args:
        # Unpack the device and device parameters
        dev = arg[0]
        opts = arg[1]

        # Open the device
        env.open(dev)
    return None


def close_dev(args, env):
    """Close the devices given in the argument list."""
    for arg in args:
        # Unpack the device and device parameters
        dev = arg[0]
        opts = arg[1]

        # Open the device
        env.close(dev)
    return None


def use_dev(args, env):
    """Use the device listed in the argument list."""
    # We can only have one argument
    arg = args[0]

    # Unpack the device and any parameters
    dev = arg[0]
    opts = arg[1]

    # Set the device
    env.use(dev)
    return None


def read(args, env):
    """Read inputs from the current environment device."""
    read_last = False
    for item in args:
        if not item.is_ident():
            env.write(item)
            read_last = False
        else:
            temp = env.input()
            env.set(item.as_ident(), MUMPSExpression(temp))
            read_last = True

    # If we did not read last, output an extra newline
    if not read_last:
        env.write("\n")

    return None


def set_var(args, env):
    """Set the symbols in the argument list to the given expression."""
    for item in args:
        env.set(item[0], item[1])
    return None


def write(args, env):
    """Write out the given expressions."""
    for item in args:
        env.write(item)
    env.write("\n")
    return None


def write_symbols(args, env):
    """Write out all of the symbols in the environment."""
    env.print()
    return None


###################
# INTRINSIC FUNCTIONS
# Intrinsic functions are those functions in MUMPS which are prefixed
# with a single dollar sign and provide some functionality which is
# difficult or otherwise impossible to complete using the standard
# MUMPS commands.
###################
def intrinsic_ascii(expr, which=1):
    """Return the UTF-8 ordinal value for the character number in expr given
    by the input parameter `which` or -1 if `which` is larger than the
    length of the expression."""
    try:
        if which-1 >= 0:
            char = MUMPSExpression(ord(str(expr)[which-1]))
        else:
            raise IndexError
    except IndexError:
        char = MUMPSExpression(-1)

    return char


def instrinsic_char(args):
    """Return the UTF-8 character value for the ordinal number or numbers
    given in the argument list."""
    chars = []
    for arg in args:
        chars.append(chr(arg.as_number()))
    return MUMPSExpression(''.join(chars))


def intrinsic_extract(expr, low=1, high=None):
    """Extract the first character from `expr` if neither `low` and `high`
    are given. If just `low` is given, then return the character at that
    index. If both `low` and `high` are given, return the substring from
    `low` to `high` index."""
    try:
        if isinstance(low, int) and isinstance(high, int):
            # Get the indices (noting that the low index is inclusive)
            slen = len(str(expr))
            low -= 1

            # The low index cannot be higher than the high index
            # The low index cannot be below 0 either
            if low > high or low < 0:
                raise IndexError

            # The length cannot exceed the string length
            if high > slen:
                high = slen

            return MUMPSExpression(str(expr)[low:high])
        elif isinstance(low, int):
            # Get the index
            idx = low-1

            # The low index cannot be below 0
            if idx < 0:
                raise IndexError

            return MUMPSExpression(str(expr)[idx])
        else:
            return MUMPSExpression(str(expr)[0])
    except IndexError:
        return mumps_null()


def intrinsic_find(expr, search, start=None):
    """Find the first instance of the substring `search` in `expr` after
    the`start`th character or from the beginning if `start` is None."""
    try:
        sub = str(search)
        idx = mumpy.MUMPSExpression(
            str(expr).index(sub, start) + len(sub) + 1)
    except ValueError:
        idx = mumpy.MUMPSExpression(0)

    return idx


def intrinsic_justify(expr, rspace, ndec=None):
    """Right justify the value given in `expr` by the number of spaces in
    `rspace`. If the optional `ndec` argument is given, then `expr` will
    be treated as numeric and rounded to `ndec` decimal places or zero
    padded if there are not at least `ndec` decimal places."""
    if ndec is not None:
        expr = round(expr.as_number(), ndec)
        s = str(expr).split(".")
        dig, dec = len(s[0]), len(s[1]) if len(s) > 1 else 0
        expr = expr if dec >= ndec else str(expr).ljust(ndec + dig + 1, '0')

    return MUMPSExpression(str(expr).rjust(rspace))


def intrinsic_length(expr, char=None):
    """Compute the length of the input `expr` as a string or, if `char` is
    not None, count the number of occurrences of `char` in `expr`."""
    if char is not None:
        return MUMPSExpression(str(expr).count(str(char)))
    return MUMPSExpression(len(str(expr)))


def intrinsic_piece(expr, char, num=1):
    """Give the `num`th piece of `expr` split about `char` (1 indexed)."""
    try:
        piece = str(expr).split(sep=str(char))[num-1]
    except IndexError:
        piece = mumpy.mumps_null()

    return MUMPSExpression(piece)


def intrinsic_random(num):
    """Given `num`, return a random integer in the range [0, num). Raise
    a syntax error if num is less than 1."""
    if num < 1:
        raise mumpy.MUMPSSyntaxError("RANDOM argument less than 1.",
                                     err_type="$R ARG INVALID")

    return MUMPSExpression(random.randint(0, num))


def intrinsic_select(args):
    """Given a list of `args` (a list of expression tuples), return the
    expression in index 1 for the first expression in index 0 which
    evaluates to True."""
    for arg in args:
        if arg[0]:
            return arg[1]
    raise mumpy.MUMPSSyntaxError("No select arguments evaluated true.",
                                 err_type="NO $S ARGS TRUE")


def intrinsic_translate(expr, trexpr, newexpr=None):
    """Remove every character in `trexpr` from `expr` if `newexpr` is None,
    or translate each character in `trexpr` to the identical index character
    from `newexpr`. If `newexpr` is shorter than `trexpr`, then remove the
    characters from `trexpr` which do not have siblings in `newexpr`."""
    # We use the string and translation map for both paths
    expr = str(expr)
    trexpr = str(trexpr)
    trmap = dict()

    if newexpr is not None:
        # Create a translation map between the two strings
        # In this iteration, we map positionally identical characters
        # between the input string and the replacement string
        # Characters without matches are deleted (i.e. if the
        # replacement string is shorter than the translation string)
        newmap = str(newexpr)
        for i, c in enumerate(trexpr):
            try:
                trmap[ord(c)] = ord(newmap[i])
            except IndexError:
                trmap[ord(c)] = None
    else:
        # Create a translation map which deletes each character
        for c in trexpr:
            trmap[ord(c)] = None

    # Return the translated string
    return MUMPSExpression(expr.translate(trmap))


###################
# SPECIAL VARIABLE FUNCTIONS
# Special variables are values in MUMPS which return some state information
# about the environment to the caller. They cannot be assigned to as a
# normal variable and are always provided *by* the environment.
###################
def horolog():
    """Return the MUMPS $H time and date variable."""
    # Get today and now
    today = datetime.datetime.today()
    now = datetime.datetime.now()

    # Figure out the midnight of today so we can compute the timedelta
    midnight = datetime.datetime.combine(today, _horolog_midnight)

    # Produce the deltas
    daydelta = today - _horolog_origin
    tdelta = now - midnight

    # Produce the string
    return MUMPSExpression("{d},{t}".format(
        d=daydelta.days,
        t=tdelta.seconds,
    ))


def current_job():
    """Return the MUMPS $J value, which is the current process ID."""
    return MUMPSExpression(os.getpid())


###################
# LANGUAGE COMPONENTS
# Language components are various components of the language which can be
# assembled and executed by the parser to provide the action or behavior
# specified in the ANSI/ISO M standard.
#
# Most of the components are designed in such a way that they can be
# assembled or compounded from repeated calls to the __init__ function.
#
# For example, MUMPSExpressions compound (and, in effect, reduce) as you
# perform operations on them. Clients should be mindful of this behavior
# as it can produce unexpected results. This has the effect of, like
# quantum physics, changing the state of the element as you examine it.
# For this reason, some components provide '''SAFE''' functions which
# do not modify the component in place.
###################
class MUMPSLine:
    """Represent a full line of MUMPS code."""
    def __init__(self, cmd, other=None):
        """Initialize the line"""
        if isinstance(other, (MUMPSLine, MUMPSEmptyLine)):
            self.list = other.list
            self.list.append(cmd)
        else:
            self.list = [cmd]

    def __repr__(self):
        """Return a string representation of this command."""
        return "MUMPSLine({cmds})".format(
            cmds=self.list,
        )

    def execute(self):
        """Execute the entire line of commands."""
        last = True
        for cmd in self.list:
            # If the last command returned an expression, we're done
            if isinstance(last, MUMPSExpression):
                break

            # If the last command returned False, quit
            if last is not None and not last:
                last = None
                break

            # Execute the next command and get it's return value
            last = cmd.execute()

        return last


class MUMPSEmptyLine:
    """Represents a no-op line in MUMPS."""
    def __init__(self, data, **kwargs):
        self.data = data

    def __repr__(self):
        return "MUMPSEmptyLine({data})".format(data=self.data)

    def execute(self):
        """Do absolutely nothing."""
        pass


class MUMPSCommand:
    """Represents a MUMPS command execution."""
    def __init__(self, cmd, args, env, post=None):
        """Initialize the MUMPS command instance with a command and args and
        any given post-conditional expression."""
        # Check that we can call this command function
        if not callable(cmd):
            raise TypeError("A callable command function is expected.")

        # Check that we got an actual argument list
        if not isinstance(args, (type(None), MUMPSArgumentList)):
            raise MUMPSSyntaxError("Commands require a valid argument list.",
                                   err_type="INVALID ARGUMENTS")

        # Check that our expression can be evaluated
        if not isinstance(post, (type(None), MUMPSExpression)):
            raise MUMPSSyntaxError(
                "Post-conditionals must be valid expressions.",
                err_type="INVALID POST-CONDITIONAL"
            )

        # Check that we got a valid environment
        if not isinstance(env, mumpy.MUMPSEnvironment):
            raise TypeError("A valid MUMPS environment must be specified.")

        self.cmd = cmd
        self.args = args
        self.env = env
        self.post = post

    def __repr__(self):
        """Return a string representation of this command."""
        return "MUMPSCommand({cmd}, {args}, {post})".format(
            cmd=self.cmd,
            args=self.args,
            post=self.post
        )

    def execute(self):
        """Execute the action of this command."""
        # Check the value of the post-conditional
        # Return if this expression evaluates as False
        if self.post is not None and not self.post:
            return None

        # Execute the command with the given arguments
        return self.cmd(self.args, self.env)


class MUMPSFuncSubCall:
    """Represents a function or subroutine call in a MUMPS routine."""
    def __init__(self, tag, env, parser, args=None,
                 is_func=False, rou=None, post=True):
        """Initialize a MUMPS Function or Subroutine call."""
        # The tag should be a valid MUMPS Identifier
        if not isinstance(tag, MUMPSIdentifier):
            raise MUMPSSyntaxError("Invalid Function or Subroutine name given.",
                                   err_type="INVALID FUNC OR SUB")

        # Check that we got an actual argument list
        if not isinstance(args,
                          (type(None), MUMPSArgumentList)) and not args == ():
            raise MUMPSSyntaxError("Functions and subroutines require a "
                                   "valid argument list.",
                                   err_type="INVALID ARGUMENTS")

        # Check that we got a valid environment
        if not isinstance(env, mumpy.MUMPSEnvironment):
            raise TypeError("A valid MUMPS environment must be specified.")

        # ...and parser
        if not isinstance(parser, mumpy.MUMPSParser):
            raise TypeError("A valid MUMPS parser must be specified.")

        self.tag = tag
        self.args = args
        self.env = env
        self.parser = parser
        self.is_func = is_func
        self.rou = self.env.get_routine(rou)
        self.post = post

        # If we don't have a routine at this point, we're in an error state
        if self.rou is None:
            raise MUMPSSyntaxError("No routine found.", err_type="NO LINE")

    def __repr__(self):
        return "MUMPSFuncSubCall({tag}, {args}, {as_func}, {rou})".format(
            tag=self.tag,
            args=self.args,
            as_func=self.is_func,
            rou=self.rou,
        )

    def execute(self):
        """Execute the subroutine or function call."""
        # Check for a post-conditional (for subroutines only)
        if not self.post:
            return None

        # Execute the function or subroutine
        self.env.push_func_to_stack(self)
        p = self.parser.parse_tag(self.rou, self.tag)
        self.env.pop_func_from_stack()

        # Check for syntax errors
        if self.is_func and isinstance(p, (type(None), MUMPSNone)):
            raise MUMPSSyntaxError("Function call did not return value.",
                                   err_type="FUNCTION NO RETURN")
        if not self.is_func and not isinstance(p, MUMPSNone):
            raise MUMPSSyntaxError("Subroutine call returned a value.",
                                   err_type="SUBROUTINE RETURN")

        # Return our value
        return p


class MUMPSExpression:
    """Performs arbitrarily complex expression computation."""
    def __init__(self, expr):
        # Handle cases where we may be assigned an
        # Identifier or another Expression
        if isinstance(expr, MUMPSExpression):
            self.expr = expr.expr
        elif isinstance(expr, MUMPSIdentifier):
            self.expr = expr
        elif isinstance(expr, MUMPSFuncSubCall):
            self.expr = expr.execute()
        elif expr is None:
            self.expr = ""
        else:
            self.expr = expr

    ###################
    # SAFE FUNCTIONS
    # These functions have no side-effects. They do not modify the
    # existing expression. The operator overloaded functions will
    # modify the existing expression and return it with the compound
    # result of the operation.
    ###################
    def as_number(self):
        """Return the canonical MUMPS numeric form of this expression."""
        if isinstance(self.expr, MUMPSIdentifier):
            return _mumps_number(str(self.expr.value()))
        return _mumps_number(self.expr)

    def is_ident(self):
        """Return True if this expression is also an Identifier."""
        return True if isinstance(self.expr, MUMPSIdentifier) else False

    def as_ident(self):
        """Return the Identifier represented by this expression."""
        return self.expr if isinstance(self.expr, MUMPSIdentifier) else None

    def equals(self, other):
        """Returns True if this expression is equal to the other expression.

        Unlike the == overloaded method, this method will not modify the
        contents of the current expression."""
        return int(str(self) == str(MUMPSExpression(other)))

    def __getitem__(self, item):
        """Enable MUMPSExpressions to be subscriptable."""
        return self.expr.__getitem__(item)

    def __len__(self):
        """Return the expression length."""
        return len(self.expr)

    def __bool__(self):
        """Return True if this expression evaluates to true."""
        return bool(self.as_number())

    def __hash__(self):
        """Return the hash of the current value."""
        return hash(str(self))

    def __str__(self):
        """Return the string value of the expression."""
        if isinstance(self.expr, MUMPSIdentifier):
            v = str(self.expr.value())
        else:
            v = str(self.expr)
        return v

    def __repr__(self):
        """Return a string representation of this object."""
        return "MUMPSExpression('{expr}',{str},{num},{bool})".format(
            expr=repr(self.expr),
            str=str(self),
            num=self.as_number(),
            bool=bool(self)
        )

    ###################
    # UNSAFE FUNCTIONS
    # These functions WILL MODIFY THE EXISTING EXPRESSION. They compute
    # the reduced expression into the existing expression and return self.
    ###################
    def __eq__(self, other):
        """Return 1 if both MUMPS expressions are equal."""
        self.expr = int(str(self) == str(MUMPSExpression(other)))
        return self

    def __ne__(self, other):
        """Return 1 if this MUMPS expression is not equal to other."""
        self.expr = int(str(self) != str(MUMPSExpression(other)))
        return self

    def __gt__(self, other):
        """Return 1 if this MUMPS expression is greater than other."""
        self.expr = int(self.as_number() > _other_as_number(other))
        return self

    def __lt__(self, other):
        """Return 1 if this MUMPS expression is less than other."""
        self.expr = int(self.as_number() < _other_as_number(other))
        return self

    def __add__(self, other):
        """Add two MUMPS expressions together."""
        self.expr = _mumps_number(self.as_number() + _other_as_number(other))
        return self

    def __sub__(self, other):
        """Subtract two MUMPS expressions."""
        self.expr = _mumps_number(self.as_number() - _other_as_number(other))
        return self

    def __mul__(self, other):
        """Multiple two MUMPS expressions."""
        self.expr = _mumps_number(self.as_number() * _other_as_number(other))
        return self

    def __truediv__(self, other):
        """Divide two MUMPS expressions."""
        self.expr = _mumps_number(self.as_number() / _other_as_number(other))
        return self

    def __floordiv__(self, other):
        """Integer divide two MUMPS expressions.

        See here for truncation towards zero:
        http://stackoverflow.com/questions/19919387/in-python-what-is-a-good-way-to-round-towards-zero-in-integer-division"""
        n = self.as_number()
        d = _other_as_number(other)
        v = n // d if n * d > 0 else (n + (-n % d)) // d
        self.expr = _mumps_number(v)
        return self

    def __mod__(self, other):
        """Return the modulus of two MUMPS expressions."""
        self.expr = _mumps_number(self.as_number() % _other_as_number(other))
        return self

    def __pow__(self, power, modulo=None):
        """Return the power of two MUMPS expressions."""
        self.expr = _mumps_number(self.as_number() ** _other_as_number(power))
        return self

    def __neg__(self):
        """Return the unary negative of this MUMPS expression."""
        self.expr = -self.as_number()
        return self

    def __pos__(self):
        """Return the unary positive of this MUMPS expression."""
        self.expr = self.as_number()
        return self

    def __and__(self, other):
        """Return the AND result of two MUMPS expressions."""
        self.expr = int(self.as_number() and _other_as_number(other))
        return self

    def __or__(self, other):
        """Return the OR result of two MUMPS expressions."""
        self.expr = int(self.as_number() or _other_as_number(other))
        return self

    def __invert__(self):
        """Return the NOT result of this MUMPS expression."""
        self.expr = int(not self.as_number())
        return self

    def concat(self, other):
        """Concatenates two MUMPS values together and returns itself.."""
        self.expr = "{}{}".format(str(self), str(MUMPSExpression(other)))
        return self

    def sorts_after(self, other):
        """Return True if this MUMPS expression sorts after other in
        collation (UTF-8) order."""
        o = MUMPSExpression(other)
        s = str(self)
        l = sorted([s, str(o)])
        self.expr = 1 if (s == l[1]) else 0
        return self

    def follows(self, other):
        """Return True if this MUMPS expression follows other in
        binary order."""
        o = MUMPSExpression(other)
        b = bytes(str(self), encoding='utf8')
        l = sorted([b, bytes(str(o), encoding='utf8')])
        self.expr = 1 if (b == l[1]) else 0
        return self

    def contains(self, other):
        self.expr = 0 if (
            str(self).find(str(MUMPSExpression(other))) == -1
        ) else 1
        return self


def mumps_null():
    """Return the MUMPS null value, ""."""
    return MUMPSExpression(None)


def mumps_true():
    """Return the MUMPS true value, 1."""
    return MUMPSExpression(1)


def mumps_false():
    """Return the MUMPS false value, 0."""
    return MUMPSExpression(0)


class MUMPSIdentifier:
    """Represents a MUMPS identifier in code."""
    def __init__(self, ident, env, subscripts=None):
        # Handle the case that we may be passed another instance of
        # a MUMPSIdentifier object
        if isinstance(ident, MUMPSIdentifier):
            self._ident = str(ident._ident)
        else:
            self._ident = str(ident)

        # Make sure we got valid subscripts
        if not isinstance(subscripts, (type(None), MUMPSArgumentList)):
            raise MUMPSSyntaxError("Invalid subscript list given.",
                                   err_type="INVALID SUBSCRIPTS")
        if subscripts is not None and mumps_null() in subscripts:
            raise MUMPSSyntaxError("Null subscript given for identifier.",
                                   err_type="NULL SUBSCRIPT")

        self._subscripts = subscripts

        # Accept an environment so we can resolve our own value
        self._env = env

        # Check that we are a valid identifier
        self.is_valid()

    def __eq__(self, other):
        """Return True if this Identifier is equal to other."""
        if isinstance(other, MUMPSIdentifier):
            return self._ident == other._ident
        return False

    def __hash__(self):
        """Return the hash associated with this identifier."""
        return hash(self._ident)

    def __str__(self):
        """Return the string name of the identifier."""
        return str(self._ident)

    def __repr__(self):
        """Return a string representation of this object."""
        return "MUMPSIdentifier('{ident}',{val})".format(
            ident=self._ident,
            val=self.value()
        )

    def value(self):
        """Return the resolved value of this Identifier."""
        return self._env.get(self)

    def subscripts(self):
        """Return the subscripts associated with this Identifier."""
        return self._subscripts

    def is_valid(self):
        """Returns True if this is a valid MUMPS identifier."""
        c = self._ident[0]
        if c.isdigit():
            raise MUMPSSyntaxError("Variable names cannot start with digits.")
        if not c in "{}{}".format(string.ascii_letters, "%"):
            raise MUMPSSyntaxError("Variable names must be valid "
                                   "ASCII letters or the '%' character.")


class MUMPSPointerIdentifier(MUMPSIdentifier):
    """Represents a normal MUMPS identifier which will be used as a pointer
    when passed into a function or subroutine."""
    def __init__(self, ident, env):
        super().__init__(ident, env)


class MUMPSNone:
    """Represents the empty return from a subroutine. The purpose of this
    class is merely to act as a sentinel value, indicating that execution
    has finished and that the parser should return."""
    def __init__(self):
        pass

    def __repr__(self):
        return "MUMPSNone()"


class MUMPSArgumentList:
    """Holds a list of MUMPS arguments for a command to process."""
    def __init__(self, item, others=None):
        if isinstance(others, MUMPSArgumentList):
            self.list = others.list
            self.list.append(item)
        else:
            self.list = [item]

    def __repr__(self):
        """A string representation of the argument list."""
        return "MUMPSArgumentList({})".format(self.list)

    def __iter__(self):
        """Provide an iterator for the arguments."""
        return iter(self.list)

    def __len__(self):
        """Return the number of arguments in this list."""
        return len(self.list)

    def __getitem__(self, item):
        """Return the argument at the specified index."""
        return self.list[item]

    def __contains__(self, item):
        return item in self.list

    def reverse(self):
        """Return the reverse of the argument list."""
        self.list.reverse()
        return self


class MUMPSLocal:
    """Wrap a blist.sorteddict to provide MUMPS local variable functionality."""
    def __init__(self, value=None):
        self._b = blist.sorteddict()
        self._n = 0
        if value is not None:
            self._b[""] = value

    def __repr__(self):
        return "MUMPSLocal({root}, {n})".format(
            root=self._b[""],
            n=self._n,
        )

    def __str__(self):
        """Return the value of the root node."""
        return str(self._b[""])

    def get(self, ident):
        """Return the value given by the input identifier. If the identifier
        has no subscripts, then return the root node. If the subscript or
        subscripts don't exist, simply return null."""
        try:
            s = ident.subscripts() if not isinstance(ident, str) else None

            # Return the root value
            if s is None:
                return self._b[""]

            # Otherwise, return the value at the requested subscripts
            b = self._b
            for sub in s:
                b = b[str(sub)]
            return b[""]
        except AttributeError:
            raise MUMPSSyntaxError("Invalid identifier given for this var.",
                                   "INVALID IDENTIFIER")
        except KeyError:
            return mumps_null()

    def set(self, ident, value):
        """Set the value at the given identifier. If the identifier has no
        subscripts, then set the root node."""
        try:
            s = ident.subscripts() if not isinstance(ident, str) else None

            # Set the root value
            if s is None:
                self._b[""] = value
                return

            # Otherwise, set the value at the requested subscripts
            b = self._b
            for sub in s:
                ss = str(sub)
                try:
                    b = b[ss]
                except KeyError:
                    b[ss] = blist.sorteddict()
                    b = b[ss]
            b[""] = value
        except AttributeError:
            raise MUMPSSyntaxError("Invalid identifier given for this var.",
                                   "INVALID IDENTIFIER")

    def delete(self, ident):
        """Delete the value at the given identifier. If the root node is
        deleted, then every child node is also deleted. As a consequence of
        this behavior, the environment actually performs the delete for
        that particular case. This means that we should always have a list
        of subscripts."""
        try:
            s = ident.subscripts()

            if len(s) < 1:
                raise MUMPSSyntaxError("Variable with no subscripts given.",
                                       err_type="INVALID SUBSCRIPTS")

            self._delete(self._b, s)
        except AttributeError:
            raise MUMPSSyntaxError("Invalid identifier given for this var.",
                                   err_type="INVALID IDENTIFIER")

    def _delete(self, d, subscripts):
        """Recursive delete helper function. Since MUMPS kill command permits"""
        l = len(subscripts)

        # If there is only one subscript, delete that node and return
        if l == 1:
            try:
                s = str(subscripts[0])
                del d[s]
            except KeyError:
                pass

            return

        # If there are more subscripts, recurse
        try:
            s = str(subscripts[0])
            self._delete(d[s], subscripts[1:])
        except KeyError:
            pass

    def order(self, ident):
        """Return an iterator for the given identifier. If the identifier
        has no subscripts, then raise a syntax error."""
        try:
            s = ident.subscripts() if not isinstance(ident, str) else None

            # Set the root value
            if s is None:
                raise MUMPSSyntaxError("Cannot $ORDER over a scalar value.",
                                       err_type="INVALID $ORDER PARAM")

            # Otherwise, set the value at the requested subscripts
            b = self._b
            for sub in s:
                ss = str(sub)
                try:
                    b = b[ss]
                except KeyError:
                    b[ss] = blist.sorteddict()
                    b = b[ss]
            return b
        except AttributeError:
            raise MUMPSSyntaxError("Invalid identifier given for this var.",
                                   "INVALID IDENTIFIER")

    def pprint_str(self):
        """Return a pretty-print style string which can be output when
        the user issues an argumentless `WRITE` command (spill symbols)."""
        #TODO.md: implement this
        out = ""
        return out


class MUMPSSyntaxError(Exception):
    """Represents a MUMPS syntax error."""
    def __init__(self, err, err_type=None, line=None):
        if isinstance(err, MUMPSSyntaxError):
            self.msg = err.msg
            self.err_type = err.err_type
            self.line = line
        else:
            self.msg = str(err)
            self.err_type = "UNKNOWN" if err_type is None else err_type
            self.line = line
            #TODO.md: Remove this print_exc call
            try:
                traceback.print_exc()
            except:
                pass

    def __str__(self):
        return "SYNTAX ERROR <{type}{line}>: {msg}".format(
            type=self.err_type,
            msg=self.msg,
            line=":{num}".format(num=self.line) if self.line is not None else "",
        )

    def __repr__(self):
        return str(self)


def _mumps_number(v):
    """Given a number (perhaps evaluated by expression), return the
    integral value if it is an integer, or a float otherwise."""
    try:
        return _to_mumps_number(v)
    except ValueError:
        return 0


def _to_mumps_number(v):
    """Given a value, attempt to coerce it to either an integer or float."""
    sign = 1
    ndec = 0
    try:
        tmp = float(v)

        if tmp.is_integer():
            return int(tmp)
        else:
            return tmp
    except ValueError:
        v = str(v)
        n = []

        # Build a number based on the MUMPS numeric conversion rules
        for c in v:
            # Look for numeric characters (digits, decimal, or sign)
            if c.isnumeric() or c in ('.', '+', '-'):
                # Make sure we only add one decimal
                if c == '.':
                    if ndec >= 1:
                        break
                    else:
                        ndec += 1

                # Correctly swap the sign
                if c == '-':
                    sign *= -1
                    continue

                # Ignore the plus signs
                if c == '+':
                    continue

                # If we made it this far, this is a valid numeric character
                n.append(c)
            else:
                # If we don't find any,
                break

        # Re-assemble the digits and attempt to convert it
        n = float("".join(n)) * sign
        return n if not n.is_integer() else int(n)


def _other_as_number(other):
    """Return the `as_number` value from the other MUMPSExpression or
    0 if the other value is not a MUMPSExpression."""
    return MUMPSExpression(other).as_number()
