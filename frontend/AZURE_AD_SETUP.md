# Azure AD Authentication Setup Guide

This guide will help you configure Azure Active Directory authentication for the 10K Insight application.

## Prerequisites

- An Azure subscription
- Administrator access to Azure Active Directory

## Step 1: Register Application in Azure AD

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to **Azure Active Directory** > **App registrations**
3. Click **+ New registration**
4. Configure the application:
   - **Name**: `10K Insight Application` (or your preferred name)
   - **Supported account types**: 
     - Choose "Accounts in this organizational directory only" for single tenant
     - Or "Accounts in any organizational directory" for multi-tenant
   - **Redirect URI**: 
     - Platform: Single-page application (SPA)
     - URI: `http://localhost:5173` (for development)
5. Click **Register**

## Step 2: Configure Authentication

1. In your app registration, go to **Authentication**
2. Under **Single-page application**, add redirect URIs:
   - Development: `http://localhost:5173`
   - Production: `https://your-production-domain.com`
3. Under **Implicit grant and hybrid flows**, ensure:
   - ✅ Access tokens (used for implicit flows)
   - ✅ ID tokens (used for implicit and hybrid flows)
4. Click **Save**

## Step 3: Configure API Permissions (Optional)

1. Go to **API permissions**
2. The following permissions are pre-configured:
   - `User.Read` - Read user profile
3. If you need additional permissions, click **+ Add a permission**
4. Click **Grant admin consent** (requires admin privileges)

## Step 4: Get Configuration Values

From your app registration overview page, note down:

1. **Application (client) ID**: Found on the Overview page
2. **Directory (tenant) ID**: Found on the Overview page
3. **Authority URL**: `https://login.microsoftonline.com/{tenant-id}`
   - For multi-tenant: `https://login.microsoftonline.com/common`

## Step 5: Configure Environment Variables

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Update the following variables in `.env`:
   ```env
   VITE_AZURE_CLIENT_ID=your-application-client-id-here
   VITE_AZURE_AUTHORITY=https://login.microsoftonline.com/your-tenant-id-here
   VITE_AZURE_REDIRECT_URI=http://localhost:5173
   ```

3. Replace the placeholder values with your actual Azure AD values

## Step 6: Install Dependencies

```bash
npm install
```

The required packages are:
- `@azure/msal-browser` - Microsoft Authentication Library for browser
- `@azure/msal-react` - React wrapper for MSAL

## Step 7: Run the Application

```bash
npm run dev
```

The application will be available at `http://localhost:5173`

## Testing Authentication

1. Open the application in your browser
2. You should be redirected to the login page
3. Click **Sign in with Microsoft**
4. A popup will appear with Microsoft login
5. Enter your Microsoft credentials
6. Grant consent if prompted
7. You should be redirected to the dashboard

## Troubleshooting

### "AADSTS50011: The redirect URI specified in the request does not match"
- Make sure the redirect URI in `.env` matches exactly what's registered in Azure AD
- Check for trailing slashes and http vs https

### "AADSTS700016: Application not found in the directory"
- Verify the Client ID is correct
- Ensure you're in the right Azure AD tenant

### "Interaction required" error
- Clear your browser cache and cookies
- Try using incognito/private mode
- Check if popup blockers are preventing the auth popup

### Users cannot sign in
- Verify API permissions are granted
- Check if the app is enabled in Azure AD
- Ensure users are assigned to the application (if assignment is required)

## Production Deployment

For production deployment:

1. Update redirect URIs in Azure AD to include your production domain
2. Update `.env` with production values:
   ```env
   VITE_AZURE_REDIRECT_URI=https://your-production-domain.com
   ```
3. Build the application:
   ```bash
   npm run build
   ```

## Security Best Practices

1. **Never commit `.env` files** - They contain sensitive information
2. **Use different app registrations** for dev/staging/production
3. **Enable Conditional Access policies** in Azure AD for additional security
4. **Regularly review** API permissions and granted consents
5. **Enable MFA** (Multi-Factor Authentication) for all users

## Additional Resources

- [MSAL.js Documentation](https://github.com/AzureAD/microsoft-authentication-library-for-js)
- [Azure AD App Registration](https://learn.microsoft.com/en-us/azure/active-directory/develop/quickstart-register-app)
- [MSAL React Guide](https://github.com/AzureAD/microsoft-authentication-library-for-js/tree/dev/lib/msal-react)

## Support

For issues related to Azure AD authentication, please contact your Azure administrator or refer to the Microsoft documentation.
