from pathlib import Path
root = Path(__file__).parent
views = (root / 'backend/core/views.py').read_text(encoding='utf-8')
frontend = (root / 'frontend/src/App.tsx').read_text(encoding='utf-8')
models = (root / 'backend/core/models.py').read_text(encoding='utf-8')
checks = {
    'active backend has no automatic mock completion': 'mock-' not in views and 'opportunity.status = "COMPLETED"' not in views,
    'claim endpoint requires verified provider state': 'opportunity.status not in {"VERIFIED", "GRANTED"}' in views,
    'callback requires completed status and HMAC': 'event_status != "COMPLETED"' in views and 'hmac.new(' in views,
    'callback requires started opportunity': 'opportunity.status != "AD_STARTED"' in views,
    'frontend calls status before claim': frontend.index('/status/') < frontend.index('/economy/claim-reward/'),
    'frontend checks verified state before claim': "adStatus.verified === true && adStatus.status === 'VERIFIED'" in frontend,
    'reward event id is unique in model': 'event_id=models.CharField(max_length=128,unique=True)' in models,
    'opportunity lifecycle choices include all required states': all(x in models for x in ['OFFERED','REQUESTED','AD_STARTED','AD_COMPLETED','VERIFYING','VERIFIED','GRANTED']),
}
for label, passed in checks.items():
    print(('PASS' if passed else 'FAIL') + ' | ' + label)
if not all(checks.values()):
    raise SystemExit(1)
