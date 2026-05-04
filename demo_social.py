"""
Demo Social Media Server
Runs 3 fake social media platforms locally for testing.
Run with: python demo_social.py
"""

from flask import Flask, request, jsonify, render_template_string, send_file
import os
import base64
from datetime import datetime

# ── Shared post storage (in memory) ──────────────────────────
posts = {
    "instagram": [],
    "facebook": [],
    "twitter": []
}

# ── Single Flask app serving all 3 platforms ─────────────────
app = Flask(__name__)


# ── API endpoint — receives posts from market advisor ─────────
@app.route("/api/post", methods=["POST"])
def receive_post():
    data = request.json
    platform = data.get("platform", "").lower()
    caption = data.get("caption", "")
    image_path = data.get("image_path", "")

    if platform not in posts:
        return jsonify({"error": f"Unknown platform: {platform}"}), 400

    image_b64 = None
    if image_path:
        print(f"[DemoSocial] Trying image path: {image_path}")
        if os.path.exists(image_path):
            print(f"[DemoSocial] ✅ Image found!")
            with open(image_path, "rb") as f:
                image_b64 = base64.b64encode(f.read()).decode("utf-8")
            print(f"[DemoSocial] ✅ Image encoded, size: {len(image_b64)}")
        else:
            print(f"[DemoSocial] ❌ Image NOT found at: {image_path}")

    posts[platform].insert(0, {
        "caption": caption,
        "image_b64": image_b64,
        "time": datetime.now().strftime("%B %d, %Y at %I:%M %p")
    })

    print(f"[DemoSocial] ✅ Post received for {platform}")
    return jsonify({"status": "posted", "platform": platform})


