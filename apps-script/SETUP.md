# Gmail Add-on Setup Instructions

## Step 1: Get Your Replit Backend URL

1. In this Replit, click the "Run" button to start the server
2. Once running, look for the preview URL (usually shown at top of the webview)
3. Copy that URL - it will look like: `https://[repl-name].[username].replit.dev`

## Step 2: Update Config.gs

1. Open `apps-script/Config.gs` 
2. Replace `YOUR_REPL_NAME.YOUR_USERNAME.replit.dev` with your actual Replit URL
3. Save the file

## Step 3: Create Google Apps Script Project

1. Go to [script.google.com](https://script.google.com)
2. Click "+ New project"
3. Name it "AI Email Assistant"

## Step 4: Copy All Files

Copy these files from `apps-script/` folder into your Apps Script project:

1. **Config.gs** - Backend configuration
2. **Code.gs** - Main entry point
3. **BackendClient.gs** - API client
4. **SidebarCard.gs** - Main UI
5. **ChatCard.gs** - Q&A interface
6. **SettingsCard.gs** - Settings UI
7. **appsscript.json** - Manifest (click gear icon ⚙️ to access)

## Step 5: Enable Gmail API

1. In Apps Script, click "Services" (+) on the left sidebar
2. Find and add "Gmail API v1"
3. Click "Add"

## Step 6: Deploy as Gmail Add-on

1. Click "Deploy" → "Test deployments"
2. Click "Install"
3. Select your Gmail account
4. Grant permissions when prompted

## Step 7: Test the Add-on

1. Open Gmail
2. Open any email
3. Look for the add-on icon in the right sidebar
4. Click it to see your AI Email Assistant!

## Features

### Main Sidebar
- **Priority Classification**: P1/P2/P3 with score and reasons
- **Summary**: AI-generated email summary
- **Tasks**: Extracted action items with owners and due dates
- **Timeline**: Thread message history

### Chat Interface
- Click "💬 Ask Questions" to query the email thread
- Get AI-powered answers with source citations

### Settings
- Click "⚙️ Manage Keywords" to add personalized priority keywords
- Keywords affect priority scoring

## Troubleshooting

**"Failed to process email thread"**
- Check that your Replit backend is running
- Verify the BACKEND_URL in Config.gs is correct
- Check Apps Script execution logs (View → Logs)

**"Backend API error"**
- Make sure the FastAPI server is running on Replit
- Test the API endpoint: `https://your-url.replit.dev/healthz`
- Check CORS configuration in the backend

**Permissions issues**
- Re-authorize the add-on
- Check OAuth scopes in appsscript.json

## Support

For issues with:
- **Backend**: Check `/app` folder and FastAPI logs
- **Frontend**: Check Apps Script execution logs
- **API**: Test endpoints at `https://your-url.replit.dev/docs`
