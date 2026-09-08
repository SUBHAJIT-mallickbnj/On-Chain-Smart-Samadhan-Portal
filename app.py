# -*- coding: utf-8 -*-
import sys
import io
import os
import unicodedata
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Keep all application data paths stable when launched from another directory.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

from flask import Flask, render_template, request, redirect, url_for, jsonify, session
import pandas as pd
import pickle
import random
import string
import csv
from datetime import datetime
from functools import wraps
from blockchain_manager import BlockchainManager
from config import Config
from admin_manager import authenticate_admin, create_admin, get_all_admins, init_default_admin, update_display_name, get_admin_display_name
import activity_log as alog
import media_manager as mmgr
from mongo_store import get_database, load_complaints, replace_complaints, mongo_enabled

try:
    from sentence_transformers import SentenceTransformer
except Exception as error:
    SentenceTransformer = None
    print(f"[WARN] Sentence-transformers unavailable. ML classification disabled: {error}")

app = Flask(__name__)
app.config.from_object(Config)

COMPLAINT_COLUMNS = [
    "Reference No", "Wallet Address", "Name", "Email", "Phone", "Address", "City",
    "State", "Zip", "Complaint", "Department", "Status", "Date",
    "Blockchain Status", "Transaction Hash", "Solve Hash", "Media URLs",
    "Discard Reason", "Discarded By", "Discarded At", "Authority Solved Note",
    "Authority Solved By", "Authority Solved At", "Last Authority Action At",
    "Dispute Raised", "Dispute Raised At", "Permanently Closed"
]

DEPARTMENT_KEYWORDS = {
    "Electricity": ("electricity", "power supply", "power cut", "bijli", "बिजली", "বিদ্যুৎ", "current", "কারেন্ট"),
    "Water Supply": ("water supply", "water shortage", "no water", "paani", "pani", "pani nahi", "पानी", "जल", "পানি", "জল"),
    "Road Maintenance": ("pothole", "potholes", "road repair", "broken road", "सड़क", "सड़क", "गड्ढा", "রাস্তা", "গর্ত"),
    "Sanitation": ("sanitation", "cleaning", "safai", "सफाई", "পরিষ্কার"),
    "Public Lighting": ("street light", "streetlight", "स्ट्रीट लाइट", "রাস্তার লাইট"),
    "Gas Leaks": ("gas leak", "gas leakage", "गैस लीक", "গ্যাস লিক"),
    "Noise": ("noise", "loudspeaker", "loud speaker", "शोर", "तेज आवाज", "শব্দ"),
    "Waste Management": ("waste management", "garbage collection", "kachra", "कूड़ा", "আবর্জনা"),
    "Drainage": ("drain", "drainage", "नाली", "जल जम", "নালা", "জল জম"),
    "Tree/Landscape": ("tree", "fallen branch", "पेड़", "पेड़", "गাছ"),
    "Public Health": ("public health", "hospital", "clinic", "अस्पताल", "चिकित्सा", "হাসপাতাল", "চিকিৎসা"),
    "Consumer Affairs": ("refund", "consumer", "धोखा", "रिफंड", "ফেরত", "ভোক্তা"),
    "Rent/Building": ("rent", "building", "landlord", "किराया", "मकान मालिक", "ভাড়া", "বাড়িওয়ালা"),
    "Fire Safety": ("fire safety", "fire", "आग", "अग्नि", "আগুন"),
    "Traffic": ("traffic", "traffic signal", "ट्रैफिक", "यातायात", "ট্রাফিক"),
}

SANITATION_PRIORITY_PHRASES = (
    "decompos", "rotting garbage", "rotten garbage", "foul odor", "foul smell",
    "bad smell", "putrid", "সড়তে", "সড়ে", "পচতে", "পচে", "দুর্গন্ধ",
    "বদ গন্ধ", "सड़ने", "सड़ गया", "सड़ने लगा", "बदबू", "दुर्गंध", "गलने",
)

DEPARTMENT_PRIORITY_PHRASES = {
    "Electricity": ("power outage", "power failure", "इलाके में बिजली", "বিদ্যুৎ নেই"),
    "Water Supply": ("municipal water", "water pipeline", "पानी की पाइपलाइन", "জলের পাইপলাইন"),
    "Sanitation": ("public toilet", "dirty toilet", "सार्वजनिक शौचालय", "शौचालय गंदा", "পাবলিক টয়লেট", "টয়লেট নোংরা"),
    "Public Lighting": ("street lamp", "street lamps", "streetlight", "सड़क की लाइट", "स्ट्रीट लैंप", "রাস্তার বাতি", "স্ট্রিট ল্যাম্প"),
    "Noise": ("loudspeaker", "loud speaker", "लाउडस्पीकर", "तेज लाउडस्पीकर", "মাইকের আওয়াজ"),
    "Waste Management": ("garbage truck", "waste collection", "कूड़ा गाड़ी", "कचरा उठाने वाली गाड़ी", "আবর্জনার গাড়ি", "বর্জ্য সংগ্রহের গাড়ি"),
    "Drainage": ("blocked drain", "drain is blocked", "rainwater flooding", "नाली बंद", "बारिश का पानी", "নালা বন্ধ", "বৃষ্টির জল"),
    "Public Health": ("government clinic", "सरकारी क्लिनिक", "सरकारी अस्पताल", "সরকারি ক্লিনিক", "সরকারি হাসপাতাল"),
    "Consumer Affairs": ("defective product", "seller refused", "खराब सामान", "विक्रेता ने", "ত্রুটিপূর্ণ পণ্য", "বিক্রেতা"),
}


def ensure_complaints_csv():
    """Return the complaint table from MongoDB, importing the legacy CSV once."""
    return load_complaints(COMPLAINT_COLUMNS)


def load_complaints_df():
    """Return a complaint dataframe with the stable application schema."""
    return ensure_complaints_csv()


def save_complaints_df(dataframe):
    """Persist the complaint table in MongoDB."""
    replace_complaints(dataframe, COMPLAINT_COLUMNS)


def complaint_store_available():
    """Keep route guards compatible with the previous file-backed implementation."""
    return True


def classify_complaint(complaint):
    """Classify complaint text and expose runtime failures instead of hiding them."""
    if not complaint:
        return "General"

    normalized_complaint = unicodedata.normalize("NFKC", complaint).casefold()
    if any(phrase.casefold() in normalized_complaint for phrase in SANITATION_PRIORITY_PHRASES):
        return "Sanitation"

    for department, phrases in DEPARTMENT_PRIORITY_PHRASES.items():
        if any(phrase.casefold() in normalized_complaint for phrase in phrases):
            return department

    keyword_matches = {
        department: sum(keyword.casefold() in normalized_complaint for keyword in keywords)
        for department, keywords in DEPARTMENT_KEYWORDS.items()
    }
    strongest_department = max(keyword_matches, key=keyword_matches.get)
    if keyword_matches[strongest_department] > 0:
        return strongest_department

    if model is None or embedding_model is None:
        print("[ERROR] Complaint classification unavailable: ML model or embedding model is not loaded")
        return "General"
    try:
        complaint_embedding = embedding_model.encode([complaint])
        return model.predict(complaint_embedding)[0]
    except Exception as error:
        print(f"[ERROR] Complaint classification failed: {error}")
        return "General"

# Load ML models with error handling
try:
    with open("complaint_model.pkl", "rb") as f:
        model = pickle.load(f)
    print("[OK] ML model loaded successfully")
except Exception as error:
    print(f"[WARN] Complaint model unavailable. ML classification disabled: {error}")
    model = None

try:
    embedding_model = SentenceTransformer("embedding_model") if SentenceTransformer else None
    if embedding_model is None:
        raise RuntimeError("SentenceTransformer is unavailable")
    print("[OK] Embedding model loaded successfully")
