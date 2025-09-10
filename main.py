from fastapi import FastAPI    , Request, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from supabase import create_client
import os
from dotenv import load_dotenv
import uuid

# Load environment variables
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize FastAPI
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

BUCKET_NAME = "photos"

# Gallery page
@app.get("/", response_class=HTMLResponse)
def gallery(request: Request):
    data = supabase.table("photos").select("*").execute().data
    return templates.\
        TemplateResponse("index.html", {"request": request, "photos": data})

# Upload form page
@app.get("/upload", response_class=HTMLResponse)
def upload_form(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})

# Handle file upload
@app.post("/upload")
async def upload_photo(title: str = Form(...), file: UploadFile = Form(...)):
    try:
        # Generate unique filename
        ext = file.filename.split(".")[-1]
        filename = f"{uuid.uuid4()}.{ext}"

        # Read file contents
        contents = await file.read()
        # Upload to Supabase Storage
        supabase.storage.from_(BUCKET_NAME).upload(filename, contents)

        # Get public URL (string)
        public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(filename)

        # Insert record into database
        supabase.table("photos").\
            insert({"title": title, "image_url": public_url}).execute()

        return RedirectResponse("/", status_code=303)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Delete photo
@app.post("/delete/{photo_id}")
def delete_photo(photo_id: int):
    # Get photo info
    data = supabase.table("photos").select("*").eq("id", photo_id).execute().data
    if not data:
        raise HTTPException(status_code=404, detail="Photo not found")

    photo = data[0]
    # Delete from storage
    filename = photo["image_url"].split("/")[-1]
    supabase.storage.from_(BUCKET_NAME).remove([filename])

    # Delete from table
    supabase.table("photos").delete().eq("id", photo_id).execute()

    return RedirectResponse("/", status_code=303)
