from datetime import datetime, timezone
from urllib.parse import urlsplit
from flask import render_template, flash, redirect, url_for, request
from flask_login import login_user, logout_user, current_user, login_required
import sqlalchemy as sa
from app import app, db, oauth
from app.forms import LoginForm, PostForm, RegistrationForm, EditProfileForm, EmptyForm, ChangePasswordForm, SetPasswordForm
from app.models import Post, User

@app.route('/update_password', methods=['GET', 'POST'])
@login_required
def update_password():
    # A clean way to set the boolean!
    isgoogle = current_user.password_hash is None

    # Hand them the correct form
    if isgoogle:
        form = SetPasswordForm()
    else:
        form = ChangePasswordForm()

    if form.validate_on_submit():
        # Only check the old password if they actually have one
        if not isgoogle:
            if not current_user.check_password(form.old_password.data):
                flash('Invalid old password.')
                return redirect(url_for('change_password'))

        # If they pass the check (or skipped it because of Google), set the new password
        current_user.set_password(form.new_password.data)
        db.session.commit()
        
        flash('Your password has been successfully updated!')
        return redirect(url_for('user', username=current_user.username))

    # We pass 'isgoogle' to the template so it knows how to render the page
    return render_template('update_password.html', title='Password Settings', form=form, isgoogle=isgoogle)
@app.route('/login/google')
def login_google():
    # If they are already logged in, don't let them log in again
    if current_user.is_authenticated:
        flash('You are already logged in.')
        return redirect(url_for('index'))
    
    # Send them to the Google login screen
    redirect_uri = url_for('authorize_google', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@app.route('/authorize/google')
def authorize_google():
    # Google sends them back here with a digital token
    token = oauth.google.authorize_access_token()
    
    # We use the token to ask Google for their email and name
    user_info = token.get('userinfo')
    if not user_info:
        flash('Google login failed.')
        return redirect(url_for('login'))
        
    email = user_info['email']
    
    # Check if this user already exists in our database
    user = db.session.scalar(sa.select(User).where(User.email == email))
    
    if user is None:
        # If they don't exist, create a brand new account for them instantly!
        # We use their Google name, or the first part of their email if name is missing
        username = user_info.get('name') or email.split('@')[0]
        user = User(username=username, email=email)
        
        # We don't set a password_hash because they use Google to log in!
        db.session.add(user)
        db.session.commit()
        
    # Log them in and send them to the homepage
    login_user(user)
    return redirect(url_for('index'))


@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.now(timezone.utc)
        db.session.commit()


@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(body=form.post.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Your post is now live!')
        return redirect(url_for('index'))
    posts = db.session.scalars(current_user.following_posts()).all()
    return render_template("index.html", title='Home Page', form=form,
                           posts=posts)

@app.route('/explore')
@login_required
def explore():
    query = sa.select(Post).order_by(Post.timestamp.desc())
    posts = db.session.scalars(query).all()
    return render_template('index.html', title='Explore', posts=posts)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username == form.username.data))
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or urlsplit(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route('/user/<username>')
@login_required
def user(username):
    user = db.first_or_404(sa.select(User).where(User.username == username))
    query = sa.select(Post).order_by(Post.timestamp.desc()).where(Post.user_id == user.id)
    posts = db.session.scalars(query).all()
    form = EmptyForm()
    return render_template('user.html', user=user, posts=posts, form=form)


@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title='Edit Profile',
                           form=form)


@app.route('/follow/<username>', methods=['POST'])
@login_required
def follow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username == username))
        if user is None:
            flash(f'User {username} not found.')
            return redirect(url_for('index'))
        if user == current_user:
            flash('You cannot follow yourself!')
            return redirect(url_for('user', username=username))
        current_user.follow(user)
        db.session.commit()
        flash(f'You are following {username}!')
        return redirect(url_for('user', username=username))
    else:
        return redirect(url_for('index'))


@app.route('/unfollow/<username>', methods=['POST'])
@login_required
def unfollow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username == username))
        if user is None:
            flash(f'User {username} not found.')
            return redirect(url_for('index'))
        if user == current_user:
            flash('You cannot unfollow yourself!')
            return redirect(url_for('user', username=username))
        current_user.unfollow(user)
        db.session.commit()
        flash(f'You are not following {username}.')
        return redirect(url_for('user', username=username))
    else:
        return redirect(url_for('index'))