# ✅ CHANGED: now serves the new Instagram HTML file
@app.route("/instagram")
def instagram():
    return send_file(os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo_instagram.html"))


# ✅ NEW: JSON endpoint so instagram.js can poll for new posts
@app.route("/posts")
def get_posts():
    return jsonify(posts)


# ── Facebook Feed ─────────────────────────────────────────────
@app.route("/facebook")
def facebook():
    return render_template_string(FACEBOOK_TEMPLATE, posts=posts["facebook"])


# ── Twitter Feed ──────────────────────────────────────────────
@app.route("/twitter")
def twitter():
    return render_template_string(TWITTER_TEMPLATE, posts=posts["twitter"])


# ── Home page — links to all 3 ────────────────────────────────
@app.route("/")
def home():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
  <title>Demo Social Media</title>
  <style>
    body { font-family: sans-serif; background: #111; color: #fff; text-align: center; padding: 3rem; }
    h1 { margin-bottom: 2rem; }
    .links { display: flex; justify-content: center; gap: 1rem; flex-wrap: wrap; }
    a { padding: 1rem 2rem; border-radius: 10px; text-decoration: none; font-weight: bold; font-size: 1rem; }
    .ig { background: linear-gradient(135deg, #f09433, #e6683c, #dc2743, #cc2366, #bc1888); color: white; }
    .fb { background: #1877f2; color: white; }
    .tw { background: #000; color: white; border: 1px solid #333; }
    p { color: #888; margin-top: 2rem; font-size: 0.9rem; }
  </style>
</head>
<body>
  <h1>🧪 Demo Social Media</h1>
  <div class="links">
    <a href="/instagram" class="ig">📸 Instagram</a>
    <a href="/facebook" class="fb">👥 Facebook</a>
    <a href="/twitter" class="tw">🐦 Twitter/X</a>
  </div>
  <p>Posts from your AI Market Advisor will appear here automatically.</p>
</body>
</html>
""")


# ── Templates ─────────────────────────────────────────────────

FACEBOOK_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
  <title>Demo Facebook</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, sans-serif; background: #f0f2f5; color: #1c1e21; }
    .header { background: #1877f2; padding: 0.8rem 1rem; color: white; font-weight: 700; font-size: 1.4rem; position: sticky; top: 0; z-index: 10; }
    .feed { max-width: 500px; margin: 1rem auto; padding: 0 0.5rem; }
    .post { background: white; border-radius: 8px; margin-bottom: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .post-header { padding: 0.8rem 1rem; display: flex; align-items: center; gap: 0.7rem; }
    .avatar { width: 40px; height: 40px; border-radius: 50%; background: #1877f2; display: flex; align-items: center; justify-content: center; color: white; font-weight: 700; }
    .page-name { font-weight: 700; font-size: 0.9rem; }
    .post-time { font-size: 0.78rem; color: #65676b; }
    .post-caption { padding: 0 1rem 0.8rem; font-size: 0.95rem; line-height: 1.5; }
    .post img { width: 100%; display: block; }
    .post-actions { padding: 0.5rem 1rem; border-top: 1px solid #e4e6ea; display: flex; gap: 1rem; color: #65676b; font-size: 0.9rem; }
    .post-actions span { cursor: pointer; padding: 0.4rem 0.6rem; border-radius: 4px; }
    .post-actions span:hover { background: #f0f2f5; }
    .empty { text-align: center; padding: 3rem; color: #888; background: white; border-radius: 8px; }
    .no-image { background: #f0f2f5; aspect-ratio: 1; display: flex; align-items: center; justify-content: center; color: #bbb; font-size: 2rem; }
  </style>
  <meta http-equiv="refresh" content="10">
</head>
<body>
  <div class="header">f  Facebook</div>
  <div class="feed">
    {% if posts %}
      {% for post in posts %}
      <div class="post">
        <div class="post-header">
          <div class="avatar">AI</div>
          <div>
            <div class="page-name">AI Market Advisor</div>
            <div class="post-time">{{ post.time }}</div>
          </div>
        </div>
        <div class="post-caption">{{ post.caption }}</div>
        {% if post.image_b64 %}
          <img src="data:image/png;base64,{{ post.image_b64 }}" alt="Ad">
        {% else %}
          <div class="no-image">🖼️</div>
        {% endif %}
        <div class="post-actions">
          <span>👍 Like</span>
          <span>💬 Comment</span>
          <span>↗️ Share</span>
        </div>
      </div>
      {% endfor %}
    {% else %}
      <div class="empty">
        <div style="font-size:3rem;margin-bottom:1rem;">📭</div>
        <div>No posts yet. Generate a strategy to post here!</div>
      </div>
    {% endif %}
  </div>
</body>
</html>
"""

TWITTER_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
  <title>Demo Twitter/X</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, sans-serif; background: #000; color: #e7e9ea; }
    .header { border-bottom: 1px solid #2f3336; padding: 1rem; font-weight: 700; font-size: 1.1rem; position: sticky; top: 0; background: rgba(0,0,0,0.85); backdrop-filter: blur(10px); z-index: 10; }
    .feed { max-width: 600px; margin: 0 auto; }
    .post { border-bottom: 1px solid #2f3336; padding: 1rem; display: flex; gap: 0.8rem; }
    .avatar { width: 40px; height: 40px; border-radius: 50%; background: #1d9bf0; flex-shrink: 0; display: flex; align-items: center; justify-content: center; color: white; font-weight: 700; }
    .post-content { flex: 1; }
    .post-header { display: flex; align-items: center; gap: 0.4rem; margin-bottom: 0.4rem; }
    .name { font-weight: 700; font-size: 0.95rem; }
    .handle { color: #71767b; font-size: 0.88rem; }
    .post-text { font-size: 0.95rem; line-height: 1.5; margin-bottom: 0.7rem; }
    .post img { width: 100%; border-radius: 12px; border: 1px solid #2f3336; display: block; margin-bottom: 0.7rem; }
    .post-actions { display: flex; gap: 1.5rem; color: #71767b; font-size: 0.85rem; }
    .post-time { color: #71767b; font-size: 0.82rem; }
    .empty { text-align: center; padding: 3rem; color: #555; }
    .no-image { background: #111; aspect-ratio: 16/9; border-radius: 12px; display: flex; align-items: center; justify-content: center; color: #333; font-size: 2rem; margin-bottom: 0.7rem; }
  </style>
  <meta http-equiv="refresh" content="10">
</head>
<body>
  <div class="header">🐦 For You</div>
  <div class="feed">
    {% if posts %}
      {% for post in posts %}
      <div class="post">
        <div class="avatar">AI</div>
        <div class="post-content">
          <div class="post-header">
            <span class="name">AI Market Advisor</span>
            <span class="handle">@ai_market_advisor</span>
            <span class="post-time">· {{ post.time }}</span>
          </div>
          <div class="post-text">{{ post.caption[:280] }}</div>
          {% if post.image_b64 %}
            <img src="data:image/png;base64,{{ post.image_b64 }}" alt="Ad">
          {% else %}
            <div class="no-image">🖼️</div>
          {% endif %}
          <div class="post-actions">
            <span>💬 Reply</span>
            <span>🔁 Repost</span>
            <span>❤️ Like</span>
            <span>↗️ Share</span>
          </div>
        </div>
      </div>
      {% endfor %}
    {% else %}
      <div class="empty">
        <div style="font-size:3rem;margin-bottom:1rem;">📭</div>
        <div>No posts yet. Generate a strategy to post here!</div>
      </div>
    {% endif %}
  </div>
</body>
</html>
"""


if __name__ == "__main__":
    print("=" * 50)
    print("  Demo Social Media Server")
    print("  Home:      http://localhost:5001")
    print("  Instagram: http://localhost:5001/instagram")
    print("  Facebook:  http://localhost:5001/facebook")
    print("  Twitter:   http://localhost:5001/twitter")
    print("=" * 50)
    app.run(port=5001, debug=False, use_reloader=False)