except Exception as error:
    print(f"[WARN] Local embedding model unavailable; loading the same multilingual model from Hugging Face: {error}")
    try:
        embedding_model = SentenceTransformer(
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        ) if SentenceTransformer else None
        print("[OK] Remote multilingual embedding model loaded successfully")
    except Exception as fallback_error:
        print(f"[ERROR] Embedding model loading failed. Using fallback: {fallback_error}")
        embedding_model = None

try:
    dept_contacts = pd.read_csv("department_contacts.csv")
    print("[OK] Department contacts loaded successfully")
except FileNotFoundError:
    print("[ERROR] department_contacts.csv not found. Creating default")
    dept_contacts = pd.DataFrame({
        'Department': ['Water Supply', 'Electricity', 'Roads', 'Sanitation'],
        'Phone': ['+1234567890', '+1234567891', '+1234567892', '+1234567893'],
        'Email': ['water@city.gov', 'power@city.gov', 'roads@city.gov', 'sanitation@city.gov']
    })
    dept_contacts.to_csv("department_contacts.csv", index=False)

try:
    with open("classes.pkl", "rb") as f:
        all_departments = pickle.load(f)
    print("[OK] Department classes loaded successfully")
except Exception as error:
    print(f"[WARN] Department classes unavailable. Using default departments: {error}")
    all_departments = dept_contacts['Department'].tolist()

# Initialize blockchain manager
blockchain_manager = BlockchainManager()

if mongo_enabled():
    try:
        init_default_admin()
    except Exception as error:
        print(f"[WARN] MongoDB admin initialization deferred: {error}")

