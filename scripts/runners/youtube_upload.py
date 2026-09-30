"""YouTube uploader cho runner tin/truyện (chỉ video; audio đi qua GitHub Pages).

One-time auth:  python youtube_upload.py --auth   (mở trình duyệt, đăng nhập 1 lần,
refresh token lưu ở youtube_token.json — KHÔNG nằm trong git repo nào)
Upload:         python youtube_upload.py --file x.mp4 --title "..." [--desc "..."]
                [--tags "ai,news"] [--privacy unlisted] [--shorts]
In ra DUY NHẤT dòng cuối: VIDEO_ID=<id> STATUS=<privacyStatus thực tế>

Lưu ý: project API chưa qua audit của YouTube sẽ bị ép privacyStatus=private
(locked) bất kể request — wrapper vẫn lấy được VIDEO_ID, user flip Unlisted tay
cho tới khi audit xong.
"""
import argparse
import json
import os
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
# CHỈ env — không còn đường lùi "cạnh file này".
#
# Đường lùi cũ đặt token vào chính thư mục engine. Nó sống được vì engine nằm dưới
# một thư mục riêng của máy cũ; engine nay là mã DÙNG CHUNG đi theo gói sang máy
# khác, nên một secret nằm trong đó là secret bị mang đi cùng. Và khi file vắng, đường
# lùi làm lỗi nổ ở tận bước gọi Google ("invalid_grant") thay vì nói thiếu biến nào.
CLIENT_SECRET = os.environ.get("YT_CLIENT_SECRET")
TOKEN_PATH = os.environ.get("YT_TOKEN_PATH")


def _doi_env():
    """Dừng khi thiếu biến — nhưng dừng lúc DÙNG, không lúc import.

    Module này bị `import` bởi pipeline truyện chỉ để gọi vài hàm; nổ ngay ở dòng import
    sẽ giết cả những luồng không hề upload gì. Kiểm ở đây thì thông điệp vẫn nói đúng
    thiếu biến nào, mà không biến một `import` thành bãi mìn.
    """
    thieu = [t for t, v in (("YT_CLIENT_SECRET", CLIENT_SECRET),
                            ("YT_TOKEN_PATH", TOKEN_PATH)) if not v]
    if thieu:
        raise SystemExit(
            "youtube_upload: thiếu " + " / ".join(thieu) + ". Đặt biến này trỏ tới file "
            "trong kho secret của máy; không còn đường lùi cạnh script.")


# full scope: upload + quản lý playlist + đổi privacy (đổi scope -> phải --auth lại)
SCOPES = ["https://www.googleapis.com/auth/youtube"]
# Không mặc định playlist nào: tên playlist là của kênh (campaign.md), runner luôn truyền.
DEFAULT_PLAYLIST = ""


def _creds(interactive=False):
    _doi_env()
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    creds = None
    if os.path.isfile(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_PATH, "w", encoding="utf-8", newline="\n") as f:
            f.write(creds.to_json())
    if not creds or not creds.valid:
        if not interactive:
            raise SystemExit("no valid token — run:  youtube_upload.py --auth")
        from google_auth_oauthlib.flow import InstalledAppFlow
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET, SCOPES)
        creds = flow.run_local_server(port=0, prompt="consent",
                                      authorization_prompt_message="")
        with open(TOKEN_PATH, "w", encoding="utf-8", newline="\n") as f:
            f.write(creds.to_json())
        print("auth OK — token saved")
    return creds


def _yt():
    from googleapiclient.discovery import build
    return build("youtube", "v3", credentials=_creds())


def _find_or_create_playlist(yt, name):
    page = None
    while True:
        r = yt.playlists().list(part="snippet", mine=True, maxResults=50,
                                pageToken=page).execute()
        for p in r.get("items", []):
            if p["snippet"]["title"].strip().lower() == name.strip().lower():
                return p["id"]
        page = r.get("nextPageToken")
        if not page:
            break
    r = yt.playlists().insert(part="snippet,status", body={
        "snippet": {"title": name,
                    "description": os.environ.get("YT_PLAYLIST_DESC", "")},
        "status": {"privacyStatus": "public"}}).execute()
    return r["id"]


