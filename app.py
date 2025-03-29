from flask import Flask, render_template, Response, abort, make_response
import markdown2
import frontmatter
import os
from flask_caching import Cache

app = Flask(__name__)

# Configure caching (stores rendered HTML files in cache folder)
app.config['CACHE_TYPE'] = 'filesystem'
app.config['CACHE_DIR'] = 'cache'
cache = Cache(app)
cache.init_app(app)

# Ensure cache folder exists
if not os.path.exists('cache'):
    os.makedirs('cache')


@app.after_request
def add_header(response):
    if "adsbygoogle.js" in response.headers.get("Content-Type", ""):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# Function to parse markdown file and extract metadata
def render_markdown(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            post = frontmatter.loads(f.read())  # Correct method
        return post.metadata, markdown2.markdown(post.content)
    except FileNotFoundError:
        return None, None

@app.route("/blog.html")
@cache.cached(timeout=3600, key_prefix="blog_home")
def blog_home():
    posts = []
    for filename in os.listdir("content"):
        if filename.endswith(".md"):
            filepath = os.path.join("content", filename)
            with open(filepath, "r", encoding="utf-8") as f:
                metadata = frontmatter.load(f)
                posts.append({
                    "title": metadata.get("title", "Untitled"),
                    "date": metadata.get("date", "Unknown"),
                    "slug": filename.replace(".md", "")
                })

    posts.sort(key=lambda x: x["date"], reverse=True)  # Newest first
    return render_template("blog_home.html", posts=posts)

@app.route("/blog/<slug>.html")
def blog_post(slug):
    cache_key = f"blog_{slug}"  # Manually define a unique cache key
    cached_content = cache.get(cache_key)

    if cached_content:  # Serve from cache if available
        return cached_content

    filepath = f"content/{slug}.md"
    metadata, html_content = render_markdown(filepath)

    if not metadata:
        abort(404)

    response = render_template("blog.html", metadata=metadata, content=html_content)

    cache.set(cache_key, response, timeout=3600)  # Manually cache the response
    return response


@app.route("/sitemap.xml")
def sitemap():
    files = [f for f in os.listdir("content") if f.endswith(".md")]
    urls = [f"https://emojibioai.com/blog/{f.replace('.md', '')}" for f in files]
    sitemap_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    {''.join([f"<url><loc>{url}</loc></url>" for url in urls])}
    </urlset>"""
    return Response(sitemap_xml, mimetype="application/xml")

@app.route("/robots.txt")
def robots():
    robots_txt = """User-agent: *
Allow: /blog/
Disallow: /api/
Sitemap: https://emojibioai.com/sitemap.xml"""
    return Response(robots_txt, mimetype="text/plain")

if __name__ == "__main__":
    app.run(debug=True)