def login_required(f):
    """Decorator to require blockchain wallet login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'wallet_address' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require super admin login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/")
def landing():
    """Landing page for the project"""
    is_logged_in = 'wallet_address' in session
    wallet_address = session.get('wallet_address', '')
    return render_template("landing.html", is_logged_in=is_logged_in, wallet_address=wallet_address)


@app.route("/health")
def health():
    """Deployment health check that verifies MongoDB connectivity."""
    try:
        get_database().command("ping")
        return jsonify({"status": "ok", "database": "mongodb"})
    except Exception as error:
        return jsonify({"status": "error", "database": "unavailable", "message": str(error)}), 503

@app.route("/home")
def home():
    """Home page - redirect to login if not authenticated"""
    if 'wallet_address' not in session:
        return redirect(url_for('login'))
    return render_template("index.html", wallet_address=session['wallet_address'])

@app.route("/login")
def login():
    """Wallet connection page"""
    return render_template("login.html")

@app.route("/api/connect_wallet", methods=["POST"])
def connect_wallet():
    """Handle wallet connection"""
    data = request.get_json()
    wallet_address = data.get('address')
    signature = data.get('signature', '')
    
    # Validate wallet address
    if not blockchain_manager.is_valid_address(wallet_address):
        return jsonify({"success": False, "message": "Invalid wallet address"})
    
    # Store in session
    session['wallet_address'] = wallet_address
    session['authenticated'] = True
    
    return jsonify({
        "success": True, 
        "message": "Wallet connected successfully",
        "address": wallet_address
    })

@app.route("/logout")
def logout():
    """Logout user"""
    session.clear()
    return redirect(url_for('login'))

@app.route("/preview", methods=["POST"])
@login_required
def preview_complaint():
    """Preview complaint before submission"""
    name     = request.form.get("name", "").strip()
    email    = request.form.get("email", "").strip()
    phone    = request.form.get("phone", "").strip()
    address  = request.form.get("address", "").strip()
    city     = request.form.get("city", "").strip()
    state    = request.form.get("state", "").strip()
    zip_code = request.form.get("zip", "").strip()
    complaint = request.form.get("complaint", "").strip()

    # Save uploaded media files temporarily
    uploaded_files = request.files.getlist("media_files")
    uploaded_files = [f for f in uploaded_files if f and f.filename]
    temp_id = ""
    media_previews = []   # list of {name, ext, type} for preview
    temp_media_urls = ""  # pipe-separated local URLs for preview gallery
    if uploaded_files:
        valid = [f for f in uploaded_files if mmgr.allowed_file(f.filename)]
        temp_id, saved = mmgr.save_temp_files(valid[:mmgr.MAX_FILES])
        local_urls = []
        for i, s in enumerate(saved):
            media_previews.append({
                "name": s["original_name"],
                "ext":  s["ext"],
                "type": "video" if s["ext"] in mmgr.VIDEO_EXTS else "image",
            })
            # Build a URL that Flask can serve from static folder
            filename = os.path.basename(s["path"])
            local_urls.append(f'/static/uploads/temp/{temp_id}/{filename}')
        temp_media_urls = "|".join(local_urls)

    predicted_dept = classify_complaint(complaint)

    # Get department info
    dept_info = dept_contacts[dept_contacts["Department"] == predicted_dept]
    if not dept_info.empty:
        dept_info = dept_info.iloc[0].to_dict()
        if 'Contact' in dept_info:
            dept_info['Phone'] = dept_info['Contact']
    else:
        dept_info = {"Department": predicted_dept, "Phone": "N/A", "Email": "N/A"}

    departments_data = dept_contacts.to_dict(orient="records")

    return render_template(
        "preview.html",
        name=name, email=email, phone=phone, address=address,
        city=city, state=state, zip=zip_code, complaint=complaint,
        dept_info=dept_info, departments_data=departments_data,
        wallet_address=session['wallet_address'],
        temp_id=temp_id,
        media_previews=media_previews,
        temp_media_urls=temp_media_urls,
    )

@app.route("/confirm", methods=["POST"])
@login_required
def confirm_complaint():
    """Confirm and submit complaint to blockchain"""
    complaint_data = {
        'name':      request.form.get("name", "").strip(),
        'email':     request.form.get("email", "").strip(),
        'phone':     request.form.get("phone", "").strip(),
        'address':   request.form.get("address", "").strip(),
        'city':      request.form.get("city", "").strip(),
        'state':     request.form.get("state", "").strip(),
        'zip':       request.form.get("zip", "").strip(),
        'complaint': request.form.get("complaint", "").strip()
    }
    department = (request.form.get("correct_department") or request.form.get("department", "")).strip()
    temp_id    = request.form.get("temp_id", "").strip()

    # Generate reference number
    ref_no = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    
    # Update ML model with feedback if possible
    if model and embedding_model and complaint_data['complaint'] and department:
        try:
            feedback_df = pd.DataFrame([[complaint_data['complaint'], department]], 
                                     columns=["complaint_text", "product"])
            
            # Save to CSV for future training
            if os.path.exists("consumer_complaints.csv"):
                feedback_df.to_csv("consumer_complaints.csv", mode="a", header=False, 
                                 index=False, quoting=csv.QUOTE_MINIMAL)
            else:
                feedback_df.to_csv("consumer_complaints.csv", mode="w", header=True, 
                                 index=False, quoting=csv.QUOTE_MINIMAL)
            
            # Incremental learning
            complaint_embedding = embedding_model.encode([complaint_data['complaint']])
            model.partial_fit(complaint_embedding, [department], classes=all_departments)
            
            # Save updated model
            with open("complaint_model.pkl", "wb") as f:
                pickle.dump(model, f)
        except Exception as e:
            print(f"Error updating ML model: {e}")
    
    # Upload media to Cloudinary (or local fallback) BEFORE saving
    media_urls = ""
    if temp_id:
        try:
            urls = mmgr.upload_complaint_media(temp_id, ref_no)
            media_urls = "|".join(urls)
            print(f"[OK] Uploaded {len(urls)} media file(s) for {ref_no}")
        except Exception as e:
            print(f"[ERROR] Media upload failed: {e}")
    
    # Save to MongoDB first so complaint details survive blockchain failures.
    blockchain_result = {"success": False, "tx_hash": "N/A"}  # Default failed status
    
    try:
        ensure_complaints_csv()
        existing_df = load_complaints_df()
        new_row = {
            "Reference No":    ref_no,
            "Wallet Address":  session['wallet_address'],
            "Name":            complaint_data['name'],
            "Email":           complaint_data['email'],
            "Phone":           complaint_data['phone'],
            "Address":         complaint_data['address'],
            "City":            complaint_data['city'],
            "State":           complaint_data['state'],
            "Zip":             complaint_data['zip'],
            "Complaint":       complaint_data['complaint'],
            "Department":      department,
            "Status":          "Submitted",
            "Date":            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Blockchain Status": "Pending",
            "Transaction Hash":  "N/A",
            "Solve Hash":        "",
            "Media URLs":        media_urls,
            "Discard Reason":   "",
            "Discarded By":     "",
            "Discarded At":     "",
            "Authority Solved Note": "",
            "Authority Solved By": "",
            "Authority Solved At": "",
            "Last Authority Action At": "",
            "Dispute Raised": "",
            "Dispute Raised At": "",
            "Permanently Closed": "",
        }
        for col in COMPLAINT_COLUMNS:
            if col not in new_row:
                new_row[col] = ""
        new_df = pd.DataFrame([new_row], columns=COMPLAINT_COLUMNS)
        combined = pd.concat([existing_df.reindex(columns=COMPLAINT_COLUMNS), new_df], ignore_index=True)
        save_complaints_df(combined)
        print(f"[OK] Complaint {ref_no} saved to MongoDB for wallet {session['wallet_address']}")
    except Exception as e:
        print(f"[ERROR] Critical error saving to MongoDB: {e}")
        # Even if CSV save fails, continue to blockchain to not lose data
    
    # Now submit to blockchain AFTER local save
    try:
        blockchain_result = blockchain_manager.submit_complaint_to_blockchain(
            ref_no, complaint_data, department, session['wallet_address']
        )
        
        # Update MongoDB with blockchain results
        if blockchain_result["success"]:
            try:
                df = load_complaints_df()
                mask = df["Reference No"].astype(str) == str(ref_no)
                df.loc[mask, "Blockchain Status"] = "Success"
                df.loc[mask, "Transaction Hash"] = blockchain_result.get("tx_hash", "N/A")
                save_complaints_df(df)
                print(f"[OK] Updated blockchain status for {ref_no}")
            except Exception as e:
                print(f"[ERROR] Failed to update blockchain status: {e}")
        else:
            try:
                df = load_complaints_df()
                mask = df["Reference No"].astype(str) == str(ref_no)
                df.loc[mask, "Blockchain Status"] = "Failed"
                save_complaints_df(df)
                print(f"[ERROR] Blockchain submission failed for {ref_no}")
            except Exception as e:
                print(f"[ERROR] Failed to update failed status: {e}")
    except Exception as e:
        print(f"[ERROR] Blockchain submission error: {e}")
        blockchain_result = {"success": False, "message": str(e), "tx_hash": "N/A"}
    
    return render_template("confirmation.html",
                         ref_no=ref_no,
                         blockchain_result=blockchain_result,
                         wallet_address=session['wallet_address'],
                         media_urls=media_urls)

@app.route("/track", methods=["GET", "POST"])
def track_complaint():
    """Track complaint by reference number - publicly accessible, no login required"""
    result = None
    blockchain_data = None
    ref_no_prefill = request.args.get('ref_no', '')
    wallet_address = session.get('wallet_address', '')

    if request.method == "GET" and ref_no_prefill:
        ref_no = ref_no_prefill.strip().upper()
    elif request.method == "POST":
        ref_no = request.form.get("ref_no", "").strip().upper()
    else:
        ref_no = None

    if ref_no:
        if complaint_store_available():
            try:
                df = load_complaints_df()
                df["Reference No"] = df["Reference No"].astype(str)
                df = df.fillna("")

                # Public lookup: find by ref_no only (no wallet enforcement)
                match = df[df["Reference No"] == ref_no]
                if not match.empty:
                    result = match.iloc[0].to_dict()
                    print(f"✅ Found complaint in MongoDB: {ref_no}")
                else:
                    print(f"❌ Complaint not found in MongoDB: {ref_no}")
            except Exception as e:
                print(f"❌ Error reading local complaints: {e}")

        # Blockchain lookup
        blockchain_data = blockchain_manager.get_complaint_from_blockchain(ref_no)
        if blockchain_data:
            print(f"✅ Found complaint on blockchain: {ref_no}")
        else:
            print(f"❌ Complaint not found on blockchain: {ref_no}")

        if result is None and blockchain_data is None:
            result = "not_found"
        elif blockchain_data and result is None:
            result = "blockchain_only"

    # Attach activity log
    activity = []
    if result and result not in ("not_found", "blockchain_only"):
        ref = str(result.get("Reference No", ""))
        if ref:
            activity = alog.get(ref)

    return render_template("track.html",
                           result=result,
                           blockchain_data=blockchain_data,
                           wallet_address=wallet_address,
                           network_info=blockchain_manager.get_network_info(),
                           ref_no_prefill=ref_no_prefill,
                           activity=activity)

@app.route("/history")
@login_required
def view_history():
    """View user's complaint history with filtering"""
    filter_status = request.args.get('filter', 'all')  # all, processing, resolved
    state_filter  = request.args.get('state', 'all')   # all, or specific Indian state
    
    user_complaints = []
    wallet_address = session['wallet_address']
    
    # Initialize default stats to prevent template errors
    stats = {
        'total': 0,
        'processing': 0,
        'resolved': 0
    }
    
    print(f"🔍 Loading history for wallet: {wallet_address}")
    
    # Get complaints from local CSV first (faster)
    if complaint_store_available():
        try:
            df = load_complaints_df()
            # Filter by wallet address (case insensitive)
            user_df = df[df["Wallet Address"].astype(str).str.lower() == wallet_address.lower()]
            
            if not user_df.empty:
                user_complaints = user_df.to_dict(orient="records")
                # Clean up NaN values
                for complaint in user_complaints:
                    for key, value in complaint.items():
                        if pd.isna(value):
                            complaint[key] = ""
                        elif isinstance(value, float) and str(value) == "nan":
                            complaint[key] = ""
                            
                # Sort by date (newest first)
                user_complaints = sorted(user_complaints, 
                                       key=lambda x: x.get('Date', ''), 
                                       reverse=True)
                print(f"✅ Found {len(user_complaints)} complaints in local CSV")
            else:
                print(f"❌ No complaints found in local CSV for wallet: {wallet_address}")
                
        except Exception as e:
            print(f"❌ Error reading complaints history from CSV: {e}")
    
    # Apply filter before blockchain check
    all_user_complaints = user_complaints.copy()  # Keep original for stats
    
    # Calculate stats first (ensure it's always available)
    stats = {
        'total':            len(all_user_complaints),
        'processing':       len([c for c in all_user_complaints if c.get('Status') in ['Processing', 'Submitted'] and c.get('Dispute Raised') != 'Yes']),
        'resolved':         len([c for c in all_user_complaints if c.get('Status') in ['Solved', 'Resolved', 'Closed']]),
        'discarded':        len([c for c in all_user_complaints if c.get('Status') == 'Discarded by Authority']),
        'authority_solved': len([c for c in all_user_complaints if c.get('Status') == 'Marked as Solved by Authority']),
        'disputed':         len([c for c in all_user_complaints if c.get('Dispute Raised') == 'Yes' and c.get('Status') not in ['Processing', 'Submitted']]),
        'reopened':         len([c for c in all_user_complaints if c.get('Dispute Raised') == 'Yes' and c.get('Status') in ['Processing', 'Submitted']]),
    }
    
    # Now apply status filter
    if filter_status == 'processing':
        user_complaints = [c for c in user_complaints if c.get('Status') in ['Processing', 'Submitted'] and c.get('Dispute Raised') != 'Yes']
    elif filter_status == 'resolved':
        user_complaints = [c for c in user_complaints if c.get('Status') in ['Solved', 'Resolved', 'Closed']]
    elif filter_status == 'discarded':
        user_complaints = [c for c in user_complaints if c.get('Status') == 'Discarded by Authority']
    elif filter_status == 'authority_solved':
        user_complaints = [c for c in user_complaints if c.get('Status') == 'Marked as Solved by Authority']
    elif filter_status == 'disputed':
        user_complaints = [c for c in user_complaints if c.get('Dispute Raised') == 'Yes' and c.get('Status') not in ['Processing', 'Submitted']]
    elif filter_status == 'reopened':
        user_complaints = [c for c in user_complaints if c.get('Dispute Raised') == 'Yes' and c.get('Status') in ['Processing', 'Submitted']]
    
    # Apply state filter
    if state_filter != 'all':
        user_complaints = [c for c in user_complaints if str(c.get('State', '')).strip() == state_filter]
    
    # Also try to get from blockchain (as backup/verification)
    try:
        ref_numbers = blockchain_manager.get_user_complaints(wallet_address)
        print(f"📊 Blockchain reports {len(ref_numbers)} complaints for this wallet")
        
        # If we have blockchain data but no local data, create minimal records
        if ref_numbers and not all_user_complaints:
            for ref_no in ref_numbers:
                blockchain_complaint = blockchain_manager.get_complaint_from_blockchain(ref_no)
                if blockchain_complaint:
                    user_complaints.append({
                        "Reference No": ref_no,
                        "Department": blockchain_complaint.get('department', 'Unknown'),
                        "Status": blockchain_complaint.get('status', 'Unknown'),
                        "Date": blockchain_complaint.get('formatted_date', 'Unknown'),
                        "Name": "Blockchain Record",
                        "Complaint": "Details stored on blockchain",
                        "Blockchain Status": "Success"
                    })
    except Exception as e:
        print(f"❌ Error reading from blockchain: {e}")
    
    print(f"📋 Returning {len(user_complaints)} complaints for history view")
    
    # Attach activity logs
    for c in user_complaints:
        c['_activity'] = alog.get(str(c.get('Reference No', '')))

    return render_template("history.html", 
                         complaints=user_complaints,
                         wallet_address=wallet_address,
                         network_info=blockchain_manager.get_network_info(),
                         stats=stats,
                         filter_status=filter_status,
                         state_filter=state_filter)

