"""
Physics Wallah API wrapper
Handles auth (OTP), fetching batches, subjects, topics, and video URLs.
"""

import aiohttp
import logging

logger = logging.getLogger(__name__)

PW_BASE = "https://api.penpencil.co"
HEADERS_BASE = {
    "Client-Type": "2",          # Android client
    "Client-Version": "3.8.0",
    "randomid": "abcdef123456",
    "Accept": "application/json",
    "Content-Type": "application/json",
    "User-Agent": "okhttp/4.9.0",
}

class PhysicsWallahAPI:
    def __init__(self, token: str = None):
        self.token = token
        self.session_headers = {
            **HEADERS_BASE,
            **({"Authorization": f"Bearer {token}"} if token else {})
        }

    # ── Auth ─────────────────────────────────────────────────────────────────

    async def send_otp(self, phone: str) -> dict:
        url = f"{PW_BASE}/v1/user/get-otp"
        payload = {
            "phone_number": phone,
            "country_code": "+91",
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=HEADERS_BASE) as resp:
                    data = await resp.json()
                    logger.info(f"send_otp response: {data}")
                    if data.get("meta", {}).get("status") == "SUCCESS" or data.get("success"):
                        return {
                            "success": True,
                            "clientId": data.get("data", {}).get("client_id", ""),
                        }
                    return {"success": False, "message": data.get("meta", {}).get("message", "Failed")}
        except Exception as e:
            logger.error(f"send_otp error: {e}")
            return {"success": False, "message": str(e)}

    async def verify_otp(self, phone: str, otp: str, client_id: str = "") -> dict:
        url = f"{PW_BASE}/v1/user/verify-otp"
        payload = {
            "phone_number": phone,
            "otp": otp,
            "country_code": "+91",
            "client_id": client_id,
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=HEADERS_BASE) as resp:
                    data = await resp.json()
                    logger.info(f"verify_otp response keys: {list(data.keys())}")
                    if data.get("meta", {}).get("status") == "SUCCESS" or data.get("success"):
                        token_data = data.get("data", {})
                        return {
                            "success": True,
                            "token": token_data.get("token", token_data.get("access_token", "")),
                            "refreshToken": token_data.get("refresh_token", ""),
                            "user": token_data.get("user", {}),
                        }
                    return {"success": False, "message": data.get("meta", {}).get("message", "Invalid OTP")}
        except Exception as e:
            logger.error(f"verify_otp error: {e}")
            return {"success": False, "message": str(e)}

    # ── Batches ───────────────────────────────────────────────────────────────

    async def get_batches(self) -> dict:
        url = f"{PW_BASE}/v2/batches/my-batches"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.session_headers, params={"page": 1}) as resp:
                    data = await resp.json()
                    if data.get("meta", {}).get("status") == "SUCCESS":
                        raw = data.get("data", [])
                        batches = [
                            {
                                "id": str(b.get("_id", b.get("id", ""))),
                                "name": b.get("name", "Unnamed Batch"),
                                "slug": b.get("slug", ""),
                                "subject": b.get("subject", ""),
                                "language": b.get("language", ""),
                                "price": b.get("discountedPrice", 0),
                                "thumbnail": b.get("previewImage", ""),
                            }
                            for b in raw
                        ]
                        return {"success": True, "batches": batches}
                    return {"success": False, "message": data.get("meta", {}).get("message", "Failed")}
        except Exception as e:
            logger.error(f"get_batches error: {e}")
            return {"success": False, "message": str(e)}

    # ── Subjects ──────────────────────────────────────────────────────────────

    async def get_batch_subjects(self, batch_id: str) -> dict:
        url = f"{PW_BASE}/v2/batches/{batch_id}/details"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.session_headers) as resp:
                    data = await resp.json()
                    if data.get("meta", {}).get("status") == "SUCCESS":
                        raw = data.get("data", {}).get("subjects", [])
                        subjects = [
                            {
                                "id": str(s.get("_id", s.get("id", ""))),
                                "name": s.get("name", "Unnamed Subject"),
                                "slug": s.get("slug", ""),
                            }
                            for s in raw
                        ]
                        return {"success": True, "subjects": subjects}
                    return {"success": False, "message": data.get("meta", {}).get("message", "Failed")}
        except Exception as e:
            logger.error(f"get_batch_subjects error: {e}")
            return {"success": False, "message": str(e)}

    # ── Topics ────────────────────────────────────────────────────────────────

    async def get_subject_topics(self, batch_id: str, subject_id: str) -> dict:
        url = f"{PW_BASE}/v2/batches/{batch_id}/subject/{subject_id}/topics"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.session_headers, params={"page": 1}) as resp:
                    data = await resp.json()
                    if data.get("meta", {}).get("status") == "SUCCESS":
                        raw = data.get("data", [])
                        topics = [
                            {
                                "id": str(t.get("_id", t.get("id", ""))),
                                "name": t.get("name", "Unnamed Topic"),
                            }
                            for t in raw
                        ]
                        return {"success": True, "topics": topics}
                    return {"success": False, "message": data.get("meta", {}).get("message", "Failed")}
        except Exception as e:
            logger.error(f"get_subject_topics error: {e}")
            return {"success": False, "message": str(e)}

    # ── Videos ────────────────────────────────────────────────────────────────

    async def get_topic_videos(self, batch_id: str, subject_id: str, topic_id: str) -> dict:
        url = f"{PW_BASE}/v2/batches/{batch_id}/subject/{subject_id}/topic/{topic_id}/videos"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.session_headers, params={"page": 1}) as resp:
                    data = await resp.json()
                    if data.get("meta", {}).get("status") == "SUCCESS":
                        raw = data.get("data", [])
                        videos = []
                        for v in raw:
                            video_data = v.get("videoDetails", v)
                            videos.append({
                                "id": str(v.get("_id", v.get("id", ""))),
                                "name": v.get("topic", v.get("name", "Unnamed Video")),
                                "duration": video_data.get("duration", 0),
                                "url": video_data.get("videoMpd", video_data.get("videoUrl", "")),
                                "drm": video_data.get("isDrm", False),
                            })
                        return {"success": True, "videos": videos}
                    return {"success": False, "message": data.get("meta", {}).get("message", "Failed")}
        except Exception as e:
            logger.error(f"get_topic_videos error: {e}")
            return {"success": False, "message": str(e)}

    async def get_video_url(self, video_id: str) -> dict:
        """Get the actual streaming URL for a video."""
        url = f"{PW_BASE}/v2/videos/{video_id}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.session_headers) as resp:
                    data = await resp.json()
                    if data.get("meta", {}).get("status") == "SUCCESS":
                        vd = data.get("data", {}).get("videoDetails", {})
                        return {
                            "success": True,
                            "mpd_url": vd.get("videoMpd", ""),
                            "m3u8_url": vd.get("videoUrl", ""),
                            "drm": vd.get("isDrm", False),
                            "drm_license": vd.get("drmLicenseUrl", ""),
                        }
                    return {"success": False, "message": "Failed to get video URL"}
        except Exception as e:
            logger.error(f"get_video_url error: {e}")
            return {"success": False, "message": str(e)}

    # ── Full Export ───────────────────────────────────────────────────────────

    async def get_all_content(self, batches: list) -> dict:
        """Build full JSON tree: batches → subjects → topics → videos"""
        result = []
        for batch in batches:
            batch_id = batch["id"]
            batch_entry = {**batch, "subjects": []}

            subj_result = await self.get_batch_subjects(batch_id)
            if not subj_result.get("success"):
                result.append(batch_entry)
                continue

            for subj in subj_result.get("subjects", []):
                subj_id = subj["id"]
                subj_entry = {**subj, "topics": []}

                topic_result = await self.get_subject_topics(batch_id, subj_id)
                if not topic_result.get("success"):
                    batch_entry["subjects"].append(subj_entry)
                    continue

                for topic in topic_result.get("topics", []):
                    topic_id = topic["id"]
                    topic_entry = {**topic, "videos": []}

                    vid_result = await self.get_topic_videos(batch_id, subj_id, topic_id)
                    if vid_result.get("success"):
                        topic_entry["videos"] = vid_result.get("videos", [])

                    subj_entry["topics"].append(topic_entry)

                batch_entry["subjects"].append(subj_entry)

            result.append(batch_entry)

        return {"batches": result, "total": len(result)}
