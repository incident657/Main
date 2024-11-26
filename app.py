from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
import folium
from geopy.geocoders import Nominatim
import os

app = Flask(__name__)

# Use environment variables for sensitive data
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'default_secret_key')  # Use a default fallback
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL','postgresql://postgresql:TCjOefc5xHMA250NB56XdsEtJf4sPNST@dpg-ct2ijodsvqrc738bhri0-a/mydatabase_8ho8') 
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['GOOGLE_MAPS_API_KEY'] = os.getenv('GOOGLE_MAPS_API_KEY')

# Initialize SQLAlchemy and Migrate
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Database model for reports
class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    location = db.Column(db.String(100))
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.Text)
    anonymous = db.Column(db.Boolean)
    username = db.Column(db.String(50))
    incident_type = db.Column(db.String(50))
    severity_type = db.Column(db.String(50))
    urgency_type = db.Column(db.String(50))
    status = db.Column(db.String(50), default='pending')

    def __repr__(self):
        return f"<Report {self.title}>"

# Initialize the database
with app.app_context():
    db.create_all()

# Geocoding function
def geocode_location(location_name):
    geolocator = Nominatim(user_agent="incident_reporting")
    try:
        location = geolocator.geocode(location_name)
        if location:
            return location.latitude, location.longitude
        return None, None
    except Exception as e:
        print(f"Error during geocoding: {e}")
        return None, None

# Routes
@app.route('/')
def login():
    return render_template('login.html')

@app.route('/authenticate_user', methods=['POST'])
def authenticate_user():
    username = request.form['username']
    password = request.form['password']
    role = request.form['role']

    if role == 'admin':
        if username == 'Emily Joy Flores' and password == 'adminpass':
            session['role'] = 'admin'
            session['username'] = username
            return redirect('/admin_reports')
        flash('Invalid admin credentials. Please try again.', 'error')
        return redirect('/')
    elif role == 'resident':
        session['role'] = 'resident'
        session['username'] = username
        return redirect('/resident_report')
    flash('Please select a valid role.', 'error')
    return redirect('/')

@app.route('/resident_report')
def resident_report():
    if session.get('role') != 'resident':
        return redirect('/')
    return render_template('resident_report.html')

@app.route('/submit_report', methods=['POST'])
def submit_report():
    report_title = request.form['report_title']
    report_location = request.form['report_location']
    latitude = request.form.get('latitude')
    longitude = request.form.get('longitude')
    report_date = request.form['report_date']
    report_description = request.form['report_description']
    anonymous = request.form.get('anonymous') == 'on'
    incident_type = request.form['incident_type']
    severity_type = request.form['severity_type']
    urgency_type = request.form['urgency_type']
    username = session.get('username') if not anonymous else None

    try:
        timestamp = datetime.strptime(report_date, '%Y-%m-%dT%H:%M')
    except ValueError:
        timestamp = None

    if not latitude or not longitude:
        latitude, longitude = geocode_location(report_location)
    if latitude is None or longitude is None:
        latitude = 14.5995  # Default to Manila
        longitude = 120.9842

    new_report = Report(
        title=report_title,
        location=report_location,
        latitude=float(latitude) if latitude else None,
        longitude=float(longitude) if longitude else None,
        timestamp=timestamp,
        description=report_description,
        anonymous=anonymous,
        username=username,
        incident_type=incident_type,
        severity_type=severity_type,
        urgency_type=urgency_type,
    )
    db.session.add(new_report)
    db.session.commit()
    return redirect('/thank_you')

@app.route('/thank_you')
def thank_you():
    return render_template('thank_you.html')

@app.route('/admin_reports')
def admin_reports():
    if session.get('role') != 'admin':
        return redirect('/')
    reports = Report.query.all()
    for report in reports:
        if report.timestamp:
            report.date = report.timestamp.strftime('%Y-%m-%d')
            report.time = report.timestamp.strftime('%H:%M')
    warning_sign = any(
        report.severity_type == 'critical' and report.urgency_type == 'immediate'
        for report in reports
    )
    map = folium.Map(location=[14.5995, 120.9842], zoom_start=12)
    for report in reports:
        if report.latitude and report.longitude:
            folium.Marker(location=[report.latitude, report.longitude], popup=report.title).add_to(map)
    map.save('templates/map.html')
    return render_template('admin_reports.html', reports=reports, warning_sign=warning_sign)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/delete_report/<int:id>', methods=['POST'])
def delete_report(id):
    report = Report.query.get(id)
    if report:
        db.session.delete(report)
        db.session.commit()
        flash("Report deleted successfully!", 'success')
    else:
        flash("Report not found!", 'error')
    return redirect('/admin_reports')

@app.route('/search_reports')
def search_reports():
    search_query = request.args.get('search')
    reports = Report.query.filter(
        Report.title.ilike(f'%{search_query}%') |
        Report.location.ilike(f'%{search_query}%') |
        Report.username.ilike(f'%{search_query}%') |
        Report.incident_type.ilike(f'%{search_query}%')
    ).all() if search_query else Report.query.all()
    return render_template('admin_reports.html', reports=reports)

@app.route('/mark_as_done/<int:id>', methods=['POST'])
def mark_as_done(id):
    report = Report.query.get_or_404(id)
    report.status = 'done'
    db.session.commit()
    return redirect(url_for('admin_reports'))

@app.route('/update_incident_type/<int:id>', methods=['POST'])
def update_incident_type(id):
    custom_incident = request.form.get('custom_incident')
    if custom_incident:
        # Update the report in the database
        report = Report.query.get_or_404(id)
        report.incident_type = custom_incident
        db.session.commit()
        flash('Incident type updated successfully.', 'success')
    else:
        flash('Custom incident type cannot be empty.', 'danger')
    return redirect(url_for('admin_reports'))

@app.route('/locate/<int:report_id>')
def locate_report(report_id):
    # Your logic here
    return f"Locate report with ID: {report_id}"

@app.route('/health')
def health_check():
    return 'OK', 200

if __name__ == "__main__":
    app.run(debug=True)

    import os

    port = int(os.environ.get('PORT', 5000))  # Get the port from the environment variable
    app.run(host='0.0.0.0', port=port) 