@app.route("/api/blockchain_status")
@login_required
def blockchain_status():
    """API endpoint to check blockchain connection status"""
    return jsonify({
        "connected": blockchain_manager.is_connected(),
        "contract_address": Config.CONTRACT_ADDRESS,
        "user_address": session.get('wallet_address')
    })

@app.route("/mark_solved", methods=["POST"])
@login_required
def mark_complaint_solved():
    """Mark complaint as solved with CAPTCHA verification"""
    data = request.get_json()
    ref_no = data.get('ref_no', '').strip().upper()
    captcha_text = data.get('captcha_text', '').strip()
    expected_captcha = data.get('expected_captcha', '').strip()
    
    # Verify CAPTCHA
    if captcha_text.lower() != expected_captcha.lower():
        return jsonify({"success": False, "message": "CAPTCHA verification failed"})
    
    # Mark as solved on blockchain
    blockchain_result = blockchain_manager.mark_complaint_as_solved(ref_no, session['wallet_address'])
    
    if blockchain_result["success"]:
        # Update local CSV
        try:
            if complaint_store_available():
                df = load_complaints_df()
                
                # Add Solve Hash column if it doesn't exist
                if "Solve Hash" not in df.columns:
                    df["Solve Hash"] = ""
                
                # Update status and solve hash for this complaint
                mask = (df["Reference No"].astype(str) == ref_no) & \
                       (df["Wallet Address"].str.lower() == session['wallet_address'].lower())
                df.loc[mask, "Status"] = "Solved"
                df.loc[mask, "Solve Hash"] = blockchain_result.get("tx_hash", "")
                save_complaints_df(df)
                print(f"✅ Updated complaint {ref_no} status to Solved in local CSV")
        except Exception as e:
            print(f"❌ Error updating local CSV: {e}")
        
        return jsonify({
            "success": True, 
            "message": "Complaint marked as solved successfully!",
            "tx_hash": blockchain_result.get("tx_hash"),
            "explorer_url": blockchain_result.get("explorer_url")
        })
    else:
        return jsonify({
            "success": False, 
            "message": blockchain_result.get("message", "Failed to mark as solved")
        })

@app.route("/all_complaints")
@login_required
def all_complaints():
    """View all complaints from all users with filters"""
    department_filter = request.args.get('department', 'all')
    status_filter     = request.args.get('status', 'all')
    state_filter      = request.args.get('state', 'all')
    search_query      = request.args.get('search', '').strip()
    
    complaints_list = []
    
    # Load all complaints from CSV
    if complaint_store_available():
        try:
            df = load_complaints_df()
            
            # Handle NaN values and ensure proper data types
            df = df.fillna("")  # Replace NaN with empty strings
            df["Wallet Address"] = df["Wallet Address"].astype(str).replace('nan', '')
            df["Department"] = df["Department"].astype(str)
            df["Status"] = df["Status"].astype(str)
            df["Blockchain Status"] = df["Blockchain Status"].astype(str)
            
            # Keep all locally stored complaints visible to the portal.
            # Blockchain status is informational; a pending/failed on-chain write should not hide the complaint.
            df = df.fillna("")

            # Keep original unfiltered data for stats calculation
            original_df = df.copy()  # Keep original for stats calculation
            
            # Apply search filter for transaction hash
            if search_query:
                # Normalize search query - remove 0x prefix if present for flexible search
                search_clean = search_query.strip()
                if search_clean.startswith("0x"):
                    search_clean = search_clean[2:]
                
                # Search in Transaction Hash and Solve Hash columns (both with and without 0x prefix)
                search_mask = (
                    df["Transaction Hash"].astype(str).str.contains(search_clean, case=False, na=False) |
                    df.get("Solve Hash", pd.Series(dtype=str)).astype(str).str.contains(search_clean, case=False, na=False)
                )
                df = df[search_mask]
            
            # Apply department filter
            if department_filter != 'all':
                df = df[df["Department"] == department_filter]
            
            # Apply status filter
            if status_filter != 'all':
                if status_filter == 'processing':
                    df = df[df["Status"].isin(["Processing", "Submitted"]) & (df.get("Dispute Raised", pd.Series(dtype=str)).astype(str) != 'Yes')]
                elif status_filter == 'resolved':
                    df = df[df["Status"].isin(["Solved", "Resolved", "Closed"])]
                elif status_filter == 'discarded':
                    df = df[df["Status"] == "Discarded by Authority"]
                elif status_filter == 'authority_solved':
                    df = df[df["Status"] == "Marked as Solved by Authority"]
                elif status_filter == 'disputed':
                    # Dispute raised but NOT yet reopened to processing
                    dispute_col = df.get("Dispute Raised", pd.Series(dtype=str)).astype(str)
                    df = df[(dispute_col == 'Yes') & ~df["Status"].isin(["Processing", "Submitted"])]
                elif status_filter == 'reopened':
                    # Dispute raised AND complaint is back to processing (reopened)
                    dispute_col = df.get("Dispute Raised", pd.Series(dtype=str)).astype(str)
                    df = df[(dispute_col == 'Yes') & df["Status"].isin(["Processing", "Submitted"])]
                else:
                    df = df[df["Status"] == status_filter]
            
            # Apply state filter
            if state_filter != 'all':
                if "State" in df.columns:
                    df = df[df["State"].astype(str).str.strip() == state_filter]
            
            # Convert to list and sort by date
            complaints_list = df.to_dict(orient="records")
            
            # Clean up NaN values
            for complaint in complaints_list:
                for key, value in complaint.items():
                    if pd.isna(value):
                        complaint[key] = ""
                    elif isinstance(value, float) and str(value) == "nan":
                        complaint[key] = ""
                        
            complaints_list = sorted(complaints_list, 
                                  key=lambda x: x.get('Date', ''), 
                                  reverse=True)
                                  
            print(f"✅ Found {len(complaints_list)} complaints (filtered)")
            
        except Exception as e:
            print(f"❌ Error reading all complaints: {e}")
    
    # Get unique departments for filter
    all_departments = dept_contacts['Department'].tolist() if not dept_contacts.empty else []
    
    # Get complaint statistics from original unfiltered data (before search and status filters)
    if 'original_df' in locals() and not original_df.empty:
        # For stats, only apply department filter (not search or status filters)
        stats_df = original_df.copy()
        if department_filter != 'all':
            stats_df = stats_df[stats_df["Department"] == department_filter]
            
        _dispute_col = stats_df.get("Dispute Raised", pd.Series(dtype=str)).astype(str)
        stats = {
            'total':            len(stats_df),
            'processing':       len(stats_df[stats_df["Status"].isin(["Processing", "Submitted"]) & (_dispute_col != 'Yes')]),
            'resolved':         len(stats_df[stats_df["Status"].isin(["Solved", "Resolved", "Closed"])]),
            'discarded':        len(stats_df[stats_df["Status"] == "Discarded by Authority"]),
            'authority_solved': len(stats_df[stats_df["Status"] == "Marked as Solved by Authority"]),
            'disputed':         len(stats_df[(_dispute_col == 'Yes') & ~stats_df["Status"].isin(["Processing", "Submitted"])]),
            'reopened':         len(stats_df[(_dispute_col == 'Yes') & stats_df["Status"].isin(["Processing", "Submitted"])]),
        }
    else:
        stats = {
            'total': 0, 'processing': 0, 'resolved': 0,
            'discarded': 0, 'authority_solved': 0,
            'disputed': 0, 'reopened': 0,
        }
    
    return render_template("all_complaints.html", 
                         complaints=complaints_list,
                         departments=all_departments,
                         selected_department=department_filter,
                         selected_status=status_filter,
                         selected_state=state_filter,
                         search_query=search_query,
                         stats=stats,
                         wallet_address=session['wallet_address'])

