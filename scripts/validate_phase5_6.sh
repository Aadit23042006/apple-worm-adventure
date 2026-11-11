#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../backend"
python manage.py check
python manage.py migrate --check
python manage.py validate_game_levels
python manage.py test
