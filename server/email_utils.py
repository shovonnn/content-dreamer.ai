from __future__ import annotations

from typing import Optional, Tuple, Dict, Any
from datetime import datetime
import json

from models.suggestion import Suggestion
from models.report import Report
import config


def generate_premium_email_template(
    *,
    subject: str,
    preheader: str = "",
    body_html: str,
    brand_name: str = "ContentDreamer AI",
    logo_url: Optional[str] = None,
    cta_text: Optional[str] = None,
    cta_url: Optional[str] = None,
    footer_address: Optional[str] = None,
    unsubscribe_url: Optional[str] = "{{unsubscribe_url}}",
) -> str:
    """
    Build a premium, mobile-friendly HTML email suitable for Mailgun.

    Notes for Mailgun:
    - You can use this HTML directly with the `html` field of the messages API.
    - To personalize, either inject values before sending or use stored templates.
    - We keep an {{unsubscribe_url}} placeholder; if you use Mailgun mailing lists, you can
      replace it with the list unsubscribe URL or set appropriate headers.
    """

    brand = brand_name or ""
    addr = footer_address or f"{brand}"
    # Basic color palette
    bg = "#f5f7fb"
    text = "#111827"
    muted = "#6b7280"
    card = "#ffffff"
    border = "#e5e7eb"
    primary = "#BA7308"

    # Hidden preheader text for better inbox previews
    preheader_html = f"""
    <div style=\"display:none;max-height:0;overflow:hidden;font-size:1px;line-height:1px;color:#fff;opacity:0;\">{preheader or ''}</div>
    """.strip()

    # Header with optional logo
    logo_section = (
        f"<img src=\"{logo_url}\" alt=\"{brand}\" style=\"height:36px;display:block;\">" if logo_url else f"<div style=\"font-size:18px;font-weight:700;color:{text}\">{brand}</div>"
    )

    # Optional CTA button
    cta_button = (
        f"""
        <table role=\"presentation\" cellspacing=\"0\" cellpadding=\"0\" border=\"0\" align=\"center\" style=\"margin:24px 0 0 0;\">
          <tr>
            <td bgcolor=\"{primary}\" style=\"border-radius:10px;\">
              <a href=\"{cta_url}\" style=\"font-size:16px;line-height:16px;color:#ffffff;text-decoration:none;padding:14px 22px;display:inline-block;font-weight:600;\">{cta_text}</a>
            </td>
          </tr>
        </table>
        """.strip()
        if cta_text and cta_url
        else ""
    )

    now = datetime.utcnow().strftime("%b %d, %Y")

    html = f"""
    <!doctype html>
    <html lang=\"en\">
    <head>
      <meta charset=\"utf-8\">
      <meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
      <meta name=\"x-apple-disable-message-reformatting\">
      <title>{subject}</title>
      <style>
        @media (max-width: 600px) {{
          .container {{ width: 100% !important; }}
          .px {{ padding-left: 16px !important; padding-right: 16px !important; }}
        }}
        a {{ color: {primary}; }}
      </style>
    </head>
    <body style=\"margin:0;background:{bg};\">
      {preheader_html}
      <table role=\"presentation\" cellpadding=\"0\" cellspacing=\"0\" width=\"100%\" style=\"background:{bg};\">
        <tr>
          <td align=\"center\">
            <table class=\"container\" role=\"presentation\" cellpadding=\"0\" cellspacing=\"0\" width=\"600\" style=\"width:600px;max-width:600px;margin:0 auto;\">
              <tr>
                <td class=\"px\" style=\"padding:28px 24px;\">
                  {logo_section}
                </td>
              </tr>
              <tr>
                <td class=\"px\" style=\"padding:0 24px 40px 24px;\">
                  <table role=\"presentation\" width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" style=\"background:{card};border:1px solid {border};border-radius:14px;overflow:hidden;\">
                    <tr>
                      <td style=\"padding:28px 24px;\">
                        <h1 style=\"margin:0 0 8px 0;font-size:22px;line-height:1.3;color:{text};\">{subject}</h1>
                        <div style=\"color:{muted};font-size:14px;margin:0 0 18px 0;\">{now}</div>
                        <div style=\"font-size:16px;line-height:1.6;color:{text};\">{body_html}</div>
                        {cta_button}
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
              <tr>
                <td class=\"px\" style=\"padding:0 24px 24px 24px;\">
                  <div style=\"text-align:center;color:{muted};font-size:12px;line-height:1.6;\">
                    <div style=\"margin-bottom:6px;\">{addr}</div>
                    <div>
                      <a href=\"{unsubscribe_url}\" style=\"color:{muted};text-decoration:underline;\">Unsubscribe</a>
                      <span style=\"padding:0 6px;color:{muted};\">·</span>
                      <a href=\"{'https://contentdreamer.ai'}\" style=\"color:{muted};text-decoration:underline;\">Visit website</a>
                    </div>
                  </div>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    </body>
    </html>
    """
    return html


