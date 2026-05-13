# Scripts to reorganize the project into elite-da-project structure

$root = "c:\Users\Admin\.cursor\projects\empty-window\vn-mst-multi-agent"
$crm = "c:\Users\Admin\.cursor\projects\empty-window\CRM"

Write-Host "Creating directories..."
New-Item -ItemType Directory -Force -Path "$root\frontend"
New-Item -ItemType Directory -Force -Path "$root\backend-api"
New-Item -ItemType Directory -Force -Path "$root\data-pipeline"

Write-Host "Moving React files to frontend/ ..."
$reactFiles = @("src", "index.html", "package.json", "package-lock.json", "tsconfig.json", "tsconfig.node.json", "vite.config.ts")
foreach ($f in $reactFiles) {
    if (Test-Path "$root\$f") { 
        Write-Host "Moving $f"
        Move-Item -Path "$root\$f" -Destination "$root\frontend\" -Force 
    }
}

Write-Host "Moving Python scrapers to data-pipeline/ ..."
$scraperFiles = @("crawler_v1.py", "api_harvester.py", "scrape_mst.py", "scrape_shallow.py", "seed_mst.txt", "data", "crawler_hsctvn.log")
foreach ($f in $scraperFiles) {
    if (Test-Path "$root\$f") { 
        Write-Host "Moving $f"
        Move-Item -Path "$root\$f" -Destination "$root\data-pipeline\" -Force 
    }
}

Write-Host "Copying CRM files to backend-api/ ..."
# Exclude node_modules or .venv if they exist to save time/space
Copy-Item -Path "$crm\*" -Destination "$root\backend-api\" -Recurse -Force -Exclude ".venv", "__pycache__", ".git"

Write-Host "Reorganization complete!"
