# Builds the folder that gets uploaded to Hugging Face. It never copies .env or data/.
$root = "C:\Projects\NEXUS-AI"
$out  = Join-Path $root "hf-space"
Remove-Item -Recurse -Force $out -ErrorAction SilentlyContinue
New-Item -ItemType Directory $out | Out-Null
Copy-Item "$root\backend\app" "$out\app" -Recurse
Copy-Item "$root\backend\requirements.txt" $out
Copy-Item "$root\deploy\Dockerfile.space" "$out\Dockerfile"
Copy-Item "$root\deploy\SPACE_README.md" "$out\README.md"
Get-ChildItem $out -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force
"Built $out"
Get-ChildItem $out | Select-Object Name
