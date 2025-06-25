import sys
from fastmcp import FastMCP
from flask import Flask, request, redirect, session, jsonify
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import os, json, pickle
from pathlib import Path
import threading
import asyncio
from werkzeug.middleware.proxy_fix import ProxyFix


# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-this-in-production')
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Initialize FastMCP
mcp = FastMCP("Demo")

CLIENT_SECRETS = "credentials.json"
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
REDIRECT_URI = os.environ.get('REDIRECT_URI', 'https://testremotemcpserver.onrender.com/google/oauth2callback')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
    
TOKEN_DIR = Path(SCRIPT_DIR) / 'Pickles'
TOKEN_DIR.mkdir(exist_ok=True)

def _save_creds(user_id: str, creds: Credentials):
    with open(TOKEN_DIR / f"{user_id}.pickle", "wb") as f:
        pickle.dump(creds, f)

def _load_creds(user_id: str) -> Credentials | None:
    path = TOKEN_DIR / f"{user_id}.pickle"
    if path.exists():
        with open(path, "rb") as f:
            return pickle.load(f)
    return None

@app.route("/google/auth")
def start_google_auth():
    user_id = request.args.get('user_id', 'default_user')
    print("user_id", user_id)
    
    try:
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI,
        )
        auth_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )

        print(state)
        print(auth_url)
        
        # Store flow data in session
        session['oauth_state'] = state
        session['user_id'] = user_id
        session['flow_data'] = {
            'client_config': flow.client_config,
            'scopes': SCOPES,
            'redirect_uri': REDIRECT_URI
        }
        
        return redirect(auth_url)
    except Exception as e:
        return f"Error starting OAuth flow: {str(e)}", 500

@app.route("/google/oauth2callback")
def google_callback():
    try:
        # Verify state
        if 'oauth_state' not in session:
            return "Invalid session state", 400
        
        user_id = session.get('user_id', 'default_user')
        flow_data = session.get('flow_data')
        
        if not flow_data:
            return "Missing flow data", 400
        
        # Recreate flow
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS,
            scopes=SCOPES,
            state=session["oauth_state"],
        )
        flow.redirect_uri = REDIRECT_URI
        
        # Fetch token
        authorization_response = request.url
        flow.fetch_token(authorization_response=authorization_response)
        
        # Save credentials
        creds = flow.credentials
        _save_creds(user_id, creds)
        
        # Clear session
        session.pop('oauth_state', None)
        session.pop('user_id', None)
        session.pop('flow_data', None)
        
        return '''
        <html>
        <head><title>OAuth Success</title></head>
        <body>
            <h2>✅ Gmail connected successfully!</h2>
            <p>You can close this tab and return to your application.</p>
        </body>
        </html>
        '''
    except Exception as e:
        return f"Error in OAuth callback: {str(e)}", 500

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy"})

@app.route('/')
def index():
    """Root endpoint with basic info"""
    return jsonify({
        "name": "MCP Server with Google OAuth",
        "endpoints": {
            "mcp_sse": "/sse",
            "google_auth": "/google/auth?user_id=<user_id>",
            "health": "/health"
        }
    })

if __name__ == "__main__":    
    # Run Flask app
    app.run(host="0.0.0.0", port=8000, debug=False)
