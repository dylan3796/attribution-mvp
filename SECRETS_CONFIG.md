# Streamlit Cloud Secrets Configuration

This guide shows how to configure admin credentials for your Streamlit Cloud deployment.

## Why This Is Needed

Streamlit Cloud uses **ephemeral storage**, which means the SQLite database resets on every app reboot. By storing admin credentials in Streamlit secrets, the admin user is automatically recreated on each startup.

---

## Setup Instructions

### 1. Go to Your App Settings

1. Visit https://share.streamlit.io/
2. Click on your **attribution-mvp** app
3. Click **"⚙️ Settings"** (or the three dots menu → "Settings")
4. Click **"Secrets"** in the left sidebar

### 2. Add Your Secrets

Copy and paste this into the secrets editor:

```toml
# Admin user credentials
[admin]
email = "your-email@company.com"          # Your email address
password = "your-secure-password-here"    # Use a strong password!
name = "Your Name"                        # Your full name

# Optional: Organization name
[organization]
name = "Your Company Name"
```

### 3. Update the Values

**Important:** Change these values to your actual information!

- `email`: Your real email address
- `password`: A **strong, unique password** (not "admin123"!)
- `name`: Your name or "Admin User"
- `organization.name`: Your company name (optional)

Example:
```toml
[admin]
email = "john@acmecorp.com"
password = "MyS3cur3P@ssw0rd!"
name = "John Smith"

[organization]
name = "Acme Corporation"
```

### 4. Save and Reboot

1. Click **"Save"**
2. Go back to your app
3. Click **"⋮"** → **"Reboot app"**

### 5. Login

After the app reboots, login with your credentials:
- Email: `your-email@company.com` (the one you set)
- Password: `your-secure-password-here` (the one you set)

---

## Local Development

The app will work locally **without** secrets. It will use default credentials:
- Email: `admin@attribution.local`
- Password: `admin123`

---

## Security Notes

⚠️ **Important Security Tips:**

1. **Use a strong password** - At least 12 characters with mixed case, numbers, and symbols
2. **Don't share secrets** - Keep your Streamlit secrets private
3. **Change password regularly** - Update the secret and reboot the app
4. **Use unique passwords** - Don't reuse passwords from other services

---

## Creating Additional Users

Once logged in as admin, you can create additional users:

1. Login with your admin credentials
2. Go to the **User Management** section (coming soon)
3. Click **"Add User"**
4. Fill in their details and assign a role

**Note:** Additional users created in the UI will be **lost on reboot** since the database is ephemeral. For persistent users, you need to:
- Add them to secrets (see below), OR
- Migrate to PostgreSQL (recommended for production)

### Adding Multiple Users to Secrets (Advanced)

```toml
[admin]
email = "admin@company.com"
password = "AdminPassword123!"
name = "Admin User"

[[users]]
email = "manager@company.com"
password = "ManagerPass123!"
name = "Sales Manager"
role = "manager"

[[users]]
email = "analyst@company.com"
password = "AnalystPass123!"
name = "Data Analyst"
role = "analyst"
```

*Note: Multi-user secrets support requires additional code changes.*

---

## Troubleshooting

### "Invalid email or password" after adding secrets

1. Make sure you **saved** the secrets
2. **Reboot** the app (secrets only load on startup)
3. Check for **typos** in your email/password
4. Verify the secrets format matches the example above

### Secrets not working

1. Make sure you're in the **Secrets** tab (not "Environment variables")
2. Check that the TOML format is valid (no syntax errors)
3. Try rebooting the app again

### Password not working

Passwords are **case-sensitive**. Make sure:
- No extra spaces before/after the password
- Caps Lock is off
- You're using the exact password from secrets

---

## Next Steps: Migrate to PostgreSQL

For a **production-ready** deployment with persistent data, migrate to PostgreSQL:

1. Create a free PostgreSQL database:
   - **Supabase** (recommended): https://supabase.com/
   - **Railway**: https://railway.app/
   - **Neon**: https://neon.tech/

2. Add database URL to secrets:
   ```toml
   [database]
   url = "postgresql://user:pass@host:5432/dbname"
   ```

3. I can help modify the code to use PostgreSQL instead of SQLite.

---

## Questions?

If you need help:
1. Check the Streamlit docs: https://docs.streamlit.io/streamlit-community-cloud/get-started/deploy-an-app/connect-to-data-sources/secrets-management
2. Ask me to help troubleshoot!
