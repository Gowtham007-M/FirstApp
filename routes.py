# routes.py
from flask import Flask, render_template, request, redirect, url_for, flash
from models import db, User, Job, Application
from flask_login import login_user, logout_user, login_required

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///recruitment.db'
app.config['SECRET_KEY'] = 'supersecretkey'
db.init_app(app)


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
    file = request.files['resume']
    filename = f"uploads/{file.filename}"
    file.save(filename)

    application = Application(user_id=current_user.id, job_id=job_id, resume=filename)
    db.session.add(application)
    db.session.commit()
    flash("Application submitted successfully!", "success")
    return redirect(url_for('index'))





if __name__ == '__main__':
    app.run(debug=True)
