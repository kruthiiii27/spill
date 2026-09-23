import os
from functools import wraps
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, abort
from werkzeug.security import generate_password_hash, check_password_hash

from config import Config
from models import db, User, Category, Post, Comment, Reaction, Bookmark, Poll, PollOption, PollVote, Report, ModerationAction
from moderation.filters import analyze_content
from moderation.rules import evaluate_user_enforcement

def create_app():
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object(Config)

    # Ensure database folder exists
    os.makedirs(os.path.dirname(app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')), exist_ok=True)
    
    db.init_app(app)

    # -------------------------------------------------------------------------
    # AUTHENTICATION HELPERS & DECORATORS
    # -------------------------------------------------------------------------
    
    @app.before_request
    def load_logged_in_user():
        user_id = session.get('user_id')
        if user_id is None:
            request.current_user = None
        else:
            request.current_user = db.session.get(User, user_id)

    def login_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.current_user:
                flash("Please log in to continue.", "error")
                return redirect(url_for('login'))
            if request.current_user.is_banned:
                session.clear()
                flash("Your account has been permanently banned for severe violations.", "error")
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function

    def admin_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.current_user or not request.current_user.is_admin:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function

    @app.context_processor
    def inject_global_data():
        categories = Category.query.all() if db.session.query(Category).first() else []
        return dict(
            current_user=request.current_user,
            categories=categories
        )

    # -------------------------------------------------------------------------
    # PUBLIC & CORE ROUTES
    # -------------------------------------------------------------------------

    @app.route('/')
    def home():
        categories = Category.query.all()
        
        # Tea of the day (highest reactions or manually tagged)
        tea_of_the_day = Post.query.filter_by(is_hidden=False, is_deleted=False)\
            .order_by(Post.reaction_count.desc(), Post.created_at.desc()).first()
            
        recent_spills = Post.query.filter_by(is_hidden=False, is_deleted=False)\
            .order_by(Post.created_at.desc()).limit(10).all()
            
        trending_spills = sorted(
            Post.query.filter_by(is_hidden=False, is_deleted=False).limit(30).all(),
            key=lambda p: p.trending_score,
            reverse=True
        )[:5]

        poll = Poll.query.filter_by(is_active=True).first()
        user_voted_option_id = None
        if poll and request.current_user:
            vote = PollVote.query.filter_by(poll_id=poll.id, user_id=request.current_user.id).first()
            if vote:
                user_voted_option_id = vote.option_id

        return render_template(
            'index.html',
            view='home',
            categories=categories,
            tea_of_the_day=tea_of_the_day,
            recent_spills=recent_spills,
            trending_spills=trending_spills,
            poll=poll,
            user_voted_option_id=user_voted_option_id
        )

    @app.route('/explore')
    def explore():
        category_slug = request.args.get('category')
        page = request.args.get('page', 1, type=int)
        
        query = Post.query.filter_by(is_hidden=False, is_deleted=False)
        selected_category = None
        
        if category_slug:
            selected_category = Category.query.filter_by(slug=category_slug).first()
            if selected_category:
                query = query.filter_by(category_id=selected_category.id)
                
        posts = query.order_by(Post.created_at.desc()).paginate(page=page, per_page=15, error_out=False)
        
        return render_template(
            'index.html',
            view='explore',
            posts=posts,
            selected_category=selected_category
        )

    @app.route('/trending')
    def trending():
        all_posts = Post.query.filter_by(is_hidden=False, is_deleted=False).all()
        sorted_posts = sorted(all_posts, key=lambda p: p.trending_score, reverse=True)[:20]
        
        return render_template('index.html', view='trending', posts=sorted_posts)

    @app.route('/spill', methods=['GET', 'POST'])
    @login_required
    def spill():
        if request.current_user.status in ['SUSPENDED', 'BANNED']:
            flash("Your posting permissions are restricted due to community policy violations.", "error")
            return redirect(url_for('home'))

        if request.method == 'POST':
            category_id = request.form.get('category_id')
            content = request.form.get('content', '').strip()

            if not content or len(content) < 5:
                flash("Spill content must be at least 5 characters long.", "error")
                return redirect(url_for('spill'))

            # AUTOMATED SERVER-SIDE MODERATION EVALUATION
            analysis = analyze_content(content)
            
            if not analysis["is_safe"]:
                severity = analysis["severity"]
                enforcement_action = evaluate_user_enforcement(request.current_user, severity)
                
                # Record moderation log
                mod_action = ModerationAction(
                    user_id=request.current_user.id,
                    action_type=enforcement_action,
                    reason=" | ".join(analysis["reasons"]),
                    severity=severity
                )
                db.session.add(mod_action)
                db.session.commit()

                if severity == "SEVERE":
                    flash("⚠️ Severe Violation Detected: Content blocked. Your account status has been updated.", "error")
                    return redirect(url_for('home'))
                else:
                    flash(f"⚠️ Please keep SPILL respectful. {analysis['reasons'][0]} Remove improper terms to publish.", "warning")
                    return render_template('index.html', view='spill', draft_content=content, draft_category=category_id)

            # SAVE POST
            new_post = Post(
                user_id=request.current_user.id,
                category_id=category_id,
                content=content
            )
            db.session.add(new_post)
            db.session.commit()

            flash("✓ Spill posted anonymously!", "success")
            return redirect(url_for('explore'))

        return render_template('index.html', view='spill')

    @app.route('/my-spills')
    @login_required
    def my_spills():
        posts = Post.query.filter_by(user_id=request.current_user.id, is_deleted=False)\
            .order_by(Post.created_at.desc()).all()
        return render_template('index.html', view='my_spills', posts=posts)

    @app.route('/saved')
    @login_required
    def saved():
        bookmarks = Bookmark.query.filter_by(user_id=request.current_user.id)\
            .order_by(Bookmark.created_at.desc()).all()
        posts = [b.post for b in bookmarks if not b.post.is_hidden and not b.post.is_deleted]
        return render_template('index.html', view='saved', posts=posts)

    @app.route('/profile')
    @login_required
    def profile():
        spill_count = Post.query.filter_by(user_id=request.current_user.id, is_deleted=False).count()
        return render_template('index.html', view='profile', spill_count=spill_count)

    @app.route('/guidelines')
    def guidelines():
        return render_template('index.html', view='guidelines')

    @app.route('/about')
    def about():
        return render_template('index.html', view='about')

    @app.route('/search')
    def search():
        query_str = request.args.get('q', '').strip()
        posts = []
        if query_str:
            posts = Post.query.filter(
                Post.content.ilike(f"%{query_str}%"),
                Post.is_hidden == False,
                Post.is_deleted == False
            ).order_by(Post.created_at.desc()).all()
            
        return render_template('index.html', view='search', query=query_str, posts=posts)

    # -------------------------------------------------------------------------
    # POST ACTIONS & SERVER-SIDE AUTHORIZATION
    # -------------------------------------------------------------------------

    @app.route('/posts/<int:post_id>/delete', methods=['POST'])
    @login_required
    def delete_post(post_id):
        post = db.session.get(Post, post_id)
        if not post:
            flash("Post not found.", "error")
            return redirect(url_for('explore'))

        # SERVER-SIDE AUTHORIZATION CHECK
        if post.user_id != request.current_user.id and not request.current_user.is_admin:
            abort(403) # Forbidden

        post.is_deleted = True
        db.session.commit()
        flash("✓ Spill deleted successfully.", "success")
        return redirect(request.referrer or url_for('explore'))

    @app.route('/posts/<int:post_id>/react', methods=['POST'])
    @login_required
    def react_post(post_id):
        post = db.session.get(Post, post_id)
        if not post:
            return jsonify({'success': False, 'error': 'Post not found'}), 404

        reaction_type = request.json.get('reaction_type', 'heart')
        
        existing = Reaction.query.filter_by(
            user_id=request.current_user.id,
            post_id=post.id,
            reaction_type=reaction_type
        ).first()

        if existing:
            db.session.delete(existing)
            post.reaction_count = max(0, post.reaction_count - 1)
            action = 'removed'
        else:
            new_reaction = Reaction(
                user_id=request.current_user.id,
                post_id=post.id,
                reaction_type=reaction_type
            )
            db.session.add(new_reaction)
            post.reaction_count += 1
            action = 'added'

        db.session.commit()
        return jsonify({'success': True, 'action': action, 'count': post.reaction_count})

    @app.route('/posts/<int:post_id>/save', methods=['POST'])
    @login_required
    def toggle_save_post(post_id):
        post = db.session.get(Post, post_id)
        if not post:
            return jsonify({'success': False, 'error': 'Post not found'}), 404

        existing = Bookmark.query.filter_by(
            user_id=request.current_user.id,
            post_id=post.id
        ).first()

        if existing:
            db.session.delete(existing)
            saved_status = False
        else:
            bookmark = Bookmark(user_id=request.current_user.id, post_id=post.id)
            db.session.add(bookmark)
            saved_status = True

        db.session.commit()
        return jsonify({'success': True, 'saved': saved_status})

    @app.route('/posts/<int:post_id>/comments', methods=['GET', 'POST'])
    @login_required
    def comments(post_id):
        post = db.session.get(Post, post_id)
        if not post or post.is_deleted:
            flash("Post not found.", "error")
            return redirect(url_for('explore'))

        if request.method == 'POST':
            content = request.form.get('content', '').strip()
            if content:
                # MODERATION CHECK ON COMMENT
                analysis = analyze_content(content)
                if not analysis["is_safe"]:
                    flash(f"⚠️ Comment rejected: {analysis['reasons'][0]}", "error")
                    return redirect(url_for('comments', post_id=post.id))

                comment = Comment(
                    post_id=post.id,
                    user_id=request.current_user.id,
                    content=content
                )
                db.session.add(comment)
                post.comment_count += 1
                db.session.commit()
                flash("✓ Comment posted anonymously.", "success")

            return redirect(url_for('comments', post_id=post.id))

        post_comments = Comment.query.filter_by(post_id=post.id).order_by(Comment.created_at.asc()).all()
        return render_template('index.html', view='comments', post=post, comments=post_comments)

    @app.route('/comments/<int:comment_id>/delete', methods=['POST'])
    @login_required
    def delete_comment(comment_id):
        comment = db.session.get(Comment, comment_id)
        if not comment:
            flash("Comment not found.", "error")
            return redirect(url_for('explore'))

        if comment.user_id != request.current_user.id and not request.current_user.is_admin:
            abort(403)

        post = comment.post
        db.session.delete(comment)
        if post:
            post.comment_count = max(0, post.comment_count - 1)
        db.session.commit()
        
        flash("✓ Comment deleted.", "success")
        return redirect(request.referrer or url_for('explore'))

    @app.route('/posts/<int:post_id>/report', methods=['POST'])
    @login_required
    def report_post(post_id):
        reason = request.form.get('reason', 'Inappropriate content')
        existing = Report.query.filter_by(user_id=request.current_user.id, post_id=post_id).first()
        
        if not existing:
            report = Report(user_id=request.current_user.id, post_id=post_id, reason=reason)
            db.session.add(report)
            db.session.commit()
            flash("✓ Report submitted to moderators. Thank you for keeping SPILL safe.", "success")
        else:
            flash("You have already reported this spill.", "info")

        return redirect(request.referrer or url_for('explore'))

    @app.route('/polls/<int:poll_id>/vote', methods=['POST'])
    @login_required
    def vote_poll(poll_id):
        option_id = request.form.get('option_id', type=int)
        
        existing_vote = PollVote.query.filter_by(poll_id=poll_id, user_id=request.current_user.id).first()
        if existing_vote:
            flash("You have already voted in this poll.", "warning")
            return redirect(request.referrer or url_for('home'))

        option = db.session.get(PollOption, option_id)
        if option and option.poll_id == poll_id:
            vote = PollVote(poll_id=poll_id, option_id=option.id, user_id=request.current_user.id)
            option.votes_count += 1
            db.session.add(vote)
            db.session.commit()
            flash("✓ Vote recorded!", "success")

        return redirect(request.referrer or url_for('home'))

    # -------------------------------------------------------------------------
    # AUTHENTICATION ROUTES
    # -------------------------------------------------------------------------

    @app.route('/auth/register', methods=['GET', 'POST'])
    def register():
        if request.current_user:
            return redirect(url_for('home'))

        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')
            email = request.form.get('email', '').strip() or None

            if not username or len(username) < 3:
                flash("Username must be at least 3 characters.", "error")
                return redirect(url_for('register'))

            if password != confirm_password:
                flash("Passwords do not match.", "error")
                return redirect(url_for('register'))

            if len(password) < 6:
                flash("Password must be at least 6 characters.", "error")
                return redirect(url_for('register'))

            if User.query.filter_by(username=username).first():
                flash("Username is already taken.", "error")
                return redirect(url_for('register'))

            hashed_pw = generate_password_hash(password)
            user = User(username=username, email=email, password_hash=hashed_pw)
            db.session.add(user)
            db.session.commit()

            session['user_id'] = user.id
            flash("Welcome to SPILL! Your account was created successfully.", "success")
            return redirect(url_for('home'))

        return render_template('index.html', view='auth_register')

    @app.route('/auth/login', methods=['GET', 'POST'])
    def login():
        if request.current_user:
            return redirect(url_for('home'))

        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')

            user = User.query.filter_by(username=username).first()
            if user and check_password_hash(user.password_hash, password):
                if user.is_banned:
                    flash("Account is permanently banned due to severe violations.", "error")
                    return redirect(url_for('login'))

                user.last_login = datetime.utcnow()
                db.session.commit()

                session['user_id'] = user.id
                flash("Successfully logged in.", "success")
                return redirect(url_for('home'))

            flash("Invalid credentials.", "error")
            return redirect(url_for('login'))

        return render_template('index.html', view='auth_login')

    @app.route('/auth/logout')
    def logout():
        session.clear()
        flash("You have been logged out safely.", "success")
        return redirect(url_for('home'))

    # -------------------------------------------------------------------------
    # ADMINISTRATIVE CONTROL DASHBOARD
    # -------------------------------------------------------------------------

    @app.route('/admin')
    @admin_required
    def admin_dashboard():
        total_users = User.query.count()
        total_posts = Post.query.filter_by(is_deleted=False).count()
        total_reports = Report.query.filter_by(status='PENDING').count()
        total_comments = Comment.query.count()

        pending_reports = Report.query.filter_by(status='PENDING').order_by(Report.created_at.desc()).all()
        recent_mod_actions = ModerationAction.query.order_by(ModerationAction.created_at.desc()).limit(10).all()
        users = User.query.order_by(User.created_at.desc()).limit(20).all()

        return render_template(
            'index.html',
            view='admin',
            total_users=total_users,
            total_posts=total_posts,
            total_reports=total_reports,
            total_comments=total_comments,
            reports=pending_reports,
            mod_actions=recent_mod_actions,
            users=users
        )

    @app.route('/admin/reports/<int:report_id>/action', methods=['POST'])
    @admin_required
    def admin_report_action(report_id):
        action = request.form.get('action') # dismiss, delete_post, suspend_user
        report = db.session.get(Report, report_id)
        if not report:
            flash("Report not found.", "error")
            return redirect(url_for('admin_dashboard'))

        if action == 'dismiss':
            report.status = 'DISMISSED'
        elif action == 'delete_post':
            report.status = 'REVIEWED'
            report.post.is_hidden = True
            report.post.is_deleted = True
        elif action == 'suspend_user':
            report.status = 'REVIEWED'
            report.post.is_hidden = True
            user = report.post.author
            user.is_suspended = True
            user.status = 'SUSPENDED'

        db.session.commit()
        flash("✓ Admin action performed.", "success")
        return redirect(url_for('admin_dashboard'))

    @app.route('/admin/users/<int:user_id>/status', methods=['POST'])
    @admin_required
    def admin_user_status(user_id):
        new_status = request.form.get('status') # ACTIVE, SUSPENDED, BANNED
        user = db.session.get(User, user_id)
        if user:
            user.status = new_status
            user.is_suspended = (new_status == 'SUSPENDED')
            user.is_banned = (new_status == 'BANNED')
            db.session.commit()
            flash(f"User {user.username} status updated to {new_status}.", "success")

        return redirect(url_for('admin_dashboard'))

    # -------------------------------------------------------------------------
    # ERROR HANDLERS
    # -------------------------------------------------------------------------

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('index.html', view='error', error_code=404, message="Something spilled over. Page not found."), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('index.html', view='error', error_code=403, message="You don't have permission to do that."), 403

    @app.errorhandler(500)
    def internal_error(e):
        return render_template('index.html', view='error', error_code=500, message="Something went wrong behind the counter."), 500

    return app

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)