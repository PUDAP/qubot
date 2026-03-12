# qubot-drivers

Qubot Hardware drivers for the PUDA (Physical Unified Device Architecture) platform. This package provides Python interfaces for controlling laboratory automation equipment.

## Features

- **Gantry Control**: Control G-code compatible motion systems (e.g., QuBot)
- **Liquid Handling**: Interface with Sartorius rLINE® pipettes and dispensers
- **Serial Communication**: Robust serial port management with automatic reconnection
- **Logging**: Configurable logging with optional file output to logs folder
- **Cross-platform**: Works on Linux, macOS, and Windows

## Installation

### From PyPI

```bash
pip install qubot-drivers
```

## Available machines

- **Biologic**
- **First**

## Device Support

The following device types are supported:

- **GCode** - G-code compatible motion systems (e.g., QuBot)
- **Sartorius rLINE®** - Electronic pipettes and robotic dispensers
- **Camera** - Webcams and USB cameras for image and video capture

## Finding Serial Ports

To discover available serial ports on your system:

```python
from qubot_drivers.core import list_serial_ports

# List all available ports
ports = list_serial_ports()
for port, desc, hwid in ports:
    print(f"{port}: {desc} [{hwid}]")

# Filter ports by description
sartorius_ports = list_serial_ports(filter_desc="Sartorius")
```

## Requirements

- Python >= 3.8
- pyserial >= 3.5
- See `pyproject.toml` for full dependency list

## Development

### Setup Development Environment

This package is part of a UV workspace monorepo. First, install `uv` if you haven't already. See the [uv installation guide](https://docs.astral.sh/uv/getting-started/installation/) for platform-specific instructions.

**From the repository root:**

```bash
# Or install dependencies for all workspace packages
uv sync --all-packages
```

This will:
- Create a virtual environment at the repository root (`.venv/`)
- Install all dependencies for all workspace packages
- Install `qubot-drivers` and other workspace packages in editable mode automatically

**Using the package:**

```bash
# Run Python scripts with workspace context (recommended, works from anywhere in the workspace)
uv run python your_script.py

# Or activate the virtual environment (from repository root where .venv is located)
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
python your_script.py
```

**Adding dependencies:**

```bash
# From the package directory
cd libs/drivers
uv add some-package

# Or from repository root
uv add --package qubot-drivers some-package
```

**Note:** Workspace packages are automatically installed in editable mode, so code changes are immediately available without reinstalling.

### Testing

Run tests using pytest with `uv run`:

```bash
# Run all tests
uv run pytest tests/

# Run a specific test file
uv run pytest tests/test_deck.py

# Run a specific test class
uv run pytest tests/test_deck.py::TestDeckToDict

# Run a specific test function
uv run pytest tests/test_deck.py::TestDeckToDict::test_to_dict_empty_deck

# Run with verbose output
uv run pytest tests/ -v

# Run with coverage report
uv run pytest tests/ --cov=qubot_drivers --cov-report=html
```

**Note:** Make sure you're in the `libs/drivers` directory or use the full path to the tests directory when running pytest commands.

### Building and Publishing

```bash
# Build distribution packages
uv build

# cd to puda project root
cd ...

# Publish to PyPI
uv publish
# Username: __token__
# Password: <your PyPI API token>
```

### Version Management

```bash
# Set version explicitly
uv version 0.0.1

# Bump version (e.g., 1.2.3 -> 1.3.0)
uv bump minor
```

## Documentation

- [PyPI Package](https://pypi.org/project/qubot-drivers/)
- [GitHub Repository](https://github.com/zhao-bears/qubot-drivers)
- [Issue Tracker](https://github.com/zhao-bears/qubot-drivers/issues)

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request on GitHub.
