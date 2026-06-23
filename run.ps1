<#
.SYNOPSIS
    Development runner script for the AI-Powered Exam Preparation Portal on Windows.
.DESCRIPTION
    Provides automated workflows to manage the Docker database, backend, and frontend.
.EXAMPLE
    .\run.ps1 setup
    .\run.ps1 dev
#>

param (
    [Parameter(Position = 0)]
    [ValidateSet("setup", "db-up", "db-down", "db-logs", "backend-setup", "backend-db-init", "backend-dev", "backend-test", "frontend-setup", "frontend-dev", "frontend-build", "dev", "clean", "help")]
    [string]$Action = "help"
)

$RootDir = Get-Location

function Show-Help {
    Write-Host "======================================================================" -ForegroundColor Cyan
    Write-Host "                AI-Powered Exam Preparation Portal                    " -ForegroundColor Cyan
    Write-Host "                       PowerShell Dev Utility                         " -ForegroundColor Cyan
    Write-Host "======================================================================" -ForegroundColor Cyan
    Write-Host "Available actions:"
    Write-Host "  .\run.ps1 setup            - Run complete project setup (dependencies & env)" -ForegroundColor Yellow
    Write-Host "  .\run.ps1 db-up            - Start PostgreSQL & pgvector container" -ForegroundColor Yellow
    Write-Host "  .\run.ps1 db-down          - Stop PostgreSQL container" -ForegroundColor Yellow
    Write-Host "  .\run.ps1 db-logs          - View live database logs" -ForegroundColor Yellow
    Write-Host "  .\run.ps1 backend-setup    - Install Python venv and backend requirements" -ForegroundColor Yellow
    Write-Host "  .\run.ps1 backend-db-init  - Initialize the database schema and pgvector extension" -ForegroundColor Yellow
    Write-Host "  .\run.ps1 backend-dev      - Run FastAPI dev server (uvicorn)" -ForegroundColor Yellow
    Write-Host "  .\run.ps1 backend-test     - Run the pytest suite" -ForegroundColor Yellow
    Write-Host "  .\run.ps1 frontend-setup   - Install frontend Node dependencies" -ForegroundColor Yellow
    Write-Host "  .\run.ps1 frontend-dev     - Run React Vite dev server" -ForegroundColor Yellow
    Write-Host "  .\run.ps1 frontend-build   - Build frontend production bundles" -ForegroundColor Yellow
    Write-Host "  .\run.ps1 dev              - Launch both backend & frontend in new terminals" -ForegroundColor Yellow
    Write-Host "  .\run.ps1 clean            - Clean cache, venv, and node_modules folders" -ForegroundColor Yellow
    Write-Host "======================================================================" -ForegroundColor Cyan
}