@app.route("/api/generate_captcha")
def generate_captcha():
    """Generate simple text CAPTCHA"""
    import random
    import string
    
    # Generate random 5-character string
    captcha_text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    
    return jsonify({"captcha": captcha_text})

# ─────────────────────────────────────────────
# SUPER ADMIN ROUTES
# ─────────────────────────────────────────────

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    """Super Admin login page"""
    if 'admin_id' in session:
        return redirect(url_for('admin_dashboard'))
    error = None
    if request.method == "POST":
        admin_id = request.form.get("admin_id", "").strip()
        password = request.form.get("password", "").strip()
        admin = authenticate_admin(admin_id, password)
        if admin:
            session['admin_id'] = admin['admin_id']
            session['admin_display_name'] = admin['display_name']
            session['admin_department'] = admin['department']
            return redirect(url_for('admin_dashboard'))
        else:
            error = "Invalid Admin ID or Password."
    return render_template("admin_login.html", error=error)


@app.route("/admin/logout")
def admin_logout():
    """Logout super admin"""
    session.pop('admin_id', None)
    session.pop('admin_display_name', None)
    session.pop('admin_department', None)
    return redirect(url_for('admin_login'))


@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    """Super Admin dashboard"""
    admin_id      = session['admin_id']
    admin_display = session.get('admin_display_name', admin_id)
    admin_dept    = session['admin_department']

    status_filter = request.args.get('status', 'all')
    search_ref    = request.args.get('search_ref', '').strip().upper()
    dept_filter   = request.args.get('dept_filter', 'all')
    state_filter  = request.args.get('state_filter', 'all')
    date_from_str = request.args.get('date_from', '').strip()
    date_to_str   = request.args.get('date_to', '').strip()

    all_dept_complaints = []
    now = datetime.now()

    if complaint_store_available():
        try:
            df = load_complaints_df()
            df = df.fillna("")

            for col in ["Discard Reason", "Discarded By", "Discarded At",
                        "Authority Solved Note", "Authority Solved By", "Authority Solved At",
                        "Last Authority Action At",
                        "Dispute Raised", "Dispute Raised At", "Permanently Closed",
                        "Media URLs"]:
                if col not in df.columns:
                    df[col] = ""

            if admin_dept != "All":
                df = df[df["Department"] == admin_dept]

            # Keep all locally recorded complaints visible to the admin portal.
            # The local CSV is the source of truth; blockchain may be pending or temporarily unavailable.
            df = df.fillna("")

            # Auto-close: expired authority actions
            for idx, row in df.iterrows():
                anchor_str = (str(row.get("Last Authority Action At", "")) or
                              str(row.get("Discarded At", "")) or
                              str(row.get("Authority Solved At", "")))
                if (str(row.get("Status", "")) in ["Discarded by Authority",
                                                    "Marked as Solved by Authority"]
                        and str(row.get("Dispute Raised", "")) != "Yes"
                        and str(row.get("Permanently Closed", "")) != "Yes"
                        and anchor_str):
                    try:
                        if (now - datetime.strptime(anchor_str, "%Y-%m-%d %H:%M:%S")
                                ).total_seconds() > 48 * 3600:
                            df.at[idx, "Status"] = "Permanently Closed"
                            df.at[idx, "Permanently Closed"] = "Yes"
                            ref = str(row.get("Reference No", ""))
                            if ref:
                                alog.append(ref, "Permanently Closed", "System",
                                            "48-hour dispute window expired")
                    except Exception:
                        pass

            # Compute global stats BEFORE applying status / search / state filters
            # (but after dept + blockchain filters, so stats reflect the admin's dept scope)
            stats_base = df.copy()
            if dept_filter != 'all' and admin_dept == 'All':
                stats_base = stats_base[stats_base["Department"] == dept_filter]
            stats = {
                'total':            len(stats_base),
                'active':           len(stats_base[
                                        stats_base["Status"].isin(["Submitted", "Processing"]) &
                                        (stats_base["Dispute Raised"] != "Yes")
                                    ]),
                'discarded':        len(stats_base[stats_base["Status"] == "Discarded by Authority"]),
                'authority_solved': len(stats_base[stats_base["Status"] == "Marked as Solved by Authority"]),
                'dispute':          len(stats_base[
                                        (stats_base["Dispute Raised"] == "Yes") &
                                        (stats_base["Status"] == "Processing")
                                    ]),
                'resolved':         len(stats_base[stats_base["Status"].isin(
                                        ["Solved", "Resolved", "Closed", "Permanently Closed"])]),
            }

            # Status filter
            if status_filter == 'active':
                df = df[df["Status"].isin(["Submitted", "Processing"])]
            elif status_filter == 'discarded':
                df = df[df["Status"] == "Discarded by Authority"]
            elif status_filter == 'authority_solved':
                df = df[df["Status"] == "Marked as Solved by Authority"]
            elif status_filter == 'dispute':
                df = df[(df["Dispute Raised"] == "Yes") & (df["Status"] == "Processing")]
            elif status_filter == 'resolved':
                df = df[df["Status"].isin(["Solved", "Resolved", "Closed", "Permanently Closed"])]

            # Search by ref
            if search_ref:
                df = df[df["Reference No"].astype(str).str.upper().str.contains(search_ref, na=False)]

            # Secondary dept filter
            if dept_filter != 'all' and admin_dept == 'All':
                df = df[df["Department"] == dept_filter]

            # State filter
            if state_filter != 'all':
                if "State" in df.columns:
                    df = df[df["State"].astype(str).str.strip() == state_filter]

            # Date range
            if date_from_str:
                try:
                    df["_dcmp"] = pd.to_datetime(df["Date"], errors='coerce')
                    df = df[df["_dcmp"] >= pd.to_datetime(date_from_str)]
                    df = df.drop(columns=["_dcmp"])
                except Exception:
                    pass
            if date_to_str:
                try:
                    df["_dcmp"] = pd.to_datetime(df["Date"], errors='coerce')
                    df = df[df["_dcmp"] <= pd.to_datetime(date_to_str + " 23:59:59")]
                    df = df.drop(columns=["_dcmp"])
                except Exception:
                    pass

            all_dept_complaints = df.to_dict(orient="records")
            all_dept_complaints = sorted(all_dept_complaints,
                                         key=lambda x: x.get('Date', ''), reverse=True)

            # Persist auto-close to full CSV
            full_df = load_complaints_df()
            full_df = full_df.fillna("")
            for col in ["Discard Reason", "Discarded By", "Discarded At",
                        "Authority Solved Note", "Authority Solved By", "Authority Solved At",
                        "Last Authority Action At",
                        "Dispute Raised", "Dispute Raised At", "Permanently Closed"]:
                if col not in full_df.columns:
                    full_df[col] = ""
            for idx, row in full_df.iterrows():
                anchor_str = (str(row.get("Last Authority Action At", "")) or
                              str(row.get("Discarded At", "")) or
                              str(row.get("Authority Solved At", "")))
                if (str(row.get("Status", "")) in ["Discarded by Authority",
                                                    "Marked as Solved by Authority"]
                        and str(row.get("Dispute Raised", "")) != "Yes"
                        and str(row.get("Permanently Closed", "")) != "Yes"
                        and anchor_str):
                    try:
                        if (now - datetime.strptime(anchor_str, "%Y-%m-%d %H:%M:%S")
                                ).total_seconds() > 48 * 3600:
                            full_df.at[idx, "Status"] = "Permanently Closed"
                            full_df.at[idx, "Permanently Closed"] = "Yes"
                    except Exception:
                        pass
            save_complaints_df(full_df)

        except Exception as e:
            print(f"❌ Error loading admin dashboard: {e}")
            stats = {
                'total': 0, 'active': 0, 'discarded': 0,
                'authority_solved': 0, 'dispute': 0, 'resolved': 0,
            }
    else:
        stats = {
            'total': 0, 'active': 0, 'discarded': 0,
            'authority_solved': 0, 'dispute': 0, 'resolved': 0,
        }

    # Attach activity log
    for c in all_dept_complaints:
        c['_activity'] = alog.get(str(c.get('Reference No', '')))

    available_departments = dept_contacts['Department'].tolist() if not dept_contacts.empty else []

    return render_template("admin_dashboard.html",
                           complaints=all_dept_complaints,
                           admin_id=admin_id,
                           admin_display=admin_display,
                           admin_dept=admin_dept,
                           stats=stats,
                           status_filter=status_filter,
                           search_ref=search_ref,
                           dept_filter=dept_filter,
                           state_filter=state_filter,
                           date_from=date_from_str,
                           date_to=date_to_str,
                           available_departments=available_departments,
                           network_info=blockchain_manager.get_network_info())


