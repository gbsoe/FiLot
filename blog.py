"""
Blog blueprint for the FiLot website
"""

import datetime
from flask import Blueprint, render_template, abort
from models import Post, db

# Create the blueprint
blog_bp = Blueprint('blog', __name__, url_prefix='/blog')

@blog_bp.route('/')
def blog_list():
    """Display list of all blog posts."""
    try:
        posts = Post.query.order_by(Post.published_at.desc()).all()
        
        meta = {
            "title": "FiLot Blog | DeFi Investment Insights & Solana Updates",
            "description": "Latest insights on DeFi yield farming, Solana ecosystem updates, and cryptocurrency investment strategies from the FiLot team.",
            "keywords": "DeFi yield farming blog, Solana investment updates, crypto investment strategies, passive income crypto guide, FiLot investment insights"
        }
        
        return render_template('blog_list.html', posts=posts, meta=meta)
    except Exception as e:
        # Log the error
        import logging
        logging.error(f"Error in blog list: {e}")
        abort(500)

@blog_bp.route('/<slug>')
def blog_post(slug):
    """Display a single blog post."""
    try:
        post = Post.query.filter_by(slug=slug).first_or_404()
        
        # Generate meta tags specific to this post
        meta = {
            "title": f"{post.title} | FiLot Blog",
            "description": post.summary,
            "keywords": ", ".join(post.keywords.split(",")) if post.keywords else "DeFi yield farming, Solana, cryptocurrency, investing"
        }
        
        return render_template('blog_post.html', post=post, meta=meta)
    except Exception as e:
        # Log the error
        import logging
        logging.error(f"Error in blog post {slug}: {e}")
        abort(404)