# PostgreSQL Setup Guide

## 🎯 Overview

This guide shows you how to set up PostgreSQL for your attribution platform on Streamlit Cloud.

**Why PostgreSQL?**
- ✅ Data persists forever (never lost on reboot)
- ✅ Production-ready and scalable
- ✅ Free tier available (Supabase, Neon, Railway)
- ✅ Better performance than SQLite
- ✅ Auto-backups included

---

## 🚀 Quick Setup (15 minutes)

### Step 1: Create Free PostgreSQL Database

**Option A: Supabase (Recommended)**

1. Go to https://supabase.com/
2. Click **"Start your project"**
3. Sign in with GitHub
4. Click **"New project"**
5. Fill in:
   - **Name**: `attribution-mvp`
   - **Database Password**: Create a strong password (save it!)
   - **Region**: Choose closest to you
6. Click **"Create new project"**
7. Wait 2 minutes for database to provision

**Get Connection String:**
1. In your Supabase project, go to **Settings** → **Database**
2. Scroll to **Connection string** section
3. Select **"URI"**
4. Copy the connection string (looks like `postgresql://postgres:[YOUR-PASSWORD]@...`)
5. Replace `[YOUR-PASSWORD]` with your actual password

**Option B: Neon**

1. Go to https://neon.tech/
2. Sign up (free tier: 0.5 GB storage)
3. Create project → Get connection string

**Option C: Railway**

1. Go to https://railway.app/
2. Sign up (free tier: $5 credit/month)
3. New Project → PostgreSQL → Get connection string

---

### Step 2: Configure Streamlit Cloud

1. Go to https://share.streamlit.io/
2. Find your **attribution-mvp** app
3. Click **"⚙️ Settings"** → **"Secrets"**
4. Add this configuration:

```toml
[database]
url = "postgresql://postgres:YOUR_PASSWORD@db.xxx.supabase.co:5432/postgres"

[admin]
email = "your-email@company.com"
password = "your-secure-password"
name = "Your Name"

[organization]
name = "Your Company"
```

**Important**: Replace these values:
- `url`: Your actual PostgreSQL connection string from Step 1
- `email`, `password`, `name`: Your admin credentials

5. Click **"Save"**
6. Click **"Reboot app"**

---

### Step 3: Verify It Works

1. Wait 2-3 minutes for app to reboot
2. Open your Streamlit Cloud app
3. Login with your credentials
4. Add some test data (partners, deals)
5. **Reboot the app** (Settings → Reboot)
6. Login again
7. ✅ **Your data should still be there!**

---

## 🔧 Local Development

### Option 1: Keep Using SQLite (Recommended)

For local development, the app automatically uses SQLite. No changes needed!

```bash
# Just run as normal
streamlit run app_universal.py
```

The app detects:
- **Streamlit Cloud** (with secrets) → Uses PostgreSQL
- **Local** → Uses SQLite (`attribution.db` file)

### Option 2: Use PostgreSQL Locally

If you want to test with PostgreSQL locally:

1. Install PostgreSQL on your machine
2. Create a `.env` file:

```bash
DATABASE_URL=postgresql://localhost/attribution_dev
```

3. Run migrations:

```bash
python3 -c "from db_universal import Database; db = Database(); db.init_db()"
```

4. Start app:

```bash
streamlit run app_universal.py
```

---

## 📊 Database Schema

The app automatically creates these tables:

1. **organizations** - Multi-tenant support
2. **users** - User accounts with roles
3. **sessions** - Login sessions
4. **attribution_target** - Opportunities/deals
5. **partner_touchpoint** - Partner activities
6. **attribution_rule** - Attribution models
7. **ledger_entry** - Attribution calculations
8. **measurement_workflow** - Attribution workflows
9. **attribution_period** - Period management
10. **partners** - Partner lookup table

All tables are created automatically on first run!

---

## 🔍 Troubleshooting

### "Could not connect to database"