@app.route("/admin/discard_complaint", methods=["POST"])
@admin_required
def admin_discard_complaint():
    """Discard a complaint with mandatory reason"""
    data   = request.get_json()
    ref_no = data.get('ref_no', '').strip().upper()
    reason = data.get('reason', '').strip()

    if not ref_no:
        return jsonify({"success": False, "message": "Reference number is required."})
    if not reason:
        return jsonify({"success": False, "message": "Discard reason is mandatory."})

    admin_dept    = session['admin_department']
    admin_display = session.get('admin_display_name', session['admin_id'])
    actor_label   = f"{admin_display} ({admin_dept})"

    if load_complaints_df().empty:
        return jsonify({"success": False, "message": "No complaints found."})

    try:
        df = load_complaints_df()
        df = df.fillna("")

        for col in ["Discard Reason", "Discarded By", "Discarded At",
                    "Authority Solved Note", "Authority Solved By", "Authority Solved At",
                    "Last Authority Action At",
                    "Dispute Raised", "Dispute Raised At", "Permanently Closed"]:
            if col not in df.columns:
                df[col] = ""

        df["Reference No"] = df["Reference No"].astype(str)
        mask = df["Reference No"] == ref_no

        if not mask.any():
            return jsonify({"success": False, "message": "Complaint not found."})

        if admin_dept != "All":
            dept_mask = mask & (df["Department"] == admin_dept)
            if not dept_mask.any():
                return jsonify({"success": False, "message": "Access denied: not your department."})
            mask = dept_mask

        if df.loc[mask, "Status"].iloc[0] == "Permanently Closed":
            return jsonify({"success": False, "message": "Complaint is permanently closed."})

        if df.loc[mask, "Status"].iloc[0] not in ["Submitted", "Processing"]:
            return jsonify({"success": False, "message": "Complaint must be active before an authority action can be taken."})

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        df.loc[mask, "Status"]                 = "Discarded by Authority"
        df.loc[mask, "Discard Reason"]          = reason
        df.loc[mask, "Discarded By"]            = actor_label
        df.loc[mask, "Discarded At"]            = now_str
        df.loc[mask, "Last Authority Action At"]= now_str
        df.loc[mask, "Dispute Raised"]          = ""
        df.loc[mask, "Dispute Raised At"]       = ""
        df.loc[mask, "Permanently Closed"]      = ""

        save_complaints_df(df)
        alog.append(ref_no, "Discarded by Authority", actor_label, reason)
        return jsonify({"success": True, "message": "Complaint discarded successfully."})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


@app.route("/admin/mark_solved_authority", methods=["POST"])
@admin_required
def admin_mark_solved_authority():
    """Mark a complaint as solved by authority"""
    data   = request.get_json()
    ref_no = data.get('ref_no', '').strip().upper()
    note   = data.get('note', '').strip()

    if not ref_no:
        return jsonify({"success": False, "message": "Reference number is required."})
    if not note:
        return jsonify({"success": False, "message": "A resolution note is required."})

    admin_dept    = session['admin_department']
    admin_display = session.get('admin_display_name', session['admin_id'])
    actor_label   = f"{admin_display} ({admin_dept})"

    if load_complaints_df().empty:
        return jsonify({"success": False, "message": "No complaints found."})

    try:
        df = load_complaints_df()
        df = df.fillna("")

        for col in ["Discard Reason", "Discarded By", "Discarded At",
                    "Authority Solved Note", "Authority Solved By", "Authority Solved At",
                    "Last Authority Action At",
                    "Dispute Raised", "Dispute Raised At", "Permanently Closed"]:
            if col not in df.columns:
                df[col] = ""

        df["Reference No"] = df["Reference No"].astype(str)
        mask = df["Reference No"] == ref_no

        if not mask.any():
            return jsonify({"success": False, "message": "Complaint not found."})

        if admin_dept != "All":
            dept_mask = mask & (df["Department"] == admin_dept)
            if not dept_mask.any():
                return jsonify({"success": False, "message": "Access denied: not your department."})
            mask = dept_mask

        if df.loc[mask, "Status"].iloc[0] == "Permanently Closed":
            return jsonify({"success": False, "message": "Complaint is permanently closed."})

        if df.loc[mask, "Status"].iloc[0] not in ["Submitted", "Processing"]:
            return jsonify({"success": False, "message": "Complaint must be active before an authority action can be taken."})

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        df.loc[mask, "Status"]                  = "Marked as Solved by Authority"
        df.loc[mask, "Authority Solved Note"]   = note
        df.loc[mask, "Authority Solved By"]     = actor_label
        df.loc[mask, "Authority Solved At"]     = now_str
        df.loc[mask, "Last Authority Action At"]= now_str
        df.loc[mask, "Dispute Raised"]          = ""
        df.loc[mask, "Dispute Raised At"]       = ""
        df.loc[mask, "Permanently Closed"]      = ""

        save_complaints_df(df)
        alog.append(ref_no, "Marked as Solved by Authority", actor_label, note)
        return jsonify({"success": True, "message": "Complaint marked as solved by authority."})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


