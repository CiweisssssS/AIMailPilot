# Deployment Guide

This guide covers deploying the AI Mail Pilot application to Render (backend) and Vercel (frontend).

## Architecture

- **Backend**: FastAPI (Python) on Render
- **Frontend**: React/TypeScript on Vercel
- **Database**: Supabase (PostgreSQL)

## Backend Deployment (Render)

### Prerequisites
- Render account
- GitHub repository connected to Render

### Steps

1. **Create a new Web Service** in Render
   - Connect your GitHub repository
   - Select the repository branch

2. **Configure Build Settings**:
   - **Root Directory**: (leave empty)
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

3. **Set Environment Variables**:
   ```
   OPENAI_API_KEY=your_openai_api_key
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
   SUPABASE_KEY=your_anon_key
   SESSION_SECRET=your_random_session_secret
   GOOGLE_CLIENT_ID=your_google_client_id
   GOOGLE_CLIENT_SECRET=your_google_client_secret
   GOOGLE_REDIRECT_URI=https://your-render-app.onrender.com/auth/callback
   PORT=10000
   ```

4. **Deploy**
   - Render will automatically build and deploy
   - Note your deployment URL (e.g., `https://your-app.onrender.com`)

5. **Verify Deployment**:
   - Check health endpoint: `https://your-app.onrender.com/health`
   - Should return: `{"ok": true}`

## Frontend Deployment (Vercel)

### Prerequisites
- Vercel account
- GitHub repository connected to Vercel

### Steps

1. **Import Project** in Vercel
   - Connect your GitHub repository
   - Select the repository

2. **Configure Project Settings**:
   - **Root Directory**: `client`
   - **Framework Preset**: Vite
   - **Build Command**: `npm run build` (or `pnpm build` / `yarn build`)
   - **Output Directory**: `dist`

3. **Set Environment Variables**:
   ```
   NEXT_PUBLIC_API_BASE=https://your-render-app.onrender.com
   NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
   NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
   ```

4. **Deploy**
   - Vercel will automatically build and deploy
   - Your app will be available at `https://your-app.vercel.app`

## Post-Deployment

1. **Update CORS in Backend** (if needed):
   - If your Vercel URL changes, update the CORS origins in `app/main.py`
   - Or use environment variables for dynamic CORS configuration

2. **Test Endpoints**:
   - Backend health: `GET https://your-render-app.onrender.com/health`
   - Frontend should connect to backend API

3. **Monitor Logs**:
   - Render: View logs in Render dashboard
   - Vercel: View logs in Vercel dashboard

## Troubleshooting

### Backend Issues
- **Build fails**: Check `requirements.txt` is at repo root
- **Import errors**: Verify Python path includes `app/` directory
- **Port binding**: Ensure using `$PORT` environment variable

### Frontend Issues
- **API connection fails**: Verify `NEXT_PUBLIC_API_BASE` points to Render URL
- **CORS errors**: Check CORS configuration in `app/main.py` includes Vercel domain

### Database Issues
- **Connection errors**: Verify Supabase credentials are correct
- **Table not found**: Run database migrations from `database/schema.sql`
