@echo off
REM Deploy frontend to Azure Container Apps

echo ========================================
echo  Frontend Deployment Script
echo ========================================

REM Configuration
set REGISTRY=atsalesagents.azurecr.io
set IMAGE_NAME=agent10k-frontend
set TAG=latest
set CONTAINER_APP=agent10k-frontend
set RESOURCE_GROUP=salesAgent

echo.
echo [1/5] Building Docker image...
docker build -t %REGISTRY%/%IMAGE_NAME%:%TAG% .
if errorlevel 1 (
    echo ERROR: Docker build failed
    exit /b 1
)

echo.
echo [2/5] Logging into Azure Container Registry...
az acr login --name atsalesagents
if errorlevel 1 (
    echo ERROR: ACR login failed
    exit /b 1
)

echo.
echo [3/5] Pushing image to registry...
docker push %REGISTRY%/%IMAGE_NAME%:%TAG%
if errorlevel 1 (
    echo ERROR: Docker push failed
    exit /b 1
)

echo.
echo [4/5] Updating Container App...
az containerapp update ^
    --name %CONTAINER_APP% ^
    --resource-group %RESOURCE_GROUP% ^
    --image %REGISTRY%/%IMAGE_NAME%:%TAG%
if errorlevel 1 (
    echo ERROR: Container app update failed
    exit /b 1
)

echo.
echo [5/5] Checking deployment status...
az containerapp show ^
    --name %CONTAINER_APP% ^
    --resource-group %RESOURCE_GROUP% ^
    --query "properties.latestRevisionFqdn" ^
    --output tsv

echo.
echo ========================================
echo  Deployment Complete!
echo ========================================
echo.
echo Frontend URL: https://agent10k-frontend.jollycoast-bd873abf.westus.azurecontainerapps.io
echo.

pause
