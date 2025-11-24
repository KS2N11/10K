# Azure Container Apps Deployment Guide

This guide explains how to deploy the 10K Insight Agent to Azure Container Apps.

## Architecture

The application consists of three containers:
- **Frontend**: React + Vite application served by Nginx
- **Backend**: FastAPI application
- **Database**: PostgreSQL (can use Azure Database for PostgreSQL or containerized)

## Prerequisites

1. Azure CLI installed and logged in
2. Docker installed locally
3. Azure Container Registry (ACR) or Docker Hub account

## Environment Variables

### Frontend Container

The frontend requires the following environment variable to be set in Azure Container Apps:

| Variable | Description | Example Value |
|----------|-------------|---------------|
| `VITE_API_URL` | Backend API URL | `https://agent10k-backend.ambitiousground-7c789fbb.eastus.azurecontainerapps.io` |

**Important**: The frontend uses runtime configuration, which means you can change the API URL without rebuilding the container. The `VITE_API_URL` environment variable is injected into the running container.

### Backend Container

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `OPENAI_API_KEY` | OpenAI API key | No* |
| `GROQ_API_KEY` | Groq API key | No* |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key | No* |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint | No* |
| `AZURE_OPENAI_DEPLOYMENT` | Azure OpenAI deployment name | No* |
| `AZURE_OPENAI_API_VERSION` | Azure OpenAI API version | No* |
| `CORS_ORIGINS` | Allowed CORS origins (comma-separated) | Yes |
| `ENVIRONMENT` | Environment name (development/production) | Yes |

*At least one LLM provider (OpenAI, Groq, or Azure OpenAI) is required.

**Example CORS_ORIGINS**:
```
https://agent10k-frontend.ambitiousground-7c789fbb.eastus.azurecontainerapps.io,http://localhost:3000
```

## Deployment Steps

### 1. Build and Push Container Images

#### Option A: Using Azure Container Registry

```bash
# Login to Azure
az login

# Create resource group (if not exists)
az group create --name rg-10k-insight --location eastus

# Create Azure Container Registry
az acr create --resource-group rg-10k-insight --name acr10kinsight --sku Basic

# Login to ACR
az acr login --name acr10kinsight

# Build and push backend
docker build -t acr10kinsight.azurecr.io/agent10k-backend:latest .
docker push acr10kinsight.azurecr.io/agent10k-backend:latest

# Build and push frontend
cd frontend
docker build -t acr10kinsight.azurecr.io/agent10k-frontend:latest .
docker push acr10kinsight.azurecr.io/agent10k-frontend:latest
```

#### Option B: Using Docker Hub

```bash
# Login to Docker Hub
docker login

# Build and push backend
docker build -t yourusername/agent10k-backend:latest .
docker push yourusername/agent10k-backend:latest

# Build and push frontend
cd frontend
docker build -t yourusername/agent10k-frontend:latest .
docker push yourusername/agent10k-frontend:latest
```

### 2. Create Azure Container Apps Environment

```bash
# Install Container Apps extension
az extension add --name containerapp --upgrade

# Create Container Apps environment
az containerapp env create \
  --name env-10k-insight \
  --resource-group rg-10k-insight \
  --location eastus
```

### 3. Create PostgreSQL Database

#### Option A: Azure Database for PostgreSQL

```bash
az postgres flexible-server create \
  --resource-group rg-10k-insight \
  --name psql-10k-insight \
  --location eastus \
  --admin-user adminuser \
  --admin-password 'YourSecurePassword123!' \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --storage-size 32 \
  --version 14

# Get connection string
# Format: postgresql://adminuser:YourSecurePassword123!@psql-10k-insight.postgres.database.azure.com:5432/postgres?sslmode=require
```

#### Option B: Containerized PostgreSQL

Deploy a PostgreSQL container (not recommended for production):

```bash
az containerapp create \
  --name postgres \
  --resource-group rg-10k-insight \
  --environment env-10k-insight \
  --image postgres:15-alpine \
  --target-port 5432 \
  --ingress internal \
  --env-vars \
    POSTGRES_DB=tenk_insight \
    POSTGRES_USER=postgres \
    POSTGRES_PASSWORD=postgres
```

### 4. Deploy Backend Container

```bash
az containerapp create \
  --name agent10k-backend \
  --resource-group rg-10k-insight \
  --environment env-10k-insight \
  --image acr10kinsight.azurecr.io/agent10k-backend:latest \
  --target-port 8000 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 3 \
  --cpu 1.0 \
  --memory 2.0Gi \
  --env-vars \
    DATABASE_URL="postgresql://adminuser:YourSecurePassword123!@psql-10k-insight.postgres.database.azure.com:5432/postgres?sslmode=require" \
    GROQ_API_KEY="your-groq-api-key" \
    ENVIRONMENT=production \
    CORS_ORIGINS="https://agent10k-frontend.ambitiousground-7c789fbb.eastus.azurecontainerapps.io"

# Get backend URL
az containerapp show \
  --name agent10k-backend \
  --resource-group rg-10k-insight \
  --query properties.configuration.ingress.fqdn \
  --output tsv
# Output example: agent10k-backend.ambitiousground-7c789fbb.eastus.azurecontainerapps.io
```

### 5. Deploy Frontend Container

**Important**: Set `VITE_API_URL` to the backend URL from step 4 (with `https://` prefix).

