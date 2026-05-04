"""
AI-Powered Smart Market Strategy Advisor
"""

import os
import json
import uuid
from datetime import datetime, timedelta

from flask import (
    Flask, render_template, request,
    redirect, url_for, jsonify, send_from_directory, send_file, abort
)
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

from config import Config
from models.database import db, Product, ScheduledPost
from modules.strategy_engine import generate_strategy
from modules.image_generator import generate_ad_image, generate_ad_gif
from modules.social_poster import post_to_platform
from modules.voice_generator import get_welcome_audio, get_ready_audio
from modules.pdf_generator import generate_strategy_pdf
from modules.rag_engine import (
    ingest_pdf, retrieve_context, delete_document,
    list_documents, get_stats
)


# ─────────────────────────────────────────────────────────────
# APP INIT
# ─────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

scheduler = BackgroundScheduler(
    jobstores={"default": SQLAlchemyJobStore(url="sqlite:///instance/advisor.db")},
    job_defaults={"coalesce": True, "max_instances": 1}
)


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

DAY_MAP = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6
}

def parse_best_time(time_slot_str, week_offset=0):
    parts = time_slot_str.strip().lower().split()
    if len(parts) < 2:
        return datetime.utcnow() + timedelta(days=3 + week_offset * 7, hours=12)
    day_name  = parts[0]
    time_part = parts[1]
    try:
        hour = int(time_part.replace("pm", "").replace("am", ""))
        if "pm" in time_part and hour != 12:
            hour += 12
        elif "am" in time_part and hour == 12:
            hour = 0
    except ValueError:
        hour = 12
    today = datetime.utcnow()
    target_weekday = DAY_MAP.get(day_name, 0)
    days_ahead = target_weekday - today.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    target_dt = today + timedelta(days=days_ahead + week_offset * 7)
    target_dt = target_dt.replace(hour=hour, minute=0, second=0, microsecond=0)
    return target_dt


def make_caption(strategy):
    cta      = strategy["ad_content"]["call_to_action"]
    hashtags = " ".join(strategy["ad_content"]["hashtags"])
    base     = strategy.get("caption", cta)
    return f"{base}\n\n{hashtags}"


def execute_scheduled_post(post_id):
    with app.app_context():
        post = ScheduledPost.query.get(post_id)
        if not post:
            return
        try:
            post_url = post_to_platform(
                platform=post.platform,
                image_path=post.image_path,
                caption=post.caption
            )
            post.status  = "posted"
            post.post_url = post_url
        except Exception as e:
            post.status = "failed"
            post.error_message = str(e)
        finally:
            db.session.commit()


# ─────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/audio/welcome")
def audio_welcome():
    language   = request.args.get("lang", "english")
    audio_path = get_welcome_audio(language)
    if audio_path and os.path.exists(audio_path):
        return send_from_directory("static/audio", os.path.basename(audio_path))
    return "", 404


@app.route("/static/audio/<filename>")
def serve_audio(filename):
    return send_from_directory("static/audio", filename)


