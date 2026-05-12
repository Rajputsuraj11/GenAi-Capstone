# 🚀 Streamlit Cloud Deployment Guide

## 📋 Prerequisites

1. **GitHub Repository**: Your code is already on GitHub
2. **Groq API Keys**: 3 API keys for multi-key setup
3. **Streamlit Account**: Free account at [streamlit.io](https://streamlit.io)

## 🔧 Step 1: Prepare Environment Variables

Since `.streamlit/secrets.toml` is in `.gitignore`, you'll need to set secrets in Streamlit Cloud:

### In Streamlit Cloud Dashboard:
1. Go to your app → **Settings** → **Secrets**
2. Add these secrets:

```toml
GROQ_API_KEY_PII = "your_pii_api_key_here"
GROQ_API_KEY_CONFIDENTIAL = "your_confidential_api_key_here"
GROQ_API_KEY_ABUSIVE = "your_abusive_api_key_here"
```

## 📦 Step 2: Deploy to Streamlit Cloud

### Option A: Via GitHub (Recommended)
1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click **"New app"**
3. **Repository**: `Rajputsuraj11/GenAi-Capstone`
4. **Branch**: `main`
5. **Main file path**: `app.py`
6. Click **"Deploy"**

### Option B: Via CLI
```bash
pip install streamlit
streamlit run app.py  # Test locally first
streamlit deploy  # Deploy to cloud
```

## ⚙️ Step 3: Configure App Settings

In Streamlit Cloud dashboard:

### Basic Settings:
- **App name**: `PDF Compliance Scanner`
- **App URL**: `pdf-compliance-scanner`
- **Python version**: `3.10+`

### Advanced Settings:
- **Memory**: `2 GB` (minimum for PDF processing)
- **CPU**: `1 core` (minimum)
- **Timeout**: `30 minutes` (for large PDFs)

## 🔍 Step 4: Verify Deployment

1. **Check logs**: Look for any import errors
2. **Test functionality**: Upload a small PDF
3. **Monitor API usage**: Check Groq dashboard

## 🛠️ Common Issues & Solutions

### Issue: "Module not found" errors
**Solution**: Ensure all dependencies are in `requirements.txt`

### Issue: "API key not configured"
**Solution**: Add secrets in Streamlit Cloud dashboard

### Issue: "Memory limit exceeded"
**Solution**: 
- Increase memory allocation
- Optimize PDF processing for large files
- Add file size limits

### Issue: "Slow performance"
**Solution**:
- Upgrade to paid plan for more resources
- Use parallel processing (already implemented)
- Add caching for repeated scans

## 📊 Performance Tips

1. **File Size Limits**: Add max file size (10-50MB)
2. **Page Limits**: Warn users about large documents
3. **Caching**: Cache results for repeated scans
4. **Monitoring**: Set up error tracking

## 🔒 Security Considerations

- ✅ API keys stored in Streamlit secrets
- ✅ No sensitive data in code
- ✅ PDF files processed temporarily
- ✅ Rate limiting implemented
- ✅ Input validation added

## 📈 Scaling Options

### Free Tier Limits:
- **Memory**: 1 GB
- **CPU**: 1 core
- **Monthly hours**: 30 hours

### Paid Tier Benefits:
- **Memory**: Up to 8 GB
- **CPU**: Up to 4 cores
- **No hourly limits**
- **Priority support**

## 🎯 Next Steps

1. Deploy to Streamlit Cloud
2. Test with various PDF types
3. Monitor performance and usage
4. Add user feedback collection
5. Consider paid plan for production use

---

**Your app URL will be**: `https://pdf-compliance-scanner.streamlit.app`
