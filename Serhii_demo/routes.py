from PIL import Image
from flask import request, render_template, send_file, flash, redirect,\
    url_for
from Serhii_demo import app, db, bcrypt
from Serhii_demo.models import User
from Serhii_demo.form import RegistrationForm, LoginForm, UpdateAccountForm
from flask_login import login_user, current_user, logout_user, login_required
import glob
import json
import os
import secrets


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/upload')
def upload():
    return render_template('upload.html')


@app.route('/uploadFile', methods=['POST'])
def uploadFile():
    filepath = app.root_path + f'\\storage\\{current_user.username}\\'\
        if current_user.is_authenticated else\
        app.root_path + '\\storage\\'
    filelist = [x.replace(filepath, '')
                for x in
                glob.glob(filepath + '*.json')]
    if request.method == 'POST':
        f = request.files['inputFile']
        if f.filename in filelist:
            flash('File with such name already exists in storage.', 'warning')
        else:
            upd_filepath = filepath + str(f.filename)
            data = f.read()
            try:
                json.loads(data.decode('utf-8'))
                assert f.filename.rsplit('.', 1)[1].lower() == 'json'
                with open(upd_filepath, 'w') as destFile:
                    destFile.write(data.decode('utf-8'))
                    flash('Your file was uploaded to storage!', 'success')
            except AssertionError:
                flash('File was not uploaded. Only files with JSON extension \
                    are allowed.', 'warning')
            except Exception:
                flash('File was not uploaded. File must contain valid JSON \
                    data', 'warning')

        return redirect(url_for('upload'))


@app.route('/filelist')
def filelist():
    filepath = app.root_path + f'\\storage\\{current_user.username}\\'\
        if current_user.is_authenticated else \
        app.root_path + '\\storage\\'
    filelist = [x.replace(filepath, '')
                for x in
                glob.glob(filepath + '*.json')]
    image_file = url_for('static', filename='profile_pictures/'
                         + current_user.image_file)\
        if current_user.is_authenticated else \
        url_for('static', filename='profile_pictures/default.jpg')
    return render_template('filelist.html', files=filelist,
                           image_file=image_file)


@app.route('/downloads/<path:filename>')
def download_file(filename):
    if current_user.is_authenticated:
        return send_file(f'storage\\{current_user.username}\\'+str(filename),
                         as_attachment=True,
                         cache_timeout=0)
    else:
        return send_file('storage\\'+str(filename), as_attachment=True,
                         cache_timeout=0)


@app.route('/update/<path:filename>')
def update(filename):
    try:
        with open(app.root_path + f'\\storage\\{filename}', 'r') as src_file:
            data = src_file.read()
    except Exception:
        data = ''
    return render_template('update.html', filename=filename, data=data)


@app.route('/updateFile/<path:filename>', methods=['POST'])
def updateFile(filename):
    filepath = app.root_path + f'\\storage\\{current_user.username}\\'\
        if current_user.is_authenticated else\
        app.root_path + '\\storage\\'
    filelist = [x.replace(filepath, '')
                for x in
                glob.glob(filepath + '*.json')]
    if filename in filelist:
        data = request.form['text']
        try:
            upd_filepath = \
                    filepath + filename
            json.loads(data)
            with open(upd_filepath, 'w') as destFile:
                destFile.write(data)
                flash('File was successfully updated.', 'success')
        except Exception:
            flash('File was not updated. Only valid json data is accepted.',
                  'warning')
        finally:
            return redirect(url_for('filelist'))


@app.route('/delete/<path:filename>')
def delete_file(filename):
    os.remove(app.root_path + f'\\storage\\{filename}')
    flash('File was removed.', 'success')
    return redirect(url_for('filelist'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and bcrypt.check_password_hash(user.password,
                                               form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else \
                redirect(url_for('home'))
        else:
            flash('Login Unsuccessfull. Please check username and password.',
                  'danger')
    return render_template('login.html', form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data)\
            .decode('utf-8')
        user = User(username=form.username.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        os.mkdir(f'Serhii_demo/storage/{form.username.data}')
        flash(f'Your account has been created! You are now able to login.',
              'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)


@app.route('/logout', methods=['GET', 'POST'])
def logout():
    logout_user()
    return redirect(url_for('home'))


def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pictures',
                                picture_fn)
    output_size = (100, 100)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn


@app.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        os.rename(f'Serhii_demo/storage/{current_user.username}',
                  f'Serhii_demo/storage/{form.username.data}')
        current_user.username = form.username.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
    imageFile = url_for('static', filename='profile_pictures/' +
                        current_user.image_file)
    return render_template('account.html', image_file=imageFile, form=form)


@app.after_request
def add_header(response):
    # response.cache_control.no_store = True
    response.headers['Cache-Control'] = 'no-store, no-cache, must-\
    revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response
