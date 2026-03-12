"""
Video streaming proxy server.
Runs alongside the bot on Railway.
Proxies DRM-free video streams from PW's CDN using the user's auth token.
"""

import os
import logging
import aiohttp
from flask import Flask, request, Response, jsonify, redirect
import threading

logger = logging.getLogger(__name__)

app = Flask(__name__)

PW_BASE = "https://api.penpencil.co"
HEADERS_BASE = {
    "Client-Type": "2",
    "Client-Version": "3.8.0",
    "randomid": "abcdef123456",
    "User-Agent": "okhttp/4.9.0",
}


@app.route("/")
def index():
    return jsonify({"status": "ok", "service": "PW Video Proxy"})


@app.route("/stream/<video_id>")
def stream_video(video_id: str):
    """
    Fetch the real video URL for the video_id and redirect the client.
    The client (browser / VLC) will then stream directly from PW's CDN.
    """
    token = request.args.get("token", "")
    if not token:
        return jsonify({"error": "token required"}), 401

    import requests as req  # sync for Flask

    headers = {**HEADERS_BASE, "Authorization": f"Bearer {token}"}
    url = f"{PW_BASE}/v2/videos/{video_id}"

    try:
        resp = req.get(url, headers=headers, timeout=10)
        data = resp.json()
        if data.get("meta", {}).get("status") == "SUCCESS":
            vd = data.get("data", {}).get("videoDetails", {})
            video_url = vd.get("videoMpd") or vd.get("videoUrl", "")
            drm = vd.get("isDrm", False)

            if drm:
                return jsonify({
                    "error": "DRM protected video",
                    "message": "This video uses DRM encryption. Stream URL returned for compatible players.",
                    "mpd_url": video_url,
                    "drm_license": vd.get("drmLicenseUrl", ""),
                    "note": "Use a DRM-capable player like ExoPlayer or browser with Widevine"
                }), 200

            if video_url:
                # Redirect directly to the CDN stream
                return redirect(video_url, code=302)
            return jsonify({"error": "No video URL found"}), 404
        return jsonify({"error": data.get("meta", {}).get("message", "Failed")}), 400
    except Exception as e:
        logger.error(f"stream error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/info/<video_id>")
def video_info(video_id: str):
    """Return full video metadata as JSON."""
    token = request.args.get("token", "")
    if not token:
        return jsonify({"error": "token required"}), 401

    import requests as req

    headers = {**HEADERS_BASE, "Authorization": f"Bearer {token}"}
    url = f"{PW_BASE}/v2/videos/{video_id}"

    try:
        resp = req.get(url, headers=headers, timeout=10)
        data = resp.json()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/health")
def health():
    return jsonify({"status": "healthy"})


def run_server():
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting stream server on port {port}")
    app.run(host="0.0.0.0", port=port)


def start_in_thread():
    """Start Flask server in a background thread (used alongside the bot)."""
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    return t