@app.route("/admin/create_admin", methods=["POST"])
@admin_required
def admin_create_admin():
    """Allow an existing admin to create a new admin account"""
    data         = request.get_json()
    new_id       = data.get('admin_id', '').strip()
    password     = data.get('password', '').strip()
    department   = data.get('department', '').strip()
    display_name = data.get('display_name', '').strip()

    success, message = create_admin(new_id, password, department,
                                    created_by=session['admin_id'],
                                    display_name=display_name)
    return jsonify({"success": success, "message": message})


@app.route("/admin/update_display_name", methods=["POST"])
@admin_required
def admin_update_display_name():
    """Allow an admin to update their own display name"""
    data     = request.get_json()
    new_name = data.get('display_name', '').strip()
    success, message = update_display_name(session['admin_id'], new_name)
    if success:
        session['admin_display_name'] = new_name
    return jsonify({"success": success, "message": message})


@app.route("/admin/admins")
@admin_required
def admin_list_admins():
    """Return list of all admins"""
    return jsonify({"admins": get_all_admins()})


@app.route("/admin/departments")
@admin_required
def admin_get_departments():
    """Return list of system departments for dropdown"""
    depts = dept_contacts['Department'].tolist() if not dept_contacts.empty else []
    return jsonify({"departments": depts})


