/**
 * Backend danh sách đăng ký nhận bản tin (Google Apps Script, gắn với một Google Sheet).
 *
 * SETUP (one-time, ~5 phút):
 *   1. Tạo Google Sheet mới tên "<Tên kênh> Subscribers" (sheets.new).
 *   2. Extensions > Apps Script → xóa code mặc định, dán TOÀN BỘ file này.
 *   3. Sửa SECRET thành một chuỗi ngẫu nhiên dài (giữ kín), rồi điền khối NHẬN DIỆN.
 *   4. Deploy > New deployment > type "Web app":
 *        - Execute as: Me
 *        - Who has access: Anyone
 *      → Copy "Web app URL" (dạng https://script.google.com/macros/s/XXX/exec).
 *   5. Điền URL + SECRET vào file cấu hình email của kênh (xem send_newsletter.py).
 *
 * Endpoints:
 *   POST  (email=...)                      → đăng ký (dedup, lưu vào sheet "subs")
 *   GET   ?action=list&token=SECRET        → JSON danh sách email (wrapper dùng để gửi)
 *   GET   ?action=unsub&email=..&t=TOKEN   → hủy đăng ký (link trong mỗi email)
 */
var SECRET = 'CHANGE_ME_TO_A_LONG_RANDOM_STRING';

// ── NHẬN DIỆN KÊNH — điền trước khi dán vào Apps Script ─────────────────────
// Khối này là bản sao thủ công của `channel.yml:brand`: Apps Script chạy trên máy chủ
// Google nên không đọc được file cấu hình nào của bạn. Để nguyên giá trị mẫu thì thư
// chào mừng gửi đi sẽ mang tên kênh mẫu — người đăng ký là người đầu tiên thấy.
var BRAND_A    = 'Tên';               // nửa đầu tên hiển thị
var BRAND_B    = 'Kênh';              // nửa sau
var AUTHOR     = 'Tên tác giả';
var TAGLINE    = 'bản tin định kỳ';   // ghép vào câu "Cảm ơn bạn đã đăng ký X — <tagline>"
var SITE_URL   = 'https://vi-du.vn/news/ten-kenh/';
var ACCENT     = '#0ea5b7';           // màu nhấn; nền email TRẮNG nên phải đủ tương phản
var TEST_EMAIL = 'ban@example.com';   // chỉ dùng cho testWelcome()
var BRAND      = BRAND_A + ' ' + BRAND_B;

function _sheet() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  return ss.getSheetByName('subs') || ss.insertSheet('subs');
}

function _json(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

function _tok(email) {
  return Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, email + SECRET)
    .map(function (b) { b = (b + 256) % 256; return (b < 16 ? '0' : '') + b.toString(16); })
    .join('').slice(0, 16);
}

function _nextFridayVN() {
  var now = new Date();
  var dow = parseInt(Utilities.formatDate(now, 'Asia/Ho_Chi_Minh', 'u'), 10); // 1=Mon..7=Sun
  var hour = parseInt(Utilities.formatDate(now, 'Asia/Ho_Chi_Minh', 'H'), 10);
  var days = (5 - dow + 7) % 7;
  if (days === 0 && hour >= 21) days = 7; // Friday after send time -> next week
  var d = new Date(now.getTime() + days * 86400000);
  return Utilities.formatDate(d, 'Asia/Ho_Chi_Minh', 'dd/MM/yyyy');
}