**Fix**: Check your connection string in Streamlit secrets
- Make sure you replaced `[YOUR-PASSWORD]`
- Verify database is running (check Supabase dashboard)
- Try the connection string in a tool like TablePlus or pgAdmin

### "relation does not exist"

**Fix**: Database tables not created yet
1. Reboot the app (forces schema creation)
2. Check Supabase logs for errors

### "password authentication failed"

**Fix**: Wrong password in connection string
- Double-check password in Supabase dashboard
- Update secret with correct password
- Reboot app

### App still using SQLite locally

**Fix**: This is expected behavior!
- Local dev uses SQLite (easier)
- Production (Streamlit Cloud) uses PostgreSQL
- To force PostgreSQL locally, add `DATABASE_URL` to `.env`

---

## 📈 Monitoring Your Database

### Supabase Dashboard

1. Go to https://app.supabase.com/
2. Select your project
3. Click **"Table Editor"** to view data
4. Click **"SQL Editor"** to run queries
5. Click **"Database"** → **"Roles"** to manage access

### Useful SQL Queries

**Check table sizes:**
```sql
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

**Count records:**
```sql
SELECT
    'attribution_target' as table_name, COUNT(*) FROM attribution_target
UNION ALL
SELECT 'partner_touchpoint', COUNT(*) FROM partner_touchpoint
UNION ALL
SELECT 'ledger_entry', COUNT(*) FROM ledger_entry;
```

**View recent ledger entries:**
```sql
SELECT * FROM ledger_entry
ORDER BY calculation_timestamp DESC
LIMIT 10;
```

---

## 💾 Backups

### Automatic Backups (Supabase)

Supabase automatically backs up your database:
- **Daily backups** for 7 days (free tier)
- Access backups: Project → Settings → Database → Backups

### Manual Backup

Export your database:

```bash
# Using Supabase CLI
supabase db dump > backup.sql

# Or using pg_dump
pg_dump "postgresql://..." > backup.sql
```

Restore from backup:

```bash
psql "postgresql://..." < backup.sql
```

---

## 🔐 Security Best Practices

1. **Never commit connection strings** to Git
2. **Use strong passwords** (12+ characters)
3. **Rotate passwords regularly** (update secrets when you do)
4. **Use read-only connections** for analytics (create separate user)
5. **Enable SSL** (Supabase does this by default)

---

## 📊 Cost Estimates

### Free Tier Limits:

**Supabase (Most Generous)**
- Database: 500 MB
- Bandwidth: 2 GB/month
- API requests: Unlimited
- Cost: **FREE**

**Neon**
- Storage: 0.5 GB
- Compute: Suspends after 5 min inactive
- Cost: **FREE**

**Railway**
- $5 credit/month
- ~512 MB RAM
- Cost: **FREE** (with credit)

### When to Upgrade:

You'll need to upgrade when you hit:
- **500 MB database** (~50,000 deals)
- **2 GB bandwidth/month** (~10,000 active users/month)

Paid tiers start at $25/month (Supabase Pro)

---

## 🎯 Next Steps

After PostgreSQL is set up:

1. ✅ **Test thoroughly** - Add data, reboot, verify persistence
2. ✅ **Set up backups** - Export database weekly
3. ✅ **Monitor usage** - Check Supabase dashboard monthly
4. ✅ **Invite users** - Add team members via admin panel
5. ✅ **Import historical data** - Use CSV import feature

---

## 📞 Support

**Need help?**
- Supabase docs: https://supabase.com/docs
- PostgreSQL docs: https://postgresql.org/docs
- Streamlit secrets: https://docs.streamlit.io/streamlit-community-cloud/deploy-your-app/secrets-management

**Common Issues:**
- Connection errors → Check firewall, IP whitelisting
- Slow queries → Add indexes (we already have them!)
- Out of storage → Upgrade plan or archive old data

---

## ✨ You're Done!

Your attribution platform now has:
- ✅ Persistent data storage
- ✅ Production-ready database
- ✅ Automatic backups
- ✅ Scalable infrastructure

**Everything you add will be saved forever!** 🎉
