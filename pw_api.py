"""
Physics Wallah API - based on working reference repo (extraxted)
Domain: api.penpencil.xyz
OTP flow: send-otp → then POST /v1/oauth/token with OTP as password
"""

import aiohttp
import logging

logger = logging.getLogger(__name__)

PW_BASE   = "https://api.penpencil.xyz"
ORG_ID    = "5eb393ee95fab7468a79d189"
CLIENT_ID = "system-admin"
CLIENT_SECRET = "KjPXuAVfC5xbmgreETNMaL7z"

HEADERS = {
    "Host": "api.penpencil.xyz",
    "client-id": ORG_ID,
    "client-version": "12.84",
    "user-agent": "Android",
    "randomid": "e4307177362e86f1",
    "client-type": "MOBILE",
    "device-meta": "{APP_VERSION:12.84,DEVICE_MAKE:Asus,DEVICE_MODEL:ASUS_X00TD,OS_VERSION:6,PACKAGE_NAME:xyz.penpencil.physicswalb}",
    "content-type": "application/json; charset=UTF-8",
}

def auth_headers(token):
    return {**HEADERS, "authorization": f"Bearer {token}"}

def clean_phone(phone: str) -> str:
    phone = phone.strip().replace(" ", "").replace("-", "")
    if phone.startswith("+91"):
        phone = phone[3:]
    elif phone.startswith("91") and len(phone) == 12:
        phone = phone[2:]
    return phone


