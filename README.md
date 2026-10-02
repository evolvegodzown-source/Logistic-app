# Logistic-app
shows logistics details

## Dashboard login

The dashboard reads credentials from `DASHBOARD_USERNAME` and `DASHBOARD_PASSWORD`
environment variables, or from Streamlit secrets:

```toml
[auth]
username = "your-admin-username"
password = "your-strong-password"
```

For local development, save this as `.streamlit/secrets.toml`. For a hosted app,
configure the same `[auth]` values in the hosting provider's secrets settings.
Do not commit `secrets.toml` or put credentials in source code.
