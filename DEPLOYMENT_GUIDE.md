# Deployment Guide - Persona & Job Details Features

**Deployment Date:** November 21, 2025  
**Commit:** e95189d  
**Features:** Job Details View + Intelligent Persona-Based Pitch Generation

---

## 🎯 What's Being Deployed

### Feature 1: Job Details View
- New `/job/:jobId` route showing detailed job status
- Real-time progress tracking with company-level status
- Direct navigation to company insights
- Sales-friendly status labels

### Feature 2: Intelligent Pitch Generation
- Smart persona assignment (CISO for security, CTO for tech, CFO for finance, etc.)
- Natural email style matching sales team examples
- Short, conversational tone (150-200 words)
- No corporate buzzwords

---

## 🚀 Deployment Steps

### Option 1: Standard Deployment (Recommended)

```bash
# 1. Pull the latest changes
git pull origin main

# 2. Restart backend (if already running)
# Stop the backend with Ctrl+C, then:
cd c:\Projects\10K
.venv\Scripts\python.exe -m uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload

# 3. Rebuild and restart frontend
cd frontend
npm install  # Only if needed
npm run build
npm run dev

# 4. Verify deployment
# - Backend: http://127.0.0.1:8000/docs
# - Frontend: http://localhost:3000
```

### Option 2: Full Restart (Clean Deployment)

```bash
# Stop all services
# Press Ctrl+C in all terminal windows

# Start all services fresh
cd c:\Projects\10K
start_all.bat
```

---

## ✅ Verification Checklist

### Backend Tests
- [ ] API is running at http://127.0.0.1:8000
- [ ] Check `/health` endpoint responds
- [ ] Unit tests pass: `.venv\Scripts\python.exe test_persona_mapping.py`

### Frontend Tests
- [ ] React app loads at http://localhost:3000
- [ ] Navigate to Analysis Queue → "All Analysis Jobs" tab
- [ ] Click "View Details →" on any job card
- [ ] Verify job details page shows company list with statuses
- [ ] Click "View Insights" on a completed company
- [ ] Verify it navigates to Company Insights and auto-expands

### Pitch Generation Tests
- [ ] Run a new analysis on a tech company
- [ ] Check generated pitch in "Top Pitches" page
- [ ] Verify persona is appropriate (e.g., CISO for cybersecurity, CTO for AI/cloud)
- [ ] Check email style is conversational and brief (150-200 words)
- [ ] Ensure no phrases like "I hope this finds you well" or "cutting-edge solution"

---

## 🔄 Rollback Instructions

If something goes wrong, you can instantly rollback:

### Quick Rollback
```bash
# Rollback to previous version
git reset --hard HEAD~1

# Restart services
start_all.bat
```

### Rollback to Backup Branch
```bash
# Switch to backup branch
git checkout backup-before-persona-and-jobs-20251121-165743

# Restart services
start_all.bat

# When ready to return to new version:
git checkout main
```

### Emergency: Restore Specific Files
```bash
# Restore only pitch generation (keep job details)
git checkout HEAD~1 -- src/nodes/solution_matcher/pitch_writer.py
git checkout HEAD~1 -- src/nodes/solution_matcher/fit_scorer.py

# OR restore only job details (keep pitch generation)
git checkout HEAD~1 -- frontend/src/pages/JobDetails.tsx
git checkout HEAD~1 -- frontend/src/App.tsx
git checkout HEAD~1 -- frontend/src/pages/AnalysisQueue.tsx
```

---

## 📊 Monitoring

### What to Watch For

**First 24 Hours:**
- Monitor pitch generation quality in "Top Pitches" page
- Check that personas are assigned correctly
- Verify job details page loads without errors
- Watch for any frontend console errors

**Key Metrics:**
- Pitch persona distribution (should see variety: CISO, CTO, CFO, etc.)
- Email tone quality (conversational vs corporate)
- Job details page load time
- Navigation between job details and company insights

### Known Issues
None expected. All features tested and working.

---

## 📝 Testing Scenarios

### Scenario 1: Cybersecurity Company
1. Analyze a cybersecurity company (e.g., Palo Alto Networks)
2. Check generated pitch
3. **Expected:** Persona should be "CISO" (not CFO)
4. **Expected:** Email should be brief and direct

### Scenario 2: Tech Company
1. Analyze a cloud/AI company (e.g., Microsoft, Amazon)
2. Check generated pitch
3. **Expected:** Persona should be "CTO"
4. **Expected:** Email mentions their 10-K insights naturally

### Scenario 3: Job Details Navigation
1. Start a batch analysis (3-5 companies)
2. Go to "All Analysis Jobs" tab
3. Click "View Details →" on the active job
4. **Expected:** See all companies with status indicators
5. Click "View Insights" on a completed company
6. **Expected:** Navigate to insights page with auto-expanded details

---

## 🆘 Troubleshooting

### Issue: Pitch still showing old style
**Solution:** Clear browser cache, restart backend, regenerate pitches

### Issue: Job details page shows 404
**Solution:** 
```bash
cd frontend
npm run build
```

### Issue: Persona still defaulting to CFO
**Solution:** Check that fit_scorer.py includes categorize_product() function

### Issue: Frontend not updating
**Solution:**
```bash
cd frontend
rm -rf node_modules/.vite
npm run dev
```

---

## 📞 Support

If issues persist after rollback:
1. Check git status: `git status`
2. Verify you're on main branch: `git branch`
3. Check commit history: `git log --oneline -5`
4. Review application logs in terminal windows

---

## ✨ Success Criteria

Deployment is successful when:
- ✅ All verification tests pass
- ✅ Pitches show diverse personas (not all CFO)
- ✅ Email style is natural and conversational
- ✅ Job details page navigates smoothly
- ✅ No console errors in frontend
- ✅ No backend errors in logs

**Estimated deployment time:** 5-10 minutes  
**Estimated verification time:** 10-15 minutes  
**Total:** ~20-25 minutes