```bash
BACKEND_URL="https://agent10k-backend.ambitiousground-7c789fbb.eastus.azurecontainerapps.io"

az containerapp create \
  --name agent10k-frontend \
  --resource-group rg-10k-insight \
  --environment env-10k-insight \
  --image acr10kinsight.azurecr.io/agent10k-frontend:latest \
  --target-port 80 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 2 \
  --cpu 0.5 \
  --memory 1.0Gi \
  --env-vars \
    VITE_API_URL="$BACKEND_URL"

# Get frontend URL
az containerapp show \
  --name agent10k-frontend \
  --resource-group rg-10k-insight \
  --query properties.configuration.ingress.fqdn \
  --output tsv
```

### 6. Update CORS Origins

After deploying the frontend, update the backend's CORS origins to include the frontend URL:

```bash
FRONTEND_URL="https://agent10k-frontend.ambitiousground-7c789fbb.eastus.azurecontainerapps.io"

az containerapp update \
  --name agent10k-backend \
  --resource-group rg-10k-insight \
  --set-env-vars \
    CORS_ORIGINS="$FRONTEND_URL,http://localhost:3000"
```

## Updating Containers

### Update Backend

```bash
# Rebuild and push new image
docker build -t acr10kinsight.azurecr.io/agent10k-backend:latest .
docker push acr10kinsight.azurecr.io/agent10k-backend:latest

# Update container app (triggers new revision)
az containerapp update \
  --name agent10k-backend \
  --resource-group rg-10k-insight \
  --image acr10kinsight.azurecr.io/agent10k-backend:latest
```

### Update Frontend

```bash
# Rebuild and push new image
cd frontend
docker build -t acr10kinsight.azurecr.io/agent10k-frontend:latest .
docker push acr10kinsight.azurecr.io/agent10k-frontend:latest

# Update container app
az containerapp update \
  --name agent10k-frontend \
  --resource-group rg-10k-insight \
  --image acr10kinsight.azurecr.io/agent10k-frontend:latest
```

### Update Environment Variables Only

If you only need to change the API URL (without rebuilding):

```bash
# Update backend URL
az containerapp update \
  --name agent10k-frontend \
  --resource-group rg-10k-insight \
  --set-env-vars \
    VITE_API_URL="https://new-backend-url.azurecontainerapps.io"
```

## Troubleshooting

### Frontend shows "Network Error"

This error occurs when the frontend cannot connect to the backend. Check:

1. **Verify VITE_API_URL is set correctly**:
   ```bash
   az containerapp show \
     --name agent10k-frontend \
     --resource-group rg-10k-insight \
     --query properties.template.containers[0].env
   ```
   
2. **Check if backend is running**:
   ```bash
   BACKEND_URL=$(az containerapp show \
     --name agent10k-backend \
     --resource-group rg-10k-insight \
     --query properties.configuration.ingress.fqdn \
     --output tsv)
   
   curl https://$BACKEND_URL/health
   ```

3. **Verify CORS is configured**:
   - Backend CORS_ORIGINS must include the frontend URL
   - Check backend logs for CORS errors

4. **Check browser console**:
   - Open browser DevTools (F12)
   - Look for the "API Base URL" console log
   - Verify it matches your backend URL

### Backend container not starting

Check logs:
```bash
az containerapp logs show \
  --name agent10k-backend \
  --resource-group rg-10k-insight \
  --follow
```

Common issues:
- Invalid DATABASE_URL
- Missing required LLM API keys
- Database connection failures

### Database connection issues

1. For Azure Database for PostgreSQL:
   - Ensure firewall rules allow Container Apps
   - Add rule: Azure services and resources
   
2. For containerized PostgreSQL:
   - Check if postgres container is running
   - Verify internal networking

## Monitoring

### View Logs

```bash
# Backend logs
az containerapp logs show \
  --name agent10k-backend \
  --resource-group rg-10k-insight \
  --follow

# Frontend logs
az containerapp logs show \
  --name agent10k-frontend \
  --resource-group rg-10k-insight \
  --follow
```

### View Metrics

```bash
# Backend metrics
az monitor metrics list \
  --resource /subscriptions/{subscription-id}/resourceGroups/rg-10k-insight/providers/Microsoft.App/containerApps/agent10k-backend \
  --metric Requests \
  --start-time 2025-11-11T00:00:00Z \
  --end-time 2025-11-11T23:59:59Z
```

## Cost Optimization

1. **Use consumption-only replicas**: Set min-replicas to 0 for dev/staging
2. **Right-size resources**: Start with minimum CPU/memory and scale up if needed
3. **Use Azure Database for PostgreSQL Flexible Server**: Burstable tier for dev/staging
4. **Enable auto-scaling**: Configure based on HTTP request count or CPU usage

## Security Best Practices

1. **Use Azure Key Vault** for secrets (API keys, database passwords)
2. **Enable Container Apps authentication** for admin endpoints
3. **Use managed identities** for Azure resource access
4. **Enable HTTPS only** (already enabled by default)
5. **Restrict CORS origins** to known frontend URLs only
6. **Use environment-specific configurations** (separate dev/staging/prod)

## Next Steps

- Set up Azure Monitor for comprehensive monitoring
- Configure Application Insights for detailed telemetry
- Implement automated deployments with GitHub Actions
- Set up Azure Key Vault for secret management
- Configure custom domain names
- Enable auto-scaling based on metrics
