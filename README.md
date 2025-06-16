# Stratego Bot Arena

This repository provides a small environment for running Stratego bots.  It includes two
submodules containing C++/Java code used to evaluate bots as well as a Python
interface to drive games.

## Clone With Submodules

```bash
git clone --recursive <repository_url>
# or, if already cloned
cd stratego_bot_arena
git submodule update --init --recursive
```

## Installing Python Dependencies

Make sure you have Python 3.13+ installed and activate your preferred virtual
environment.  Then install the package and the required tools:

```bash
python -V
pip install .
pip install pybind11
export pybind11_DIR=$(python -m pybind11 --cmakedir)
pip install git+https://github.com/valvarl/deepnash-torchrl.git@rb_test
```

These steps install the Python package itself, the `pybind11` headers used by
some C++ components and the optional Stratego training environment.

## Viewing the API Documentation

A copy of the original competition manager documentation is kept in
`lib/stratego_evaluator/doc/manager_manual.txt`.  Open it with your favourite
viewer:

```bash
nano lib/stratego_evaluator/doc/manager_manual.txt
```

It explains the communication protocol used by the included agents and the
`stratego` manager.

## Compiling the Native Components

Both submodules provide Makefiles.  Run `make` in their directories to build the
executables and the Java archive:

```bash
# Build the C++ manager and bundled agents
cd lib/stratego_evaluator/manager
make

# Build the Java client
cd ../../demon_of_ignorance/src
make
```

Some agents also include their own Makefiles.  The game script will compile
those on first use if the executables are missing.

## Running a Self-play Game

With the managers compiled and Python installed you can run a match between the
provided bots using the helper script.  For example:

```bash
python scripts/run_game.py \
  --red lib/stratego_evaluator/agents/basic_cpp/basic_cpp \
  --blue lib/stratego_evaluator/agents/peternlewis/peternlewis \
  --render none
```

The script compiles the chosen bots when necessary and then starts a game
without graphics.  Pass `--render human` to see a simple window showing the
board.