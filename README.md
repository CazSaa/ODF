## PyCUDD install instructions

Dependencies:
- Python 3.13 (This version is currently hardcoded in `lib/pycudd2.0.2/pycudd/Makefile`, you can probably use a different version by changing the `PYTHON_VER` variable in the Makefile)
- SWIG (I used version 4.3.0, other versions may work as well)
- gcc (I used version 14.2.1, other versions may work as well)
- g++ (I used version 14.2.1, other versions may work as well)
- make (I used version 4.4.1, other versions may work as well)
Open terminal in the root directory of the project and run the following commands:
```bash
$ cd lib/pycudd2.0.2/cudd-2.4.2
$ mkdir lib
$ make build
$ make libso
$ cd ../pycudd
$ make
```
