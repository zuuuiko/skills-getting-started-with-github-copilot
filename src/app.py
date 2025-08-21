"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from motor.motor_asyncio import AsyncIOMotorClient
from contextlib import asynccontextmanager
import os
from pathlib import Path

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create MongoDB connection
    app.mongodb_client = AsyncIOMotorClient('mongodb://localhost:27017')
    app.mongodb = app.mongodb_client.school_activities
    yield
    # Shutdown: close MongoDB connection
    app.mongodb_client.close()

app = FastAPI(
    title="Mergington High School API",
    description="API for viewing and signing up for extracurricular activities",
    lifespan=lifespan
)

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(current_dir, "static")), name="static")

@app.get("/")
async def root():
    return RedirectResponse(url="/static/index.html")

@app.get("/activities")
async def get_activities():
    """Get all activities with their details"""
    cursor = app.mongodb.activities.find({}, {'_id': 0})
    activities_list = await cursor.to_list(length=None)
    
    # Convert list to dictionary with activity names as keys
    activities = {activity.pop('name'): activity for activity in activities_list}
    return activities

@app.post("/activities/{activity_name}/signup")
async def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    # Get the activity
    activity = await app.mongodb.activities.find_one({'name': activity_name})
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Check if student is already signed up
    if email in activity['participants']:
        raise HTTPException(status_code=400, detail="Student already signed up")

    # Add student to participants
    result = await app.mongodb.activities.update_one(
        {'name': activity_name},
        {'$push': {'participants': email}}
    )

    if result.modified_count == 1:
        return {"message": f"Signed up {email} for {activity_name}"}
    else:
        raise HTTPException(status_code=500, detail="Failed to sign up student")

@app.post("/activities/{activity_name}/unregister")
async def unregister_from_activity(activity_name: str, email: str):
    """Remove a student from an activity"""
    # Get the activity
    activity = await app.mongodb.activities.find_one({'name': activity_name})
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    # Check if student is registered
    if email not in activity['participants']:
        raise HTTPException(status_code=400, detail="Student is not registered for this activity")

    # Remove student from participants
    result = await app.mongodb.activities.update_one(
        {'name': activity_name},
        {'$pull': {'participants': email}}
    )

    if result.modified_count == 1:
        return {"message": f"Removed {email} from {activity_name}"}
    else:
        raise HTTPException(status_code=500, detail="Failed to remove student")