@app.route("/analyze", methods=["POST"])
def analyze():
    # ── 1. Form data ──────────────────────────────────────────
    product_name   = request.form.get("product_name",  "").strip()
    description    = request.form.get("description",   "").strip()
    category       = request.form.get("category",      "").strip()
    price_range    = request.form.get("price_range",   "").strip()
    usp            = request.form.get("usp",           "").strip()
    business_name  = request.form.get("business_name", "").strip()
    business_type  = request.form.get("business_type", "").strip()
    business_size  = request.form.get("business_size", "").strip()
    years_active   = request.form.get("years_active",  "").strip()
    country        = request.form.get("country",       "").strip()
    city           = request.form.get("city",          "").strip()
    website        = request.form.get("website",       "").strip()
    phone          = request.form.get("phone",         "").strip()
    email          = request.form.get("email",         "").strip()
    language       = request.form.get("language",      "English").strip()
    social_handles = request.form.get("social_handles","").strip()
    budget         = request.form.get("budget",        "Not specified").strip()
    campaign_goal  = request.form.get("campaign_goal", "Brand Awareness").strip()
    tone           = request.form.get("tone",          "Professional").strip()
    target_gender  = request.form.get("target_gender", "All genders").strip()
    target_age     = request.form.get("target_age",    "All ages").strip()
    competitors    = request.form.get("competitors",   "").strip()
    key_message    = request.form.get("key_message",   "").strip()
    platforms_selected = request.form.getlist("platforms")

    if not product_name or not description:
        return render_template("index.html", error="Product name and description are required.")

    product = Product(
        name=product_name,    description=description,
        category=category,    price_range=price_range,    usp=usp,
        business_name=business_name, business_type=business_type,
        business_size=business_size, years_active=years_active,
        country=country,      city=city,          website=website,
        phone=phone,          email=email,         language=language,
        social_handles=social_handles,
        budget=budget,        campaign_goal=campaign_goal, tone=tone,
        target_gender=target_gender, target_age=target_age,
        competitors=competitors, key_message=key_message
    )
    db.session.add(product)
    db.session.commit()

    # ── 2. RAG context retrieval ──────────────────────────────
    rag_query   = f"{product_name} {category} {country} {city} {description} {campaign_goal}"
    rag_context = ""
    try:
    # Search all documents — no tag filtering since tags are empty
        rag_context_main    = retrieve_context(rag_query, top_k=4)
        rag_context_digital = retrieve_context(
            f"social media platforms {country} demographics age income spending",
            top_k=3
        )
        combined = f"{rag_context_main}\n\n{rag_context_digital}".strip()
        rag_context = combined[:3000]

        if rag_context:
            print(f"[App] RAG context injected ({len(rag_context)} chars)")
        else:
            print("[App] No RAG context found")
    except Exception as e:
        print(f"[App] RAG retrieval skipped: {e}")

    # ── 3. Generate strategy ──────────────────────────────────
    try:
        strategy = generate_strategy(
            product_name, description, country, price_range, budget,
            business_name=business_name, category=category,
            campaign_goal=campaign_goal, tone=tone,
            target_gender=target_gender, target_age=target_age,
            competitors=competitors, usp=usp, language=language,
            city=city, business_size=business_size,
            years_active=years_active, key_message=key_message,
            social_handles=social_handles, rag_context=rag_context
        )
    except Exception as e:
        return render_template("index.html",
            error=f"Strategy generation failed: {str(e)}.")

    # ── 3. Handle uploaded image ──────────────────────────────
    uploaded_file   = request.files.get("product_image")
    user_image_path = None
    if uploaded_file and uploaded_file.filename:
        os.makedirs("static/generated_ads", exist_ok=True)
        uid = uuid.uuid4().hex[:8]
        ext = os.path.splitext(uploaded_file.filename)[1].lower() or ".jpg"
        user_image_path = f"static/generated_ads/upload_{uid}{ext}"
        uploaded_file.save(user_image_path)

    # ── 4. Generate ad image ──────────────────────────────────
    caption = make_caption(strategy)
    try:
        image_path, image_url = generate_ad_image(
            strategy.get("image_prompt", f"Modern advertisement for {product_name}"),
            product_name,
            caption=caption,
            hashtags=strategy["ad_content"].get("hashtags", []),
            business_name=business_name,
            phone=phone, email=email, website=website,
            user_image_path=user_image_path
        )
    except Exception as e:
        image_path = "static/generated_ads/placeholder.png"
        image_url  = None
        print(f"[App] Image generation failed: {e}")

    # ── 4b. Generate animated GIF ─────────────────────────────
    video_path = None
    try:
        video_path = generate_ad_gif(image_path, product_name)
    except Exception as e:
        print(f"[App] GIF generation failed: {e}")

    # ── 4c. Generate strategy PDF ─────────────────────────────
    pdf_path = None
    try:
        pdf_path = generate_strategy_pdf(product, strategy, caption)
        print(f"[App] PDF path: {pdf_path}")
    except Exception as e:
        import traceback
        print(f"[App] PDF generation failed: {e}")
        traceback.print_exc()

    # ── 4d. Generate ready voice ──────────────────────────────
    ready_audio_path = None
    try:
        ready_audio_path = get_ready_audio(language=language, product_name=product_name)
    except Exception as e:
        print(f"[App] Voice generation failed: {e}")

    # ── 5. Schedule posts ─────────────────────────────────────
    scheduled_posts_info = []
    for platform_data in strategy.get("platforms", []):
        platform_name = platform_data["name"].lower()
        if not any(p.lower() == platform_name for p in platforms_selected):
            continue
        best_times = platform_data.get("best_times", ["Tuesday 7PM"])
        for week_offset, time_slot in enumerate(best_times[:2]):
            scheduled_time = parse_best_time(time_slot, week_offset=week_offset)
            post = ScheduledPost(
                product_id=product.id, platform=platform_name,
                image_path=image_path, caption=caption,
                scheduled_time=scheduled_time, status="pending"
            )
            db.session.add(post)
            db.session.commit()
            scheduler.add_job(
                func=execute_scheduled_post, trigger="date",
                run_date=scheduled_time, args=[post.id],
                id=f"post_{post.id}", replace_existing=True
            )
            scheduled_posts_info.append({
                "platform": platform_name,
                "time": scheduled_time.strftime("%A, %b %d at %I:%M %p UTC"),
                "time_slot_label": time_slot
            })
            print(f"[App] Scheduled {platform_name} post #{post.id} for {scheduled_time}")

    return render_template(
        "strategy.html",
        product=product,
        strategy=strategy,
        image_path=image_path,
        scheduled_posts=scheduled_posts_info,
        caption=caption,
        video_path=video_path,
        pdf_path=pdf_path,
        ready_audio_path=ready_audio_path
    )