def add_to_playlist(yt, video_id, playlist_name):
    pid = _find_or_create_playlist(yt, playlist_name)
    yt.playlistItems().insert(part="snippet", body={
        "snippet": {"playlistId": pid,
                    "resourceId": {"kind": "youtube#video", "videoId": video_id}}}).execute()
    print(f"PLAYLIST_OK={pid}")


def set_privacy(yt, video_id, privacy):
    # videos.update REPLACES the whole status object — omitting embeddable here
    # resets it to False and embeds show "Video unavailable". Always include it.
    yt.videos().update(part="status", body={
        "id": video_id,
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False,
                   "embeddable": True}}).execute()
    print(f"PRIVACY_OK={video_id}:{privacy}")


def add_to_playlist_retry(yt, vid, playlist, attempts=4, sleep=time.sleep):
    """Thêm video vào playlist, CÓ retry. Trả True nếu vào được, False nếu chịu thua.

    14/08/2026 (UAT Phàm Nhân Tu Tiên phần 2): `playlistItems.insert` dính 409 SERVICE_UNAVAILABLE
    thoáng qua của YouTube -> video ĐÃ đăng nhưng rơi NGOÀI playlist. Trước đây bước này chỉ `warn`
    một lần rồi đi tiếp, nên khi chạy tự động ban đêm nó hỏng ÂM THẦM: Telegram vẫn báo ✅ kèm link,
    không ai biết video lạc playlist cho tới khi tình cờ mở kênh ra xem.

    Playlist vẫn là việc PHỤ — thất bại KHÔNG được làm hỏng upload. Nhưng phải kêu TO bằng marker
    `PLAYLIST_FAIL=` để wrapper thông báo và con người còn thấy mà vá tay.
    """
    for attempt in range(attempts):
        try:
            add_to_playlist(yt, vid, playlist)
            print(f"PLAYLIST_OK={playlist}", flush=True)
            return True
        except Exception as exc:
            last = attempt == attempts - 1
            wait = 5 * (2 ** attempt)
            print(f"  [warn] playlist add lần {attempt + 1}/{attempts} hỏng ({exc})"
                  + ("" if last else f" — chờ {wait}s rồi thử lại"), flush=True)
            if not last:
                sleep(wait)
    print(f"PLAYLIST_FAIL={vid} playlist={playlist!r} — video ĐÃ đăng nhưng CHƯA vào playlist. "
          f"Vá tay: python youtube_upload.py --playlist-add {vid} --playlist \"{playlist}\"",
          flush=True)
    return False


