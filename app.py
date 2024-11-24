from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
import folium
from geopy.geocoders import Nominatim


app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Configure the app to use the SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///reports.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Database model for reports
class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    location = db.Column(db.String(100))
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)  # Add timestamp here
    description = db.Column(db.Text)
    anonymous = db.Column(db.Boolean)
    username = db.Column(db.String(50))
    incident_type = db.Column(db.String(50))
    severity_type = db.Column(db.String(50))
    urgency_type = db.Column(db.String(50))
    status = db.Column(db.String(50), default='pending')  # New column for status

    def __repr__(self):
        return f"<Report {self.title}>"

# Initialize the database inside the application context
with app.app_context():
    db.create_all()

def geocode_location(location_name):
    geolocator = Nominatim(user_agent="incident_reporting")
    try:
        location = geolocator.geocode(location_name)
        if location:
            return location.latitude, location.longitude
        else:
            print(f"Geocoding failed for location: {location_name}")
            return None, None
    except Exception as e:
        print(f"Error during geocoding: {e}")
        return None, None


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
        else:
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
    location_option = request.form['location_option']
    report_location = request.form['report_location']
    latitude = request.form.get('latitude')  # Get latitude from hidden input
    longitude = request.form.get('longitude')  # Get longitude from hidden input
    report_time = request.form.get('report_time')  # Use .get() to avoid KeyError
    report_date = request.form['report_date']  # The full datetime string
    report_description = request.form['report_description']
    anonymous = request.form.get('anonymous') == 'on'
    incident_type = request.form['incident_type']
    severity_type = request.form['severity_type']
    urgency_type = request.form['urgency_type']

    # Include the username only if the report is not anonymous
    username = session.get('username') if not anonymous else None

    # Combine date and time into one datetime object
    try:
        timestamp = datetime.strptime(report_date, '%Y-%m-%dT%H:%M')  # Adjust to match datetime-local format
    except ValueError:
        timestamp = None  # Handle error in case of invalid format
    
     # If latitude and longitude are missing, attempt geocoding
    if not latitude or not longitude:
       latitude, longitude = geocode_location(report_location)

# Fallback to default if geocoding fails
    if latitude is None or longitude is None:
       latitude = 14.5995  # Default latitude (e.g., Manila)
       longitude = 120.9842  # Default longitude

    
    new_report = Report(
        title=report_title,
        location=report_location,
        latitude=float(latitude) if latitude else None,
        longitude=float(longitude) if longitude else None,
        timestamp=timestamp,  # Store the combined datetime
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
    # Get the report's anonymous status from the session or any other source
    # (you could store this in a session variable or pass it directly)
    anonymous = session.get('anonymous', False)  # For example, store anonymous status in the session
    return render_template('thank_you.html', anonymous=anonymous)


@app.route('/admin_reports')
def admin_reports():
    if session.get('role') != 'admin':
        return redirect('/')

    reports = Report.query.all()

    # Split timestamp into date and time attributes
    for report in reports:
        if report.timestamp:
            report.date = report.timestamp.strftime('%Y-%m-%d')  # Date part
            report.time = report.timestamp.strftime('%H:%M')  # Time part
        else:
            report.date = 'N/A'
            report.time = 'N/A'

    # Initialize the flag for warning sign
    warning_sign = None

    # Loop through reports and check for critical and immediate conditions
    for report in reports:
        if report.severity_type == 'critical' and report.urgency_type == 'immediate':
            warning_sign = True
            break  # Exit the loop once we find a report that matches the condition

    # Create map with reports
    map = folium.Map(location=[14.5995, 120.9842], zoom_start=12)
    for report in reports:
        if report.latitude and report.longitude:
            folium.Marker(
                location=[report.latitude, report.longitude],
                popup=report.title
            ).add_to(map)
    map.save('templates/map.html')

    return render_template('admin_reports.html', reports=reports, warning_sign=warning_sign)

@app.route('/locate/<int:report_id>')
def locate_report(report_id):
    report = Report.query.get_or_404(report_id)
    if report.latitude is None or report.longitude is None:
        flash('Invalid location data.', 'error')
        return redirect('/admin_reports')

    # Render the map with the report's coordinates
    map = folium.Map(location=[report.latitude, report.longitude], zoom_start=15)
    folium.Marker(
        location=[report.latitude, report.longitude],
        popup=report.title,
    ).add_to(map)
    map.save('templates/locate_map.html')
    return render_template('locate_map.html', report=report)

@app.route('/logout')
def logout():
    session.pop('role', None)
    session.pop('username', None)
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

@app.route('/search_reports', methods=['GET'])
def search_reports():
    search_query = request.args.get('search')
    if search_query:
        reports = Report.query.filter(
            Report.title.ilike(f'%{search_query}%') |
            Report.location.ilike(f'%{search_query}%') |
            Report.username.ilike(f'%{search_query}%') |
            Report.incident_type.ilike(f'%{search_query}%')
        ).all()
    else:
        reports = Report.query.all()

    return render_template('admin_reports.html', reports=reports)

@app.route('/mark_as_done/<int:id>', methods=['POST'])
def mark_as_done(id):
    # Fetch the report by ID
    report = Report.query.get_or_404(id)
    # Update the status to "done"
    report.status = 'done'
    db.session.commit()
    return redirect(url_for('admin_reports'))  # Redirect to the admin reports page

if __name__ == "__main__":
    app.run(debug=True)
