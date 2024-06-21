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

from models import Completion, Course, Enrollment, Lesson, User
from forms import CourseForm, LessonForm, SignInForm, SignUpForm

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

def completion_lesson_status(course_id):
    if current_user.is_authenticated:
        lessons = Lesson.query.filter_by(course_id=course_id).all()
        completions = {}
        for lesson in lessons:
            completion = Completion.query.filter_by(user_id=current_user.id, lesson_id=lesson.id).first()
            completions[lesson.id] = (completion is not None)
        return completions
    return {}

@app.route('/courses/<course_id>')
def course_detail(course_id):
    course = Course.query.get_or_404(course_id)
    completions = completion_lesson_status(course_id)
    lessons = Lesson.query.filter_by(course_id=course_id).all()
    if current_user.is_authenticated:
        enrollment = Enrollment.query.filter_by(user_id=current_user.id, course_id=course.id).first()    
        return render_template('course/detail.html', course=course, lessons=lessons, enrollment=enrollment, completions=completions)
    return render_template('course/detail.html', course=course, lessons=lessons, completions=completions)

@app.route('/courses/new', methods=['GET', 'POST'])
@login_required
def course_new():
    form = CourseForm()
    if form.validate_on_submit():
        course = Course(title=form.title.data, description=form.description.data, image_url=form.image_url.data, user_id=current_user.id)
        db.session.add(course)
        db.session.commit()
        flash('Course created!', 'success')
        return redirect(url_for('course_list'))
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
        course.image_url = form.image_url.data
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


@app.route('/course/<course_id>/enroll', methods=['POST'])
@login_required
def enroll(course_id):
    course = Course.query.get_or_404(course_id)
    if Enrollment.query.filter_by(user_id=current_user.id, course_id=course.id).first():
        flash('You are already enrolled in this course.', 'warning')
        return redirect(url_for('course_detail', course_id=course_id))
    enrollment = Enrollment(user_id=current_user.id, course_id=course_id)
    db.session.add(enrollment)
    db.session.commit()
    flash('Enrolled in course!', 'success')
    return redirect(url_for('course_detail', course_id=course_id))

@app.route('/course/<course_id>/unenroll', methods=['POST'])
@login_required
def unenroll(course_id):
    course = Course.query.get_or_404(course_id)
    enrollment = Enrollment.query.filter_by(user_id=current_user.id, course_id=course.id).first()
    if not enrollment:
        flash('You are not enrolled in this course.', 'warning')
        return redirect(url_for('course_detail', course_id=course_id))
    db.session.delete(enrollment)
    db.session.commit()
    flash('Unenrolled from course!', 'success')
    return redirect(url_for('course_detail', course_id=course_id))

@app.route('/course/<course_id>/complete', methods=['POST'])
@login_required
def complete_course(course_id):
    course = Course.query.get_or_404(course_id)
    enrollment = Enrollment.query.filter_by(user_id=current_user.id, course_id=course.id).first()
    if not enrollment:
        flash('You need to enroll in the course first.', 'warning')
        return redirect(url_for('course_detail', course_id=course.id))
    enrollment.completed = True
    db.session.commit()
    flash('Course marked as completed!', 'success')
    return redirect(url_for('course_detail', course_id=course.id))

@app.route('/course/<course_id>/lesson/new', methods=['GET', 'POST'])
@login_required
def lesson_new(course_id):
    form = LessonForm()
    if form.validate_on_submit():
        order = Lesson.query.filter_by(course_id=course_id).count() + 1
        lesson = Lesson(title=form.title.data, description=form.description.data, video_link=form.video_link.data, course_id=course_id, order=order)
        db.session.add(lesson)
        db.session.commit()
        flash('Lesson added!', 'success')
        return redirect(url_for('course_detail', course_id=course_id))
    return render_template('lesson/form.html', form=form)

@app.route('/lesson/<lesson_id>')
def lesson_detail(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    course = Course.query.get_or_404(lesson.course_id)
    next_lesson = Lesson.query.filter_by(course_id=course.id).filter(Lesson.order > lesson.order).first()
    if not current_user.is_authenticated:
        return render_template('lesson/detail.html', lesson=lesson, course=course, next_lesson=next_lesson)
    if course.user_id != current_user.id and not Enrollment.query.filter_by(user_id=current_user.id, course_id=course.id).first():
        flash('You do not have access to this lesson.', 'danger')
        return redirect(url_for('course_detail', course_id=course.id))
    completion = Completion.query.filter_by(user_id=current_user.id, lesson_id=lesson.id).first()    
    return render_template('lesson/detail.html', lesson=lesson, course=course, completion=completion, next_lesson=next_lesson)

@app.route('/lesson/<lesson_id>/edit', methods=['GET', 'POST'])
@login_required
def lesson_edit(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    course = Course.query.get_or_404(lesson.course_id)
    if course.user_id != current_user.id:
        flash('You do not have access to this lesson.', 'danger')
        return redirect(url_for('course_detail', course_id=course.id))
    form = LessonForm()
    if form.validate_on_submit():
        lesson.title = form.title.data
        lesson.description = form.description.data
        lesson.video_link = form.video_link.data
        db.session.commit()
        flash('Lesson updated!', 'success')
        return redirect(url_for('course_detail', course_id=lesson.course_id))
    elif request.method == 'GET':
        form.title.data = lesson.title
        form.description.data = lesson.description
        form.video_link.data = lesson.video_link
    return render_template('lesson/form.html', form=form)

@app.route('/lesson/<lesson_id>/delete', methods=['POST'])
@login_required
def lesson_delete(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    course = Course.query.get_or_404(lesson.course_id)
    if course.user_id != current_user.id:
        flash('You do not have access to this lesson.', 'danger')
        return redirect(url_for('course_detail', course_id=course.id))
    db.session.delete(lesson)
    db.session.commit()
    flash('Lesson deleted!', 'success')
    return redirect(url_for('course_detail', course_id=lesson.course_id))

@app.route('/lesson/<lesson_id>/complete', methods=['POST'])
@login_required
def lesson_complete(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    completion = Completion.query.filter_by(user_id=current_user.id, lesson_id=lesson.id).first()

    if completion:
        db.session.delete(completion)
        db.session.commit()
        flash('Lesson marked as incomplete!', 'info')
    else:
        completion = Completion(user_id=current_user.id, lesson_id=lesson.id, completed=True)
        db.session.add(completion)
        db.session.commit()
        flash('Lesson marked as completed!', 'success')

    return redirect(url_for('lesson_detail', lesson_id=lesson.id))

if __name__ == '__main__':
    app.run(debug=True)