def upload(path, title, desc="", tags=None, privacy="unlisted", playlist="", category="28",
           thumbnail="", publish_at=""):
    from googleapiclient.http import MediaFileUpload
    yt = _yt()
    status = {"privacyStatus": privacy, "selfDeclaredMadeForKids": False}
    if publish_at:
        # Scheduled publish: YouTube YÊU CẦU privacyStatus=private + publishAt (RFC3339 UTC).
        # Tới giờ publishAt, video tự chuyển PUBLIC.
        status["privacyStatus"] = "private"
        status["publishAt"] = publish_at
    body = {
        "snippet": {"title": title[:95], "description": desc[:4900],
                    "tags": (tags or [])[:30], "categoryId": category},
        "status": status,
    }
    media = MediaFileUpload(path, chunksize=8 * 1024 * 1024, resumable=True)
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    # Resumable upload + RETRY lỗi mạng thoáng qua (ssl.SSLEOFError, reset, 5xx...). next_chunk()
    # tiếp tục TỪ CHỖ DỞ trên CÙNG req → KHÔNG tạo video trùng. (Đứt SSL ở 72% từng tạo ghost +
    # buộc retry-from-0 = video nhân đôi — xem memory.)
    import http.client
    import random
    import ssl
    import time as _time
    import httplib2
    from googleapiclient.errors import HttpError
    RETRIABLE = (httplib2.HttpLib2Error, IOError, ssl.SSLError, http.client.NotConnected,
                 http.client.IncompleteRead, http.client.ImproperConnectionState,
                 http.client.CannotSendRequest, http.client.CannotSendHeader,
                 http.client.ResponseNotReady, http.client.BadStatusLine)
    resp = None
    errs = 0
    while resp is None:
        retry = False
        try:
            status, resp = req.next_chunk()
            if status:
                print(f"  upload {int(status.progress() * 100)}%", flush=True)
        except HttpError as e:
            if getattr(e, "resp", None) is not None and e.resp.status in (500, 502, 503, 504):
                retry = True
            else:
                raise
        except RETRIABLE as e:
            retry = True
            print(f"  [retry] lỗi mạng thoáng qua: {e}", flush=True)
        if retry:
            errs += 1
            if errs > 10:
                raise RuntimeError(f"upload thất bại sau {errs} lần retry")
            _time.sleep(min(60, 2 ** errs) + random.random())
        else:
            errs = 0
    vid = resp["id"]
    actual = (resp.get("status") or {}).get("privacyStatus", "?")
    if thumbnail and os.path.isfile(thumbnail):  # ảnh đại diện = frame slide mở đầu
        try:
            yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(thumbnail)).execute()
            print(f"THUMB_OK={vid}")
        except Exception as exc:
            print(f"  [warn] thumbnail set failed: {exc}")
    if playlist:
        add_to_playlist_retry(yt, vid, playlist)
    print(f"VIDEO_ID={vid} STATUS={actual}")
    return vid


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--auth", action="store_true", help="interactive one-time login")
    ap.add_argument("--file")
    ap.add_argument("--title")
    ap.add_argument("--desc", default="")
    ap.add_argument("--desc-file", default="", help="read description from this UTF-8 file")
    ap.add_argument("--tags", default="AI,tin tức AI",
                    help="thẻ, phân cách bằng dấu phẩy (runner truyền theo campaign.md)")
    ap.add_argument("--privacy", default="public")
    ap.add_argument("--playlist", default=DEFAULT_PLAYLIST,
                    help="playlist name to add the video to ('' to skip)")
    ap.add_argument("--shorts", action="store_true",
                    help="append #Shorts to title/description")
    ap.add_argument("--thumbnail", default="", help="ảnh đại diện (frame slide mở đầu)")
    ap.add_argument("--set-thumb", default="",
                    help="maintenance: VIDEO_ID — đặt ảnh đại diện từ --thumbnail")
    ap.add_argument("--set-privacy", default="",
                    help="maintenance: VIDEO_ID — set its privacy to --privacy")
    ap.add_argument("--playlist-add", default="",
                    help="maintenance: VIDEO_ID — add it to --playlist")
    ap.add_argument("--publish-at", dest="publish_at", default="",
                    help="scheduled publish RFC3339 UTC (vd 2026-06-25T12:00:00Z); video lên private rồi tự public tới giờ")
    ap.add_argument("--update-desc", default="",
                    help="maintenance: VIDEO_ID — replace its description (needs --title + --desc/--desc-file)")
    args = ap.parse_args()
    if args.auth:
        _creds(interactive=True)
        return 0
    if args.desc_file:
        with open(args.desc_file, encoding="utf-8-sig") as f:
            args.desc = f.read()
    if args.set_thumb:
        from googleapiclient.http import MediaFileUpload
        _yt().thumbnails().set(videoId=args.set_thumb,
                               media_body=MediaFileUpload(args.thumbnail)).execute()
        print(f"THUMB_OK={args.set_thumb}")
        return 0
    if args.set_privacy:
        set_privacy(_yt(), args.set_privacy, args.privacy)
        return 0
    if args.playlist_add:
        add_to_playlist(_yt(), args.playlist_add, args.playlist or DEFAULT_PLAYLIST)
        return 0
    if args.update_desc:
        yt = _yt()
        yt.videos().update(part="snippet", body={
            "id": args.update_desc,
            "snippet": {"title": (args.title or "")[:95], "description": args.desc[:4900],
                        "categoryId": "28"}}).execute()
        print(f"DESC_OK={args.update_desc}")
        return 0
    if not args.file or not args.title:
        raise SystemExit("--file and --title required")
    title = args.title + (" #Shorts" if args.shorts else "")
    desc = args.desc + ("\n#Shorts" if args.shorts else "")
    upload(args.file, title, desc, [t.strip() for t in args.tags.split(",") if t.strip()],
           args.privacy, playlist=args.playlist, thumbnail=args.thumbnail, publish_at=args.publish_at)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