switch ($Action) {
    "help" {
        Show-Help
    }

    "setup" {
        Write-Host "--> Starting Database container..." -ForegroundColor Green
        docker compose up -d

        Write-Host "--> Creating and setting up backend virtual environment..." -ForegroundColor Green
        if (-not (Test-Path "$RootDir\backend\.venv")) {
            cd "$RootDir\backend"
            python -m venv .venv
        }
        cd "$RootDir\backend"
        & .venv\Scripts\pip install -r requirements.txt

        Write-Host "--> Creating backend .env from template if missing..." -ForegroundColor Green
        if (-not (Test-Path "$RootDir\backend\.env")) {
            Copy-Item "$RootDir\backend\.env.example" "$RootDir\backend\.env"
            Write-Host "[!] backend/.env created. Remember to update the GEMINI_API_KEY!" -ForegroundColor Magenta
        }

        Write-Host "--> Setting up frontend dependencies..." -ForegroundColor Green
        cd "$RootDir\frontend"
        npm install

        Write-Host "--> Creating frontend .env from template if missing..." -ForegroundColor Green
        if (-not (Test-Path "$RootDir\frontend\.env")) {
            Copy-Item "$RootDir\frontend\.env.example" "$RootDir\frontend\.env"
        }

        Write-Host "--> Initializing database schemas..." -ForegroundColor Green
        cd "$RootDir\backend"
        & .venv\Scripts\python -m app.init_db

        cd $RootDir
        Write-Host "======================================================================" -ForegroundColor Green
        Write-Host "Setup complete! Run '.\run.ps1 dev' to launch the application." -ForegroundColor Green
        Write-Host "======================================================================" -ForegroundColor Green
    }

    "db-up" {
        Write-Host "Starting database via docker compose..." -ForegroundColor Green
        docker compose up -d
    }

    "db-down" {
        Write-Host "Stopping database container..." -ForegroundColor Green
        docker compose down
    }

    "db-logs" {
        docker compose logs -f db
    }

    "backend-setup" {
        Write-Host "Setting up Python virtual environment..." -ForegroundColor Green
        cd "$RootDir\backend"
        if (-not (Test-Path ".venv")) {
            python -m venv .venv
        }
        & .venv\Scripts\pip install -r requirements.txt
    }

    "backend-db-init" {
        Write-Host "Running database initializer..." -ForegroundColor Green
        cd "$RootDir\backend"
        if (-not (Test-Path ".venv")) {
            Write-Error "Virtual environment not found! Run backend-setup action first."
            exit 1
        }
        & .venv\Scripts\python -m app.init_db
    }

    "backend-dev" {
        Write-Host "Starting FastAPI Dev Server..." -ForegroundColor Green
        cd "$RootDir\backend"
        if (-not (Test-Path ".venv")) {
            Write-Error "Virtual environment not found! Run backend-setup action first."
            exit 1
        }
        & .venv\Scripts\uvicorn app.main:app --reload
    }

    "backend-test" {
        Write-Host "Running pytest test suite..." -ForegroundColor Green
        cd "$RootDir\backend"
        if (-not (Test-Path ".venv")) {
            Write-Error "Virtual environment not found! Run backend-setup action first."
            exit 1
        }
        & .venv\Scripts\pytest -v
    }

    "frontend-setup" {
        Write-Host "Installing npm dependencies in frontend..." -ForegroundColor Green
        cd "$RootDir\frontend"
        npm install
    }

    "frontend-dev" {
        Write-Host "Starting Vite Dev Server..." -ForegroundColor Green
        cd "$RootDir\frontend"
        npm run dev
    }

    "frontend-build" {
        Write-Host "Building frontend assets..." -ForegroundColor Green
        cd "$RootDir\frontend"
        npm run build
    }

    "dev" {
        Write-Host "Launching dev environments in separate windows..." -ForegroundColor Green
        
        # Launch backend uvicorn
        $backendBlock = {
            Set-Location "$using:RootDir\backend"
            Write-Host "=== Backend FastAPI Development Server ===" -ForegroundColor Green
            & .venv\Scripts\uvicorn app.main:app --reload
            Read-Host "Press enter to exit"
        }
        Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendBlock

        # Launch frontend vite
        $frontendBlock = {
            Set-Location "$using:RootDir\frontend"
            Write-Host "=== Frontend React Development Server ===" -ForegroundColor Green
            npm run dev
            Read-Host "Press enter to exit"
        }
        Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendBlock

        Write-Host "FastAPI and Vite started! Check the new windows." -ForegroundColor Green
    }

    "clean" {
        Write-Host "Cleaning directory artifacts..." -ForegroundColor Yellow
        
        # Clean backend
        if (Test-Path "$RootDir\backend\.venv") {
            Remove-Item -Recurse -Force "$RootDir\backend\.venv"
        }
        Get-ChildItem -Path "$RootDir\backend" -Filter "__pycache__" -Recurse | Remove-Item -Recurse -Force
        Get-ChildItem -Path "$RootDir\backend" -Filter ".pytest_cache" -Recurse | Remove-Item -Recurse -Force

        # Clean frontend
        if (Test-Path "$RootDir\frontend\node_modules") {
            Remove-Item -Recurse -Force "$RootDir\frontend\node_modules"
        }
        if (Test-Path "$RootDir\frontend\dist") {
            Remove-Item -Recurse -Force "$RootDir\frontend\dist"
        }

        Write-Host "Clean finished." -ForegroundColor Green
    }
}

cd $RootDir
