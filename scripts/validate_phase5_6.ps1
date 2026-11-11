$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..\backend")
python manage.py check
python manage.py migrate --check
python manage.py validate_game_levels
python manage.py test