function _welcomeEmail(email) {
  var friday = _nextFridayVN();
  var unsub = ScriptApp.getService().getUrl() +
    '?action=unsub&email=' + encodeURIComponent(email) + '&t=' + _tok(email);
  var html =
    '<div style="max-width:560px;margin:0 auto;font-family:Segoe UI,Arial,sans-serif;padding:24px 16px">' +
    '<div style="font-size:22px;font-weight:800;color:#111827">' + BRAND_A + ' <span style="color:' + ACCENT + '">' + BRAND_B + '</span></div>' +
    '<div style="background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:20px;margin-top:14px">' +
    '<h2 style="margin:0 0 10px;color:#111827;font-size:18px">Đăng ký thành công 🎉</h2>' +
    '<p style="color:#374151;line-height:1.65;margin:0">Cảm ơn bạn đã đăng ký <b>' + BRAND + '</b> — ' + TAGLINE + ', do ' + AUTHOR + ' tuyển chọn &amp; đọc.</p>' +
    '<p style="color:#374151;line-height:1.65">📬 Bản tin tiếp theo sẽ đến hộp thư của bạn vào <b>thứ Sáu, ' + friday + '</b> (khoảng 21:30, giờ Việt Nam): tổng quan tuần, top 5 tin nóng, kèm bản đọc audio và video recap.</p>' +
    '<p style="margin:18px 0 0;text-align:center"><a href="' + SITE_URL + '" style="background:' + ACCENT + ';color:#fff;font-weight:700;padding:10px 20px;border-radius:9px;text-decoration:none">Xem các số đã phát hành →</a></p>' +
    '</div>' +
    '<p style="color:#9ca3af;font-size:12px;text-align:center;margin-top:14px">Nếu không phải bạn đăng ký, <a href="' + unsub + '" style="color:#9ca3af">hủy tại đây</a>.</p>' +
    '</div>';
  MailApp.sendEmail({
    to: email,
    subject: BRAND + ' — Đăng ký thành công, hẹn thứ Sáu ' + friday,
    htmlBody: html,
    name: BRAND + ' · ' + AUTHOR
  });
}

function doPost(e) {
  var email = ((e && e.parameter && e.parameter.email) || '').trim().toLowerCase();
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) return _json({ ok: false, err: 'invalid' });
  var sh = _sheet();
  var data = sh.getDataRange().getValues();
  for (var i = 0; i < data.length; i++) {
    if (String(data[i][0]).toLowerCase() === email) return _json({ ok: true, dup: true });
  }
  sh.appendRow([email, new Date()]);
  // welcome email ngay lập tức (best-effort; lỗi được ghi vào sheet "log" để debug)
  try { _welcomeEmail(email); } catch (err) {
    _log('welcome FAILED for ' + email + ': ' + err);
  }
  return _json({ ok: true });
}

function _log(msg) {
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sh = ss.getSheetByName('log') || ss.insertSheet('log');
    sh.appendRow([new Date(), msg]);
  } catch (e) {}
}

/**
 * CHẠY TAY 1 LẦN trong editor (Run > testWelcome) để Google hiện hộp thoại
 * CẤP QUYỀN GỬI MAIL (scope mới của v2 — thiếu bước này welcome email sẽ
 * lỗi im lặng). Chạy xong sẽ nhận 1 email test ở hộp thư của bạn.
 */
function testWelcome() {
  _welcomeEmail(TEST_EMAIL);
}

function doGet(e) {
  var p = (e && e.parameter) || {};
  if (p.action === 'list') {
    if (p.token !== SECRET) return _json({ ok: false, err: 'auth' });
    var rows = _sheet().getDataRange().getValues();
    var emails = [];
    for (var i = 0; i < rows.length; i++) {
      if (rows[i][0]) emails.push(String(rows[i][0]).toLowerCase());
    }
    return _json({ ok: true, emails: emails });
  }
  if (p.action === 'unsub') {
    var email = (p.email || '').trim().toLowerCase();
    if (p.t !== _tok(email)) {
      return HtmlService.createHtmlOutput('<h3>Link không hợp lệ.</h3>');
    }
    var sh = _sheet();
    var data = sh.getDataRange().getValues();
    for (var j = data.length - 1; j >= 0; j--) {
      if (String(data[j][0]).toLowerCase() === email) sh.deleteRow(j + 1);
    }
    return HtmlService.createHtmlOutput(
      '<div style="font-family:sans-serif;max-width:480px;margin:60px auto;text-align:center">' +
      '<h2>Đã hủy đăng ký 👋</h2><p>' + email + ' sẽ không nhận bản tin ' + BRAND + ' nữa.</p>' +
      '<p><a href="' + SITE_URL + '">Về trang ' + BRAND + '</a></p></div>');
  }
  return _json({ ok: false, err: 'unknown_action' });
}
