# Quick Deployment Fix

## Problem
Frontend shows "Network Error" when deployed to Azure Container Apps.

## Solution
The frontend needs to know the backend URL at **runtime**, not build time.

## Required Steps

### 1. Rebuild Frontend (One Time)
```bash
cd frontend
docker build -t <your-registry>/agent10k-frontend:latest .
docker push <your-registry>/agent10k-frontend:latest
```

### 2. Set Environment Variable on Frontend Container
```bash
# Get backend URL first
BACKEND_URL=$(az containerapp show \
  --name agent10k-backend \
  --resource-group rg-10k-insight \
  --query properties.configuration.ingress.fqdn \
  --output tsv)

# Update frontend with backend URL
az containerapp update \
  --name agent10k-frontend \
  --resource-group rg-10k-insight \
  --set-env-vars \
    VITE_API_URL="https://$BACKEND_URL"
```

### 3. Update Backend CORS
```bash
# Get frontend URL
FRONTEND_URL=$(az containerapp show \
  --name agent10k-frontend \
  --resource-group rg-10k-insight \
  --query properties.configuration.ingress.fqdn \
  --output tsv)

# Update backend CORS
az containerapp update \
  --name agent10k-backend \
  --resource-group rg-10k-insight \
  --set-env-vars \
    CORS_ORIGINS="https://$FRONTEND_URL,http://localhost:3000"
```

## Verify
1. Open frontend URL in browser
2. Open DevTools Console (F12)
3. Look for: `API Base URL: https://agent10k-backend...`
4. Should match your backend URL

## Still Having Issues?

### Check Backend is Running
```bash
curl https://agent10k-backend.<region>.azurecontainerapps.io/health
```

### View Frontend Logs
```bash
az containerapp logs show --name agent10k-frontend --follow
```

Should see: `Generated config.js with VITE_API_URL=https://...`

### View Backend Logs
```bash
az containerapp logs show --name agent10k-backend --follow
```

Look for CORS configuration message.

## Full Documentation
- [AZURE_DEPLOYMENT.md](AZURE_DEPLOYMENT.md) - Complete deployment guide
- [FRONTEND_NETWORK_ERROR_FIX.md](FRONTEND_NETWORK_ERROR_FIX.md) - Detailed technical explanation
