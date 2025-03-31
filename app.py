from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user, login_required, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)

# 🔹 Database Configuration (SQLite)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'recruitment.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key'  # Required for sessions

db = SQLAlchemy(app)

# 🔹 Initialize Flask-Login
login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)


# 🔹 Models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # "recruiter" or "applicant" or "admin"


class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(100), nullable=False)
    date_posted = db.Column(db.DateTime, default=db.func.current_timestamp())
    recruiter_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Track who posted

    recruiter = db.relationship('User', backref='jobs')  # Relationship with User model



class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False)
    resume = db.Column(db.String(300), nullable=False)
    status = db.Column(db.String(50), default="Pending")


# 🔹 Flask-Login User Loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# 🔹 Routes
@app.route('/')
def index():
    jobs = Job.query.all()
    return render_template('index.html', jobs=jobs)


@app.route('/job/<int:job_id>')
def job_detail(job_id):
    job = Job.query.get_or_404(job_id)
    return render_template('job_detail.html', job=job)


@app.route('/apply/<int:job_id>', methods=['POST'])
@login_required
def apply(job_id):
    if 'resume' not in request.files:
        flash("No file uploaded!", "danger")
        return redirect(url_for('job_detail', job_id=job_id))

    file = request.files['resume']
    if file.filename == '':
        flash("No selected file!", "danger")
        return redirect(url_for('job_detail', job_id=job_id))

    upload_folder = os.path.join(BASE_DIR, 'uploads')
    os.makedirs(upload_folder, exist_ok=True)  # Ensure uploads folder exists

    filename = os.path.join(upload_folder, file.filename)
    file.save(filename)

    application = Application(user_id=current_user.id, job_id=job_id, resume=filename)
    db.session.add(application)
    db.session.commit()

    flash("Application submitted successfully!", "success")
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Debugging: Print form data
        print(request.form)

        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')

        if not username or not email or not password or not role:
            flash("All fields are required!", "danger")
            return redirect(url_for('register'))

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email already registered! Please log in.", "warning")
            return redirect(url_for('login'))

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, email=email, password=hashed_password, role=role)

        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful! Please log in.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')




@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash("Login successful!", "success")

            # Redirect based on role
            return redirect(url_for('recruiter_dashboard' if user.role == "recruiter" else 'applicant_dashboard'))
        else:
            flash("Invalid credentials, try again.", "danger")

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logged out successfully!", "success")
    return redirect(url_for('index'))


@app.route('/recruiter_dashboard')
@login_required
def recruiter_dashboard():
    if current_user.role != "recruiter":
        flash("Access denied!", "danger")
        return redirect(url_for('index'))

    jobs = Job.query.all()
    return render_template('recruiter_dashboard.html', jobs=jobs)


@app.route('/applicant_dashboard')
@login_required
def applicant_dashboard():
    if current_user.role != "applicant":
        flash("Access denied!", "danger")
        return redirect(url_for('index'))

    jobs = Job.query.all()
    return render_template('applicant_dashboard.html', jobs=jobs)


@app.route('/post_job', methods=['GET', 'POST'])
@login_required
def post_job():
    if current_user.role != "recruiter":
        flash("Unauthorized action!", "danger")
        return redirect(url_for('index'))

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        location = request.form.get('location')

        if not title or not description or not location:
            flash("All fields are required!", "danger")
            return redirect(url_for('post_job'))

        new_job = Job(title=title, description=description, location=location, recruiter_id=current_user.id)
        db.session.add(new_job)
        db.session.commit()

        flash("Job posted successfully!", "success")
        return redirect(url_for('recruiter_dashboard'))

    return render_template('post_job.html')



@app.route('/delete_job/<int:job_id>')
@login_required
def delete_job(job_id):
    job = Job.query.get_or_404(job_id)

    # Only allow the recruiter who posted the job to delete it
    if current_user.role != "recruiter" or job.recruiter_id != current_user.id:
        flash("Unauthorized action! You can only delete your own jobs.", "danger")
        return redirect(url_for('recruiter_dashboard'))

    db.session.delete(job)
    db.session.commit()
    flash("Job deleted successfully!", "success")
    return redirect(url_for('recruiter_dashboard'))



# 🔹 Run Flask App
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Ensure tables exist
    app.run(debug=True)