def _find_top_suggestion(report_id: str, kind: str) -> Optional[Suggestion]:
    return (
        Suggestion.query.filter_by(report_id=report_id, kind=kind)
        .order_by(Suggestion.rank.desc())
        .first()
    )


def generate_report_summary_email(
    report_id: str,
    *,
    logo_url: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Build a subject and HTML for a report summary email with 5 top picks:
    - 1 article idea
    - 1 tweet idea
    - 1 reply tweet
    - 1 meme idea
    - 1 slop idea

    Returns: (subject, html)
    """
    rep: Report | None = Report.query.get(report_id)
    if not rep:
        subject = "Your ContentDreamer report is ready"
        body = "We could not locate the report."
        return subject, generate_premium_email_template(subject=subject, body_html=body, logo_url=logo_url)

    product = getattr(rep, "product", None)
    product_name = getattr(product, "name", "Your product")
    base_url = "https://contentdreamer.ai"
    report_url = f"{base_url}/report/{rep.id}"

    # pick top by kind
    art = _find_top_suggestion(rep.id, "article_headline")
    tw = _find_top_suggestion(rep.id, "tweet")
    rep_tw = _find_top_suggestion(rep.id, "tweet_reply")
    meme = _find_top_suggestion(rep.id, "meme_concept")
    slop = _find_top_suggestion(rep.id, "slop_concept")

    # helper to safely get JSON meta
    def meta_of(s: Optional[Suggestion]) -> Dict[str, Any]:
        if not s:
            return {}
        try:
            return json.loads(s.meta_json or "{}")
        except Exception:
            return {}

    m_art = meta_of(art)
    m_tw = meta_of(tw)
    m_rep = meta_of(rep_tw)
    m_meme = meta_of(meme)
    m_slop = meta_of(slop)

    # Build the inner content as bullet-like cards
    def card(label: str, content: str, hint: Optional[str] = None) -> str:
        if not content:
            content = "No suggestion available yet — check your report for live updates."
        hint_html = f"<div style=\"margin-top:6px;color:#6b7280;font-size:13px\">{hint}</div>" if hint else ""
        return f"""
        <table role=\"presentation\" width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" style=\"border:1px solid #e5e7eb;border-radius:12px;padding:14px;margin:0 0 12px 0;background:#fff;\">
          <tr>
            <td style=\"font-size:12px;color:#6b7280;text-transform:uppercase;letter-spacing:0.02em;\">{label}</td>
          </tr>
          <tr>
            <td style=\"padding-top:6px;font-size:16px;line-height:1.6;color:#111827;white-space:pre-wrap;\">{content}</td>
          </tr>
          {f'<tr><td>{hint_html}</td></tr>' if hint_html else ''}
        </table>
        """

    reply_hint = None
    st = (m_rep.get("source_tweet") if isinstance(m_rep, dict) else None) or {}
    try:
        st_id = st.get("id_str") or st.get("id")
        handle = st.get("user_screen_name") or st.get("screen_name") or st.get("user_handle") or st.get("username")
        url = (f"https://x.com/{handle}/status/{st_id}" if st_id and handle else (f"https://x.com/i/web/status/{st_id}" if st_id else (st.get("url") if isinstance(st.get("url"), str) else None)))
        metrics = " ".join([
            f"❤️ {st.get('like_count', 0)}",
            f"🔁 {st.get('retweet_count', 0)}",
            f"💬 {st.get('reply_count', 0)}",
        ])
        bits = [b for b in [metrics, url] if b]
        reply_hint = " • ".join(bits) if bits else None
    except Exception:
        reply_hint = None

    def render_native_reply(source_tweet: Dict[str, Any], reply_text: str) -> str:
        """Render a tweet-like block: original tweet on top, our reply below."""
        name = source_tweet.get("user_name") or "User"
        handle = source_tweet.get("user_screen_name") or source_tweet.get("screen_name") or source_tweet.get("user_handle") or source_tweet.get("username")
        at_handle = f"@{handle}" if handle else ""
        t_text = source_tweet.get("text") or ""
        lk = source_tweet.get("like_count", 0)
        rt = source_tweet.get("retweet_count", 0)
        rp = source_tweet.get("reply_count", 0)
        st_id = source_tweet.get("id_str") or source_tweet.get("id")
        url = (
            f"https://x.com/{handle}/status/{st_id}" if st_id and handle else (
                f"https://x.com/i/web/status/{st_id}" if st_id else (source_tweet.get("url") if isinstance(source_tweet.get("url"), str) else None)
            )
        )
        # Simple avatar using initials
        initials = "".join([p[0] for p in (name or "").split()[:2] if p]) or (at_handle[1:2] if at_handle else "•")
        open_link = f"<a href=\"{url}\" target=\"_blank\" rel=\"noopener\" style=\"color:#3b82f6;text-decoration:underline;\">Open on X ↗</a>" if url else ""
        return f"""
        <table role=\"presentation\" width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" style=\"border:1px solid #e5e7eb;border-radius:12px;padding:14px;margin:0 0 12px 0;background:#fff;\">
          <tr>
            <td>
              <table role=\"presentation\" width=\"100%\" cellpadding=\"0\" cellspacing=\"0\">
                <tr>
                  <td style=\"vertical-align:top;\">
                    <div style=\"width:36px;height:36px;border-radius:50%;background:#e5e7eb;color:#374151;display:inline-flex;align-items:center;justify-content:center;font-weight:700;\">{initials}</div>
                  </td>
                  <td style=\"padding-left:10px;\">
                    <div style=\"font-weight:600;color:#111827;\">{name}</div>
                    <div style=\"color:#6b7280;font-size:13px;\">{at_handle}</div>
                  </td>
                  <td style=\"text-align:right;vertical-align:top;\">{open_link}</td>
                </tr>
              </table>
              <div style=\"margin-top:10px;color:#111827;line-height:1.6;white-space:pre-wrap;font-size:16px;\">{t_text}</div>
              <div style=\"margin-top:10px;color:#6b7280;font-size:13px;\">❤️ {lk} &nbsp; 🔁 {rt} &nbsp; 💬 {rp}</div>
              <div style=\"height:1px;background:#e5e7eb;margin:14px 0;\"></div>
              <div style=\"font-size:12px;color:#6b7280;text-transform:uppercase;letter-spacing:0.02em;margin-bottom:6px;\">Your reply</div>
              <div style=\"border:1px solid #e5e7eb;border-radius:10px;padding:12px;color:#111827;line-height:1.6;white-space:pre-wrap;background:#fafafa;\">{reply_text}</div>
            </td>
          </tr>
        </table>
        """

    body_parts = [
        f"<p style=\"margin:0 0 16px 0\">Here are five ideas generated for <strong>{product_name}</strong>. Click through to see your full report and generate long‑form content or assets.</p>",
        card("Article idea", art.text if art else "", m_art.get("reason")),
        card("Tweet idea", tw.text if tw else "", m_tw.get("reason")),
        (
            render_native_reply(st, rep_tw.text) if (rep_tw and isinstance(st, dict) and (st.get("text")))
            else card("Reply tweet", rep_tw.text if rep_tw else "", reply_hint or m_rep.get("reason"))
        ),
        card("Meme concept", meme.text if meme else "", m_meme.get("reason")),
        card("Slop concept", slop.text if slop else "", m_slop.get("reason")),
        f"<p style=\"margin:10px 0 0 0;color:#6b7280;font-size:13px\">Tip: Open the report to unlock more suggestions and one‑click generators.</p>",
    ]
    inner = "".join(body_parts)

    subject = f"Your content ideas have been generated"
    html = generate_premium_email_template(
        subject=subject,
        preheader=f"Your latest ideas for {product_name}",
        body_html=inner,
        brand_name="ContentDreamer AI",
        logo_url=logo_url,
        cta_text="Open your report",
        cta_url=report_url,
        footer_address=None,
        unsubscribe_url="https://contentdreamer.ai/unsubscribe",
    )
    return subject, html