@app.route("/raise_dispute", methods=["POST"])
@login_required
def raise_dispute():
    """Citizen raises a dispute on a discarded / authority-solved complaint (within 48 hours)"""
    data   = request.get_json()
    ref_no = data.get('ref_no', '').strip().upper()
    wallet = session['wallet_address'].lower()

    if not ref_no:
        return jsonify({"success": False, "message": "Reference number required."})

    if load_complaints_df().empty:
        return jsonify({"success": False, "message": "No complaints found."})

    try:
        df = load_complaints_df()
        df = df.fillna("")

        for col in ["Discard Reason", "Discarded By", "Discarded At",
                    "Authority Solved Note", "Authority Solved By", "Authority Solved At",
                    "Last Authority Action At",
                    "Dispute Raised", "Dispute Raised At", "Permanently Closed"]:
            if col not in df.columns:
                df[col] = ""

        df["Reference No"] = df["Reference No"].astype(str)
        mask = ((df["Reference No"] == ref_no) &
                (df["Wallet Address"].str.lower() == wallet))

        if not mask.any():
            return jsonify({"success": False, "message": "Complaint not found or access denied."})

        row    = df.loc[mask].iloc[0]
        status = str(row.get("Status", ""))

        if status not in ["Discarded by Authority", "Marked as Solved by Authority"]:
            return jsonify({"success": False,
                            "message": "Dispute can only be raised on discarded or authority-solved complaints."})

        if str(row.get("Permanently Closed", "")) == "Yes":
            return jsonify({"success": False,
                            "message": "Complaint is permanently closed. Dispute window has passed."})

        anchor_str = (str(row.get("Last Authority Action At", "")) or
                      str(row.get("Discarded At", "")) or
                      str(row.get("Authority Solved At", "")))
        if not anchor_str:
            return jsonify({"success": False, "message": "Authority action timestamp missing."})

        try:
            anchor = datetime.strptime(anchor_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return jsonify({"success": False, "message": "Invalid authority action timestamp."})

        elapsed = (datetime.now() - anchor).total_seconds()
        if elapsed > 48 * 3600:
            df.loc[mask, "Status"]            = "Permanently Closed"
            df.loc[mask, "Permanently Closed"]= "Yes"
            save_complaints_df(df)
            alog.append(ref_no, "Permanently Closed", "System",
                        "48-hour dispute window expired")
            return jsonify({"success": False,
                            "message": "The 48-hour dispute window has expired. Complaint is permanently closed."})

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        df.loc[mask, "Status"]           = "Processing"
        df.loc[mask, "Dispute Raised"]   = "Yes"
        df.loc[mask, "Dispute Raised At"]= now_str
        save_complaints_df(df)

        wa = session['wallet_address']
        citizen_label = f"Citizen ({wa[:8]}...{wa[-4:]})"
        alog.append(ref_no, "Dispute Raised – Complaint Reopened", citizen_label)

        return jsonify({"success": True,
                        "message": "Dispute raised successfully. Your complaint has been reopened."})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


@app.route("/admin/dashboard", endpoint="_duplicate_admin_dashboard")
@admin_required
def admin_dashboard():
    """Super Admin dashboard - shows complaints for admin's department"""
    admin_id = session['admin_id']
    admin_dept = session['admin_department']
    status_filter = request.args.get('status', 'all')

    all_dept_complaints = []

    if complaint_store_available():
        try:
            df = load_complaints_df()
            df = df.fillna("")

            # Ensure new columns exist
            for col in ["Discard Reason", "Discarded By", "Discarded At",
                        "Dispute Raised", "Dispute Raised At", "Permanently Closed"]:
                if col not in df.columns:
                    df[col] = ""

            # Filter by department (unless 'All' admin)
            if admin_dept != "All":
                df = df[df["Department"] == admin_dept]

            # Keep all local complaints visible in admin queues even when blockchain status is pending or failed.
            df = df.fillna("")

            # Auto-close discarded complaints older than 48h with no dispute
            from datetime import timedelta
            now = datetime.now()
            for idx, row in df.iterrows():
                if (str(row.get("Status", "")) == "Discarded by Authority"
                        and str(row.get("Dispute Raised", "")) != "Yes"
                        and str(row.get("Permanently Closed", "")) != "Yes"
                        and row.get("Discarded At", "") != ""):
                    try:
                        discarded_at = datetime.strptime(str(row["Discarded At"]), "%Y-%m-%d %H:%M:%S")
                        if (now - discarded_at).total_seconds() > 48 * 3600:
                            df.at[idx, "Status"] = "Permanently Closed"
                            df.at[idx, "Permanently Closed"] = "Yes"
                    except Exception:
                        pass

            # Apply status filter
            if status_filter == 'active':
                df = df[df["Status"].isin(["Submitted", "Processing"])]
            elif status_filter == 'discarded':
                df = df[df["Status"] == "Discarded by Authority"]
            elif status_filter == 'dispute':
                df = df[df["Dispute Raised"] == "Yes"]
            elif status_filter == 'resolved':
                df = df[df["Status"].isin(["Solved", "Resolved", "Closed", "Permanently Closed"])]

            all_dept_complaints = df.to_dict(orient="records")
            all_dept_complaints = sorted(all_dept_complaints,
                                         key=lambda x: x.get('Date', ''), reverse=True)

            # Persist auto-close changes back to CSV (full CSV update)
            full_df = load_complaints_df()
            full_df = full_df.fillna("")
            for col in ["Discard Reason", "Discarded By", "Discarded At",
                        "Dispute Raised", "Dispute Raised At", "Permanently Closed"]:
                if col not in full_df.columns:
                    full_df[col] = ""
            from datetime import timedelta
            for idx, row in full_df.iterrows():
                if (str(row.get("Status", "")) == "Discarded by Authority"
                        and str(row.get("Dispute Raised", "")) != "Yes"
                        and str(row.get("Permanently Closed", "")) != "Yes"
                        and row.get("Discarded At", "") != ""):
                    try:
                        discarded_at = datetime.strptime(str(row["Discarded At"]), "%Y-%m-%d %H:%M:%S")
                        if (now - discarded_at).total_seconds() > 48 * 3600:
                            full_df.at[idx, "Status"] = "Permanently Closed"
                            full_df.at[idx, "Permanently Closed"] = "Yes"
                    except Exception:
                        pass
            save_complaints_df(full_df)

        except Exception as e:
            print(f"❌ Error loading admin dashboard: {e}")

    stats = {
        'total': len(all_dept_complaints),
        'active': len([c for c in all_dept_complaints if c.get('Status') in ['Submitted', 'Processing']]),
        'discarded': len([c for c in all_dept_complaints if c.get('Status') == 'Discarded by Authority']),
        'dispute': len([c for c in all_dept_complaints if c.get('Dispute Raised') == 'Yes']),
        'resolved': len([c for c in all_dept_complaints if c.get('Status') in ['Solved', 'Resolved', 'Closed', 'Permanently Closed']]),
    }

    return render_template("admin_dashboard.html",
                           complaints=all_dept_complaints,
                           admin_id=admin_id,
                           admin_dept=admin_dept,
                           stats=stats,
                           status_filter=status_filter,
                           network_info=blockchain_manager.get_network_info())


@app.route("/admin/discard_complaint", methods=["POST"], endpoint="_duplicate_admin_discard_complaint")
@admin_required
def admin_discard_complaint():
    """Discard a complaint with mandatory reason"""
    data = request.get_json()
    ref_no = data.get('ref_no', '').strip().upper()
    reason = data.get('reason', '').strip()

    if not ref_no:
        return jsonify({"success": False, "message": "Reference number is required."})
    if not reason:
        return jsonify({"success": False, "message": "Discard reason is mandatory."})

    admin_dept = session['admin_department']

    if load_complaints_df().empty:
        return jsonify({"success": False, "message": "No complaints found."})

    try:
        df = load_complaints_df()
        df = df.fillna("")

        for col in ["Discard Reason", "Discarded By", "Discarded At",
                    "Dispute Raised", "Dispute Raised At", "Permanently Closed"]:
            if col not in df.columns:
                df[col] = ""

        df["Reference No"] = df["Reference No"].astype(str)
        mask = df["Reference No"] == ref_no

        if not mask.any():
            return jsonify({"success": False, "message": "Complaint not found."})

        # Department access check
        if admin_dept != "All":
            dept_mask = mask & (df["Department"] == admin_dept)
            if not dept_mask.any():
                return jsonify({"success": False, "message": "Access denied: complaint is not in your department."})
            mask = dept_mask

        current_status = df.loc[mask, "Status"].iloc[0]
        if current_status in ["Discarded by Authority", "Permanently Closed"]:
            return jsonify({"success": False, "message": f"Complaint is already '{current_status}'."})

        if current_status not in ["Submitted", "Processing"]:
            return jsonify({"success": False, "message": "Complaint must be active before an authority action can be taken."})

        df.loc[mask, "Status"] = "Discarded by Authority"
        df.loc[mask, "Discard Reason"] = reason
        df.loc[mask, "Discarded By"] = session['admin_id']
        df.loc[mask, "Discarded At"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        df.loc[mask, "Dispute Raised"] = ""
        df.loc[mask, "Dispute Raised At"] = ""
        df.loc[mask, "Permanently Closed"] = ""

        save_complaints_df(df)
        return jsonify({"success": True, "message": "Complaint discarded successfully."})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


@app.route("/admin/create_admin", methods=["POST"], endpoint="_duplicate_admin_create_admin")
@admin_required
def admin_create_admin():
    """Allow an existing admin to create a new admin account"""
    data = request.get_json()
    new_id = data.get('admin_id', '').strip()
    password = data.get('password', '').strip()
    department = data.get('department', '').strip()

    success, message = create_admin(new_id, password, department, created_by=session['admin_id'])
    return jsonify({"success": success, "message": message})


@app.route("/admin/admins", endpoint="_duplicate_admin_list_admins")
@admin_required
def admin_list_admins():
    """Return list of all admins (for the create-admin modal)"""
    return jsonify({"admins": get_all_admins()})


@app.route("/raise_dispute", methods=["POST"], endpoint="_duplicate_raise_dispute")
@login_required
def raise_dispute():
    """Citizen raises a dispute on a discarded complaint (within 48 hours)"""
    data = request.get_json()
    ref_no = data.get('ref_no', '').strip().upper()
    wallet = session['wallet_address'].lower()

    if not ref_no:
        return jsonify({"success": False, "message": "Reference number required."})

    if load_complaints_df().empty:
        return jsonify({"success": False, "message": "No complaints found."})

    try:
        df = load_complaints_df()
        df = df.fillna("")

        for col in ["Discard Reason", "Discarded By", "Discarded At",
                    "Dispute Raised", "Dispute Raised At", "Permanently Closed"]:
            if col not in df.columns:
                df[col] = ""

        df["Reference No"] = df["Reference No"].astype(str)
        mask = (
            (df["Reference No"] == ref_no) &
            (df["Wallet Address"].str.lower() == wallet)
        )

        if not mask.any():
            return jsonify({"success": False, "message": "Complaint not found or access denied."})

        row = df.loc[mask].iloc[0]

        if str(row.get("Status", "")) != "Discarded by Authority":
            return jsonify({"success": False, "message": "Complaint is not in discarded state."})

        if str(row.get("Permanently Closed", "")) == "Yes":
            return jsonify({"success": False, "message": "Complaint is permanently closed. Dispute window has passed."})

        if str(row.get("Dispute Raised", "")) == "Yes":
            return jsonify({"success": False, "message": "Dispute already raised for this complaint."})

        # Check 48-hour window
        discarded_at_str = str(row.get("Discarded At", ""))
        if not discarded_at_str:
            return jsonify({"success": False, "message": "Discard timestamp missing."})

        try:
            discarded_at = datetime.strptime(discarded_at_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return jsonify({"success": False, "message": "Invalid discard timestamp."})

        elapsed = (datetime.now() - discarded_at).total_seconds()
        if elapsed > 48 * 3600:
            df.loc[mask, "Status"] = "Permanently Closed"
            df.loc[mask, "Permanently Closed"] = "Yes"
            save_complaints_df(df)
            return jsonify({"success": False, "message": "Dispute window of 48 hours has expired. Complaint is permanently closed."})

        # Reopen the complaint
        df.loc[mask, "Status"] = "Processing"
        df.loc[mask, "Dispute Raised"] = "Yes"
        df.loc[mask, "Dispute Raised At"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        save_complaints_df(df)

        return jsonify({"success": True, "message": "Dispute raised successfully. Your complaint has been reopened."})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


# ─────────────────────────────────────────────
if __name__ == "__main__":
    # Create necessary directories
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    os.makedirs('templates', exist_ok=True)
    os.makedirs('contracts', exist_ok=True)

    # Initialize default super admin when MongoDB is available. The app can
    # still serve local complaint history during a temporary database outage.
    try:
        init_default_admin()
    except Exception as error:
        print(f"[WARN] Super admin initialization deferred: {error}")

    # Keep debug mode explicitly opt-in. The Flask auto-reloader launches a
    # second Python process and triggers the Windows/Pandas DLL crash in this
    # project on fresh restarts, so the safe default is disabled.
    allow_debug = os.getenv('ALLOW_FLASK_DEBUG', '0').lower() in {'1', 'true', 'yes', 'on'}
    debug_mode = allow_debug and os.getenv('FLASK_DEBUG', '0').lower() in {'1', 'true', 'yes', 'on'}
    app.run(debug=debug_mode, use_reloader=False, host='0.0.0.0',
            port=int(os.getenv('PORT', '5000')))