AWA PROVIDER-FREE HINT PATCH (TYPE-SAFE)

Apply from the project root:
  Expand-Archive "$env:USERPROFILE\Downloads\AWA_PROVIDER_FREE_HINT_PATCH_FIXED.zip" "$env:TEMP\AWA_PROVIDER_FREE_HINT_PATCH_FIXED" -Force
  Copy-Item "$env:TEMP\AWA_PROVIDER_FREE_HINT_PATCH_FIXED\frontend\src\App.tsx" ".\frontend\src\App.tsx" -Force

In .env set:
  AD_PROVIDER=disabled
  AD_PROVIDER_ADAPTER=

Then rebuild:
  docker compose up -d --build

This makes HINT a free gameplay feature. It does not show ads, create ad opportunities,
claim ad rewards, or fabricate ad completions. Other ad-funded placements remain disabled.
Do not delete Docker volumes.
