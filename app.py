# -*- coding: utf-8 -*-
import os
import ConfigParser
import erppeek
import bz2
import socket
from functools import wraps

from flask_bootstrap import Bootstrap
from flask import (
    Flask, render_template, request, abort,
    session, redirect, url_for, flash)
from flask.ext.babel import Babel, gettext as _
from form import LoginForm

def get_config():
    '''Get values from cfg file'''
    conf_file = '%s/config.ini' % os.path.dirname(os.path.realpath(__file__))
    config = ConfigParser.ConfigParser()
    config.read(conf_file)

    results = {}
    for section in config.sections():
        results[section] = {}
        for option in config.options(section):
            results[section][option] = config.get(section, option)
    return results

def create_app(config=None):
    '''Create Flask APP'''
    cfg = get_config()
    app_name = cfg['flask']['app_name']
    app = Flask(app_name)
    Bootstrap(app)
    app.config.from_pyfile(config)
    return app

def parse_setup(filename):
    globalsdict = {}  # put predefined things here
    localsdict = {}  # will be populated by executed script
    execfile(filename, globalsdict, localsdict)
    return localsdict

def get_lang():
    return app.config.get('LANGUAGE')

def erp_connect():
    '''OpenERP Connection'''
    server = app.config.get('OPENERP_SERVER')
    database = app.config.get('OPENERP_DATABASE')
    username = session['username']
    password = bz2.decompress(session['password'])
    try:
        Client = erppeek.Client(server, db=database, user=username,
                                password=password)
    except socket.error:
        flash(_("Can't connect to ERP server. Check network-ports"
                "or ERP server was running."))
        abort(500)
    except:
        abort(500)
    return Client

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        logged = session.get('logged_in', None)
        if not logged:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

conf_file = '%s/config.cfg' % os.path.dirname(os.path.realpath(__file__))
app = create_app(conf_file)
app.config['BABEL_DEFAULT_LOCALE'] = get_lang()
app.root_path = os.path.dirname(os.path.abspath(__file__))
babel = Babel(app)

@app.route("/login", methods=["GET", "POST"])
def login():
    '''Login'''
    form = LoginForm()
    data = {}
    if form.validate_on_submit():
        username = request.form.get('username')
        password = bz2.compress(request.form.get('password'))
        session['username'] = username
        session['password'] = password

        Client = erp_connect()
        login = Client.login(username, bz2.decompress(password),
                             app.config.get('OPENERP_DATABASE'))
        if login:
            session['logged_in'] = True
            flash(_('You were logged in.'))
            return redirect(url_for('index'))
        else:
            flash(_('Error: Invalid username %s or password'
                    % session.get('username')))
        data['username'] = username

    return render_template('login.html', form=form, data=data)

@app.route('/logout')
@login_required
def logout():
    '''Logout App'''
    # Remove all sessions
    session.pop('logged_in', None)

    session.pop('username', None)
    session.pop('password', None)

    flash(_('You were logged out.'))
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