# ── DOWNLOAD ROUTES ───────────────────────────────────────────

@app.route("/download/strategy/<path:filename>")
def download_strategy_pdf(filename):
    """Download the strategy PDF."""
    filepath = filename
    if not os.path.exists(filepath):
        abort(404)
    return send_file(filepath, as_attachment=True,
                     download_name=f"marketing_strategy_{datetime.now().strftime('%Y%m%d')}.pdf")


@app.route("/download/ad/<path:filename>")
def download_ad_image(filename):
    """Download the ad image PNG."""
    filepath = filename
    if not os.path.exists(filepath):
        abort(404)
    return send_file(filepath, as_attachment=True,
                     download_name=f"ad_post_{datetime.now().strftime('%Y%m%d')}.png")


# ── OTHER ROUTES ──────────────────────────────────────────────

@app.route("/knowledge")
def knowledge():
    docs  = list_documents()
    stats = get_stats()
    # Convert tags string back to list for template
    for doc in docs:
        if isinstance(doc.get("tags"), str):
            doc["tags"] = [t.strip() for t in doc["tags"].split(",") if t.strip()]
    return render_template("knowledge.html", documents=docs, stats=stats)


@app.route("/knowledge/upload", methods=["POST"])
def knowledge_upload():
    pdf_file = request.files.get("pdf_file")
    label    = request.form.get("label", "").strip()
    tags_raw = request.form.get("tags",  "").strip()
    tags     = [t.strip() for t in tags_raw.split(",") if t.strip()]

    if not pdf_file or not pdf_file.filename:
        return render_template("knowledge.html",
            documents=list_documents(), stats=get_stats(),
            message="No file selected.", error=True)

    if not pdf_file.filename.lower().endswith(".pdf"):
        return render_template("knowledge.html",
            documents=list_documents(), stats=get_stats(),
            message="Only PDF files are supported.", error=True)

    import os
    from modules.rag_engine import _PDF_DIR
    os.makedirs(_PDF_DIR, exist_ok=True)
    safe_name = pdf_file.filename.replace(" ", "_")
    save_path = os.path.join(_PDF_DIR, safe_name)
    pdf_file.save(save_path)

    result = ingest_pdf(save_path, label=label or None, tags=tags)

    if result["status"] == "ok":
        msg = f"✅ '{result['label']}' indexed — {result['chunk_count']} chunks ready for RAG."
        err = False
    else:
        msg = f"Failed to index PDF: {result.get('message', 'Unknown error')}"
        err = True

    docs  = list_documents()
    stats = get_stats()
    for doc in docs:
        if isinstance(doc.get("tags"), str):
            doc["tags"] = [t.strip() for t in doc["tags"].split(",") if t.strip()]
    return render_template("knowledge.html",
        documents=docs, stats=stats, message=msg, error=err)


@app.route("/knowledge/delete", methods=["POST"])
def knowledge_delete():
    doc_id = request.form.get("doc_id", "").strip()
    if doc_id:
        delete_document(doc_id)
    return redirect(url_for("knowledge"))


@app.route("/dashboard")
def dashboard():
    posts = ScheduledPost.query.order_by(ScheduledPost.scheduled_time.asc()).all()
    now   = datetime.utcnow()
    return render_template("dashboard.html", posts=posts, now=now)


@app.route("/dashboard/data")
def dashboard_data():
    posts = ScheduledPost.query.order_by(ScheduledPost.scheduled_time.asc()).all()
    return jsonify([{
        "id": p.id, "platform": p.platform, "status": p.status,
        "scheduled_time": p.scheduled_time.strftime("%b %d %I:%M %p"),
        "post_url": p.post_url, "error": p.error_message
    } for p in posts])


@app.route("/post/<int:post_id>/retry")
def retry_post(post_id):
    execute_scheduled_post(post_id)
    return redirect(url_for("dashboard"))


@app.route("/post/<int:post_id>/delete")
def delete_post(post_id):
    post   = ScheduledPost.query.get_or_404(post_id)
    job_id = f"post_{post_id}"
    try:
        scheduler.remove_job(job_id)
    except Exception:
        pass
    db.session.delete(post)
    db.session.commit()
    return redirect(url_for("dashboard"))


@app.route("/static/generated_ads/<filename>")
def serve_ad_image(filename):
    return send_from_directory("static/generated_ads", filename)


# ─────────────────────────────────────────────────────────────
# STARTUP
# ─────────────────────────────────────────────────────────────
with app.app_context():
    os.makedirs("static/generated_ads", exist_ok=True)
    os.makedirs("static/audio", exist_ok=True)
    db.create_all()

scheduler.start()

if __name__ == "__main__":
    print("=" * 55)
    print("Meon Advertising Assistant")
    print("  Running at: http://localhost:5000")
    print("=" * 55)
    app.run(debug=True, use_reloader=False)