import time
import sys
import traceback

def deeply_nested_faulty_function():
    time.sleep(1)
    raise ValueError("A critical Python error occurred!")

def intermediate_function():
    deeply_nested_faulty_function()

def main():
    print("Python app starting...", file=sys.stdout)
    try:
        intermediate_function()
    except Exception as e:
        # This will output a multi-line traceback to stderr
        traceback.print_exc(file=sys.stderr)

if __name__ == "__main__":
    main()
