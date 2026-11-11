from pathlib import Path

source = Path('frontend/src/App.tsx').read_text(encoding='utf-8')
checks = {
    'Sound preference defaults enabled and restores saved state': "useState(() => localStorage.getItem('veloop_sound_enabled') !== 'false')" in source,
    'Sound preference is persisted': "localStorage.setItem('veloop_sound_enabled', String(soundOn))" in source,
    'Sound Off suppresses effects': 'if (!soundOn) return' in source,
    'Sound ON/OFF control is rendered': 'Sound On' in source and 'Sound Off' in source and 'onClick={toggleSound}' in source,
    'Sound control exposes accessible pressed state': 'aria-pressed={soundOn}' in source,
    'Button click feedback is wired': 'onClickCapture={(event)' in source and "target.closest('button')" in source,
    'Worm movement feedback is wired': 'if (ate < 0) sound(420)' in source,
    'Hint feedback is wired': 'sound(800)' in source,
    'Reward feedback is wired': 'sound(1000)' in source,
    'Failure feedback is wired': 'sound(130)' in source,
    'Apple collection feedback is wired': 'sound(740)' in source,
    'Level completion feedback is wired': 'sound(880)' in source,
    'Music preference is persisted': "localStorage.setItem('veloop_music_enabled', String(musicOn))" in source,
    'Music auto-start respects saved preference': 'if (musicOn) startMusic()' in source,
}
for label, ok in checks.items():
    print(('PASS' if ok else 'FAIL') + ': ' + label)
print(f'RESULT: {sum(checks.values())}/{len(checks)} audio preference checks passed')
raise SystemExit(0 if all(checks.values()) else 1)