class PhysicsWallahAPI:
    def __init__(self, token: str = None):
        self.token = token

    # ── Step 1: Send OTP ──────────────────────────────────────────────────────
    async def send_otp(self, phone: str) -> dict:
        phone = clean_phone(phone)
        url = f"{PW_BASE}/v1/user/get-otp"
        payload = {
            "phone_number": phone,
            "country_code": "+91",
            "org_id": ORG_ID,
        }
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(url, json=payload, headers=HEADERS) as resp:
                    raw = await resp.text()
                    logger.info(f"send_otp [{resp.status}]: {raw[:300]}")
                    data = {}
                    try:
                        data = await resp.json(content_type=None)
                    except Exception:
                        pass

                    # Any 200 means OTP was sent
                    if resp.status == 200:
                        client_id = (data.get("data", {}) or {}).get("client_id", "")
                        return {"success": True, "clientId": client_id}

                    msg = (data.get("meta", {}) or {}).get("message") or data.get("message") or raw[:200]
                    return {"success": False, "message": msg}
        except Exception as e:
            logger.error(f"send_otp error: {e}")
            return {"success": False, "message": str(e)}

    # ── Step 2: Verify OTP via oauth/token ────────────────────────────────────
    async def verify_otp(self, phone: str, otp: str, client_id: str = "") -> dict:
        phone = clean_phone(phone)
        # This is the KEY fix - use /v1/oauth/token with OTP as password
        url = f"{PW_BASE}/v1/oauth/token"
        payload = {
            "username": phone,
            "otp": otp,
            "organizationId": ORG_ID,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "password",
            "password": otp,    # OTP is the password
        }
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(url, json=payload, headers=HEADERS) as resp:
                    raw = await resp.text()
                    logger.info(f"verify_otp [{resp.status}]: {raw[:300]}")
                    data = {}
                    try:
                        data = await resp.json(content_type=None)
                    except Exception:
                        pass

                    if resp.status == 200:
                        token_data = data.get("data", {}) or {}
                        token = (
                            token_data.get("access_token") or
                            token_data.get("token") or
                            token_data.get("accessToken") or ""
                        )
                        user = token_data.get("user") or {}
                        return {
                            "success": True,
                            "token": token,
                            "user": user,
                        }

                    msg = (data.get("meta", {}) or {}).get("message") or data.get("message") or data.get("error_description") or raw[:200]
                    return {"success": False, "message": msg}
        except Exception as e:
            logger.error(f"verify_otp error: {e}")
            return {"success": False, "message": str(e)}

    # ── Validate token ────────────────────────────────────────────────────────
    async def validate_token(self, token: str) -> dict:
        url = f"{PW_BASE}/v1/user/profile"
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(url, headers=auth_headers(token)) as resp:
                    raw = await resp.text()
                    logger.info(f"validate_token [{resp.status}]: {raw[:200]}")
                    data = {}
                    try:
                        data = await resp.json(content_type=None)
                    except Exception:
                        pass
                    if resp.status == 200:
                        return {"success": True, "user": data.get("data", {})}
                    return {"success": False, "message": data.get("message", "Invalid token")}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # ── Batches ───────────────────────────────────────────────────────────────
    async def get_batches(self) -> dict:
        url = f"{PW_BASE}/v3/batches/my-batches"
        params = {
            "mode": "1", "filter": "false", "exam": "", "amount": "",
            "organisationId": ORG_ID, "classes": "", "limit": "20",
            "page": "1", "programId": "", "ut": "1652675230446",
        }
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(url, params=params, headers=auth_headers(self.token)) as resp:
                    data = await resp.json(content_type=None)
                    raw = data.get("data", [])
                    if not isinstance(raw, list):
                        return {"success": False, "message": str(data.get("meta", {}).get("message", "No data"))}
                    batches = [{
                        "id": str(b.get("_id", "")),
                        "name": b.get("name", "Unnamed"),
                        "subject": b.get("subject", ""),
                        "language": b.get("language", ""),
                    } for b in raw]
                    return {"success": True, "batches": batches}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # ── Subjects ──────────────────────────────────────────────────────────────
    async def get_batch_subjects(self, batch_id: str) -> dict:
        url = f"{PW_BASE}/v3/batches/{batch_id}/details"
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(url, headers=auth_headers(self.token)) as resp:
                    data = await resp.json(content_type=None)
                    subjects_raw = data.get("data", {}).get("subjects", [])
                    subjects = [{
                        "id": str(s.get("_id", "")),
                        "name": s.get("name", "Unnamed"),
                    } for s in subjects_raw]
                    return {"success": True, "subjects": subjects}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # ── Contents ──────────────────────────────────────────────────────────────
    async def get_subject_contents(self, batch_id: str, subject_id: str) -> dict:
        all_videos, all_notes = [], []
        try:
            async with aiohttp.ClientSession() as s:
                for page in range(1, 6):
                    params = {"page": str(page), "tag": "", "contentType": "exercises-notes-videos", "ut": ""}
                    url = f"{PW_BASE}/v2/batches/{batch_id}/subject/{subject_id}/contents"
                    async with s.get(url, params=params, headers=auth_headers(self.token)) as resp:
                        data = await resp.json(content_type=None)
                        items = data.get("data", [])
                        if not items:
                            break
                        for item in items:
                            raw_url = item.get("url", "")
                            # Convert MPD → M3U8 exactly like reference does
                            stream_url = raw_url.replace("d1d34p8vz63oiq", "d3nzo6itypaz07").replace("mpd", "m3u8").strip()
                            name = item.get("topic") or item.get("name") or "Unnamed"
                            item_id = str(item.get("_id", ""))
                            if raw_url.endswith((".mpd", ".m3u8")) or "video" in item.get("contentType", "").lower():
                                all_videos.append({"id": item_id, "name": name, "url": stream_url, "raw_url": raw_url, "drm": item.get("isDrmProtected", False)})
                            elif raw_url.endswith(".pdf") or "note" in item.get("contentType", "").lower():
                                all_notes.append({"id": item_id, "name": name, "url": raw_url})
                        if len(items) < 10:
                            break
            return {"success": True, "videos": all_videos, "notes": all_notes}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # ── Full export ───────────────────────────────────────────────────────────
    async def get_all_content(self, batches: list) -> dict:
        result = []
        for batch in batches:
            batch_id = batch["id"]
            batch_entry = {**batch, "subjects": []}
            subj_result = await self.get_batch_subjects(batch_id)
            if subj_result.get("success"):
                for subj in subj_result.get("subjects", []):
                    contents = await self.get_subject_contents(batch_id, subj["id"])
                    batch_entry["subjects"].append({**subj, "videos": contents.get("videos", []), "notes": contents.get("notes", [])})
            result.append(batch_entry)
        return {"batches": result, "total": len(result)}
