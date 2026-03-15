# Standard library imports
import os
import sys

# Internal imports
import ktp_controller.cli.main

if __name__ == "__main__":
    if "KTP_CONTROLLER_LOGGING_LEVEL" not in os.environ:
        # For CLI, use WARNING as the default level, no matter what
        # the library default is. We want to keep CLI output as clean
        # as possible.
        os.environ["KTP_CONTROLLER_LOGGING_LEVEL"] = "WARNING"
    sys.exit(ktp_controller.cli.main.run())
