from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'sign_in'
bcrypt = Bcrypt(app)

from models import Course, User
from forms import CourseForm, SignInForm, SignUpForm

with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

@app.route('/')
def index():
    courses = Course.query.limit(5).all()
    return render_template('index.html', courses=courses)

@app.route('/sign-in', methods=['GET', 'POST'])
def sign_in():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = SignInForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Sign In Unsuccessful. Please check username and password', 'danger')
    return render_template('user/sign_in.html', form=form)

@app.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = SignUpForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(name=form.name.data, username=form.username.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created!', 'success')
        return redirect(url_for('sign_in'))
    return render_template('user/sign_up.html', form=form)

@app.route('/sign-out')
@login_required
def sign_out():
    logout_user()
    return redirect(url_for('index'))

@app.route('/courses')
def course_list():
    courses = Course.query.all()
    return render_template('course/list.html', courses=courses)

@app.route('/courses/<course_id>')
def course_detail(course_id):
    course = Course.query.get_or_404(course_id)
    return render_template('course/detail.html', course=course)

@app.route('/courses/new', methods=['GET', 'POST'])
@login_required
def course_new():
    form = CourseForm()
    if form.validate_on_submit():
        course = Course(title=form.title.data, description=form.description.data, image_url=form.image_url.data, user_id=current_user.id)
        db.session.add(course)
        db.session.commit()
        flash('Course created!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('course/form.html', form=form)

@app.route('/courses/<course_id>/edit', methods=['GET', 'POST'])
@login_required
def course_edit(course_id):
    course = Course.query.get_or_404(course_id)
    if course.user_id != current_user.id:
        flash('You do not have access to this course.', 'danger')
        return redirect(url_for('dashboard'))
    form = CourseForm()
    if form.validate_on_submit():
        course.title = form.title.data
        course.description = form.description.data
        db.session.commit()
        flash('Course updated!', 'success')
        return redirect(url_for('course_detail', course_id=course.id))
    elif request.method == 'GET':
        form.title.data = course.title
        form.description.data = course.description
        form.image_url.data = course.image_url
    return render_template('course/form.html', form=form)

@app.route('/courses/<course_id>/delete', methods=['POST'])
@login_required
def course_delete(course_id):
    course = Course.query.get_or_404(course_id)
    if course.user_id != current_user.id:
        flash('You do not have access to this course.', 'danger')
        return redirect(url_for('dashboard'))
    db.session.delete(course)
    db.session.commit()
    flash('Course deleted!', 'success')
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True)
