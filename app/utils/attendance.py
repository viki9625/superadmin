from shapely.geometry import Point, Polygon
from shapely.errors import ShapelyError
from typing import List, Tuple, Optional
import pandas as pd
from fastapi.responses import StreamingResponse, Response
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from datetime import date
import io
from models import Attendance
import logging

def is_point_within_polygon(longitude: float, latitude: float, geo_boundary: List[Tuple[float, float]]) -> bool:

    try:
        # Create Shapely Point and Polygon objects
        point = Point(longitude, latitude)  # Create a point from longitude and latitude
        polygon = Polygon(geo_boundary)  # Create a polygon from the geo_boundary

        # Check if the point is within the polygon
        return point.within(polygon)
    except ShapelyError as e:
        logging.error(f"Error checking if point is within polygon: {e}")
        return False
    
async def fetch_attendance_records(campus_name: str, department: Optional[str], user_id: Optional[int] = None):
    """Fetch attendance records based on the given filters."""
    query_conditions = [
        Attendance.link_id.campus.name == campus_name
    ]
    
    if department:
        query_conditions.append(Attendance.link_id.department == department)

    if user_id:
        query_conditions.append(Attendance.user_id == user_id)

    # Fetch attendance records with linked user data
    attendance_records = await Attendance.find(
        *query_conditions,
        fetch_links=True
    ).to_list()

    return attendance_records

def generate_csv_report(attendance_records, filename: str):
    """Generate a CSV report from attendance records."""
    data = [
        {
            "User ID": record.user_id,
            "Name": record.name,
            "Date": record.Date,
            "Punch In Time": record.punch_in_time.strftime('%Y-%m-%d %H:%M:%S') if record.punch_in_time else "N/A",
            "Punch Out Time": record.punch_out_time.strftime('%Y-%m-%d %H:%M:%S') if record.punch_out_time else "N/A",
            "Total Hours": f"{record.time_duration_in_hours:.2f}" if record.time_duration_in_hours is not None else "N/A",
            "Status": record.status.value if record.status else "N/A",
            "Out of Bound (min)": f"{record.total_out_of_bound_time_in_minutes:.2f}" if record.total_out_of_bound_time_in_minutes is not None else "0.00"
        }
        for record in attendance_records
    ]
    df = pd.DataFrame(data)

    # Stream the CSV file
    def generate_csv():
        with io.StringIO() as csv_buffer:
            df.to_csv(csv_buffer, index=False)
            csv_buffer.seek(0)
            yield csv_buffer.read()

    headers = {"Content-Disposition": f"attachment; filename={filename}"}
    return StreamingResponse(generate_csv(), media_type="text/csv", headers=headers)


def generate_pdf_report(attendance_records, filename: str):
    """Generate a PDF report from attendance records."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # Title
    story.append(Paragraph(f"Attendance Report", styles['Title']))
    story.append(Paragraph(f"Generated on: {date.today()}", styles['Normal']))
    story.append(Paragraph("<br/><br/>", styles['Normal']))

    # Table Data Preparation
    headers = ["User ID", "Name", "Date", "Punch In", "Punch Out", "Total Hours", "Status", "Out of Bound (min)"]
    data = [headers]

    for record in attendance_records:
        punch_in = record.punch_in_time.strftime('%H:%M:%S') if record.punch_in_time else "N/A"
        punch_out = record.punch_out_time.strftime('%H:%M:%S') if record.punch_out_time else "N/A"
        total_hours = f"{record.time_duration_in_hours:.2f}" if record.time_duration_in_hours is not None else "N/A"
        status_val = record.status.value if record.status else "N/A"
        out_of_bound = f"{record.total_out_of_bound_time_in_minutes:.2f}" if record.total_out_of_bound_time_in_minutes is not None else "0.00"

        data.append([
            str(record.user_id), record.name, str(record.Date),
            punch_in, punch_out, total_hours, status_val, out_of_bound
        ])

    # Create Table
    table = Table(data, colWidths=[60, 100, 70, 60, 60, 60, 60, 70])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(table)

    doc.build(story)
    buffer.seek(0)

    headers = {"Content-Disposition": f"attachment; filename={filename}"}
    return Response(buffer.read(), media_type="application/pdf", headers=headers)