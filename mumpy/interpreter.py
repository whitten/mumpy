"""MUMPy Interpreter

The functions in this module represent various functions that may need
to be carried out from the command line (including starting the REPL
and compiling and executing a routine file).

Licensed under a BSD license. See LICENSE for more information.

Author: Christopher Rink"""
try:
    # Used by Python's input() to provide readline functionality
    # Does not work on Windows, so we'll just pass
    import readline
except ImportError:
    pass
import mumpy


def start_repl(debug=False):
    """Start the interpreter loop."""
    env = mumpy.MUMPSEnvironment()
    p = mumpy.MUMPSParser(env, debug=debug)

    # Catch the Keyboard Interrupt to let us exit gracefully
    try:
        # Accept user input
        while True:
            current_line = input("mumpy > ")

            # Catch any Syntax errors from the user input
            try:
                p.parse_repl(current_line)
            except mumpy.MUMPSSyntaxError as e:
                print(e)

            # If output was emitted, we need to add an extra newline
            if p.output:
                print("")
    except KeyboardInterrupt:
        print("")
        pass


def compile_routine(files, debug=False):
    """Compile a list of routines."""
    # Compile the routines to an intermediate format
    intf = []
    for file in files:
        print("Compiling {file}...".format(file=file))
        try:
            intf.append(mumpy.MUMPSFile(rou=file, debug=debug, recompile=True))
            print("Success!")
        except mumpy.MUMPSCompileError as e:
            print(e)
            print("Failed to compile {rou}!".format(rou=file))


def interpret(file, tag=None, args=None, device=None,
              recompile=False, debug=False):
    """Interpret a routine file.."""
    # Prepare the file
    try:
        f = mumpy.MUMPSFile(file, recompile=recompile, debug=debug)
    except mumpy.MUMPSCompileError as e:
        print(e)
        return

    # IF we recompiled and we made it this far, then there were no errors
    if recompile:
        print("{} recompiled successfully!".format(file))

    # Prepare the environment and parser
    env = mumpy.MUMPSEnvironment()
    p = mumpy.MUMPSParser(env, debug=debug)

    # If the user specifies another default device, use that
    if device is not None:
        env.open(device)
        env.use(device)

    # Parse the file
    try:
        p.parse_file(f, tag=tag, args=args)
    except mumpy.MUMPSSyntaxError as e:
        print(e)
