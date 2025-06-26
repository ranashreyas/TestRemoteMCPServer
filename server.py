import uuid
from fastmcp import FastMCP
# from mcp.server.fastmcp import FastMCP

import datetime
import pytz
import os
import hashlib

mcp = FastMCP(
    name="Current-Date-and-Time",
    instructions="When you are asked for the current date or time, call current_datetime() and pass along an optional timezone parameter (defaults to NYC)."
)

@mcp.tool()
def generate_session_uuid() -> str:
    """
    Generate a session uuid.
    returns: a uuid.
    """
    return str(uuid.uuid4())

@mcp.tool()
def google_oauth(session_uuid: str) -> str:
    """
    Perform Google OAuth to get access to the user's Gmail.
    It is very important that you remember the session uuid. if you don't remember it exactly, call the tool "generate_session_uuid" as that is the uuid that
    stores the users credentials, and the user will have to redo the oauth process.
    returns: a link to which you will show to the user, who will then click it and authorize their Google account.
    """
    return f"https://testremotemcpserver.onrender.com/google/auth?user_id=default_user&client_code={session_uuid}"

@mcp.tool()
def test_pull_creds(session_uuid: str) -> str:
    """
    pull the credentials from the user's Google account.
    returns: the credentials.
    """
    import requests
    
    try:
        # Get the secret from environment variables
        env_secret = os.environ.get('ENV_SECRET')
        if not env_secret:
            return "Error: ENV_SECRET not configured"
        
        # Generate hash of the secret
        secret_hash = hashlib.sha256(env_secret.encode()).hexdigest()
        
        # Make request with hash parameter
        response = requests.get(
            "https://testremotemcpserver.onrender.com/creds",
            params={"hash": secret_hash, "filename": session_uuid}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return f"Error fetching credentials: {response.status_code} - {response.text}. You may have to do google oauth again."
    except Exception as e:
        return f"Error making request: {str(e)}"


@mcp.tool()
def current_datetime(timezone: str = "America/New_York") -> str:
    """
    Returns the current date and time as a string. 
    If you are asked for the current date or time, call this function.
    Args:
        timezone: Timezone name (e.g., 'UTC', 'US/Pacific', 'Europe/London').
                 Defaults to 'America/New_York'.
    
    Returns:
        A formatted date and time string.
    """
    
    try:
        tz = pytz.timezone(timezone)
        now = datetime.datetime.now(tz)
        return now.strftime("%Y-%m-%d %H:%M:%S %Z")
    except pytz.exceptions.UnknownTimeZoneError:
        return f"Error: Unknown timezone '{timezone}'. Please use a valid timezone name."




if __name__ == "__main__":
    # mcp.run()
    import asyncio
    port = int(os.environ.get("PORT", 8001))
    asyncio.run(
        mcp.run_sse_async(
            host="0.0.0.0",  # Changed from 127.0.0.1 to allow external connections
            port=port,
            log_level="debug"
        )
    )


# {
#   "mcpServers": {
#     "Current Date and Time": {
#       "command": "/Users/shreyas/anaconda3/envs/mcp-server/bin/mcp",
#       "args": [
#         "run",
#         "/Users/shreyas/tempDesktop/Programming/TestRemoteMCPServer/server.py"
#       ]
#     }
#   }
# }