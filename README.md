# screenswap

Save and restore Windows monitor layouts by name. Configure your screens once in Windows display settings, then switch between setups instantly from the terminal or a desktop shortcut.

```
screenswap save productivity
screenswap load gaming
```

## Requirements

- Windows 10 or 11
- Python 3.8+

## Installation

```bash
pip install screenswap
```

## Usage

### Save a layout

Set up your monitors exactly how you want them in Windows display settings, then run:

```bash
screenswap save <name>
```

Example:

```bash
screenswap save productivity
# Layout 'productivity' saved (2 monitor(s)).
```

### Load a layout

```bash
screenswap load <name>
```

### List saved layouts

```bash
screenswap list
```

### Delete a layout

```bash
screenswap delete <name>
```

## How it works

`screenswap save` reads the current monitor configuration directly from Windows — resolution, position, refresh rate, orientation, and which display is primary — and stores it as a JSON file in `~/.screenswap/<name>.json`.

`screenswap load` reads that file, matches each saved monitor to a connected display by hardware ID (with a resolution fallback), and applies the layout atomically via the Windows display API.

Monitors not present in a saved layout are automatically repositioned to avoid overlap, and a message is printed suggesting you update the layout to include them.

## Desktop shortcut

Create a `.bat` file with your load command:

```bat
@echo off
screenswap load gaming
```

Then right-click → Create shortcut, and set it on your desktop. You can also assign a keyboard shortcut via the shortcut's Properties.

## Layout files

Layouts are stored in `~/.screenswap/` as JSON files. They are not committed to this repository — each user's layouts stay on their own machine.

Example layout file:

```json
{
  "name": "productivity",
  "saved_at": "2026-04-25T10:00:00",
  "monitors": [
    {
      "hardware_id": "SAM711A",
      "width": 3440,
      "height": 1440,
      "position_x": 0,
      "position_y": 0,
      "is_primary": true,
      "refresh_rate": 165,
      "orientation": 0
    }
  ]
}
```

## Contributing

```bash
git clone https://github.com/binsch/screenswap
cd screenswap
pip install -e . pytest pytest-mock
python -m pytest
```

Pull requests welcome.
