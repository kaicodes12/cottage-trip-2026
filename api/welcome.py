import json
import os
import urllib.request


def handler(request, response):
    """Vercel serverless function — send welcome email via Resend."""
    if request.method == "OPTIONS":
        response.status_code = 200
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return response

    if request.method != "POST":
        response.status_code = 405
        response.headers["Content-Type"] = "application/json"
        response.body = json.dumps({"error": "Method not allowed"})
        return response

    api_key = os.environ.get("RESEND_API_KEY", "")
    if not api_key:
        response.status_code = 500
        response.headers["Content-Type"] = "application/json"
        response.body = json.dumps({"error": "RESEND_API_KEY not configured"})
        return response

    try:
        body = json.loads(request.body)
    except Exception:
        response.status_code = 400
        response.headers["Content-Type"] = "application/json"
        response.body = json.dumps({"error": "Invalid JSON"})
        return response

    name = body.get("name", "").strip()
    email = body.get("email", "").strip()

    if not name or not email:
        response.status_code = 400
        response.headers["Content-Type"] = "application/json"
        response.body = json.dumps({"error": "Name and email required"})
        return response

    email_data = json.dumps({
        "from": "Cottage Trip 2026 <onboarding@resend.dev>",
        "to": [email],
        "subject": f"Welcome to Cottage '26, {name}! 🏕️",
        "html": f"""
        <div style="font-family:sans-serif;max-width:500px;margin:0 auto;padding:2rem;">
          <div style="background:#2c4a34;border-radius:16px;padding:2rem;text-align:center;margin-bottom:1.5rem;">
            <h1 style="color:#e2b05a;font-size:1.8rem;margin:0;">Cottage '26 🏕️</h1>
            <p style="color:rgba(250,245,236,0.6);font-size:0.85rem;margin-top:0.5rem;">The Squad Cottage Trip — June 2026</p>
          </div>
          <h2 style="color:#2c4a34;margin-bottom:0.5rem;">Hey {name}! 👋</h2>
          <p style="color:#3a3028;line-height:1.6;">
            You're officially on the squad for the 2026 cottage trip! Here's what you can do:
          </p>
          <ul style="color:#3a3028;line-height:1.8;">
            <li>🗳️ <strong>Vote</strong> on your favourite listings</li>
            <li>📅 <strong>Mark your blackout dates</strong> so we find the best weekend</li>
            <li>📸 <strong>Upload memes</strong> to the Meme Wall</li>
            <li>📖 <strong>Post moments</strong> in the Trip Journal</li>
            <li>🌤️ <strong>Check the weather</strong> projections</li>
          </ul>
          <p style="color:#7a6a58;font-size:0.85rem;margin-top:1.5rem;">
            See you at the cottage! 🏠
          </p>
        </div>
        """,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=email_data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            response.status_code = 200
            response.headers["Content-Type"] = "application/json"
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.body = json.dumps({"success": True})
    except urllib.error.HTTPError as e:
        response.status_code = 500
        response.headers["Content-Type"] = "application/json"
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.body = json.dumps({"error": e.read().decode()})

    return response
