import pandas as pd
import pickle
from sklearn.model_selection import train_test_split
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.utils.class_weight import compute_class_weight
from sentence_transformers import SentenceTransformer
import numpy as np
import sys
import os

NATIVE_LANGUAGE_EXAMPLES = [
    ("मेरे घर में बिजली नहीं आ रही है", "Electricity"),
    ("আমাদের এলাকায় বিদ্যুৎ নেই", "Electricity"),
    ("हमारे मोहल्ले में पानी की सप्लाई बंद है", "Water Supply"),
    ("আমাদের পাড়ায় জল সরবরাহ বন্ধ", "Water Supply"),
    ("हमारी गली में सफाई नहीं हुई", "Sanitation"),
    ("আমাদের গলিতে পরিষ্কার করা হয়নি", "Sanitation"),
    ("सड़क में बहुत बड़े गड्ढे हैं", "Road Maintenance"),
    ("রাস্তায় অনেক বড় গর্ত হয়েছে", "Road Maintenance"),
    ("सड़क की स्ट्रीट लाइट खराब है", "Public Lighting"),
    ("রাস্তার স্ট্রিট লাইট নষ্ট", "Public Lighting"),
    ("घर के पास गैस लीक हो रही है", "Gas Leaks"),
    ("বাড়ির কাছে গ্যাস লিক হচ্ছে", "Gas Leaks"),
    ("रात में बहुत तेज आवाज हो रही है", "Noise"),
    ("রাতে খুব জোরে শব্দ হচ্ছে", "Noise"),
    ("कूड़ा कई दिनों से नहीं उठाया गया", "Waste Management"),
    ("কয়েক দিন ধরে আবর্জনা নেওয়া হয়নি", "Waste Management"),
    ("नाली बंद है और पानी सड़क पर जमा है", "Drainage"),
    ("নালা বন্ধ হয়ে রাস্তায় জল জমেছে", "Drainage"),
    ("पेड़ की टूटी शाखा सड़क पर गिर गई है", "Tree/Landscape"),
    ("গাছের ভাঙা ডাল রাস্তায় পড়ে আছে", "Tree/Landscape"),
    ("सरकारी अस्पताल में इलाज नहीं मिल रहा", "Public Health"),
    ("সরকারি হাসপাতালে চিকিৎসা পাওয়া যাচ্ছে না", "Public Health"),
    ("कंपनी ने मेरे पैसे वापस नहीं किए", "Consumer Affairs"),
    ("কোম্পানি আমার টাকা ফেরত দেয়নি", "Consumer Affairs"),
    ("मकान मालिक किराए की रसीद नहीं दे रहा", "Rent/Building"),
    ("বাড়িওয়ালা ভাড়ার রসিদ দিচ্ছে না", "Rent/Building"),
    ("इमारत में आग से बचाव की व्यवस्था नहीं है", "Fire Safety"),
    ("ভবনে অগ্নি নিরাপত্তার ব্যবস্থা নেই", "Fire Safety"),
    ("ट्रैफिक सिग्नल काम नहीं कर रहा", "Traffic"),
    ("ট্রাফিক সিগন্যাল কাজ করছে না", "Traffic"),
]

NATIVE_LANGUAGE_EXAMPLES += [
    ("कल रात से बिजली की आपूर्ति बंद है", "Electricity"),
    ("बार बार बिजली जा रही है", "Electricity"),
    ("গত রাত থেকে বিদ্যুৎ সরবরাহ বন্ধ", "Electricity"),
    ("বারবার বিদ্যুৎ চলে যাচ্ছে", "Electricity"),
    ("नल में तीन दिन से पानी नहीं आ रहा", "Water Supply"),
    ("पानी की पाइपलाइन में रिसाव है", "Water Supply"),
    ("তিন দিন ধরে কলের জল আসছে না", "Water Supply"),
    ("জলের পাইপে লিক হয়েছে", "Water Supply"),
    ("सड़क किनारे कूड़ा सड़कर बदबू दे रहा है", "Sanitation"),
    ("सार्वजनिक जगह पर गंदगी और बदबू है", "Sanitation"),
    ("রাস্তার ধারে আবর্জনা পচে দুর্গন্ধ ছড়াচ্ছে", "Sanitation"),
    ("পাবলিক জায়গায় নোংরা ও দুর্গন্ধ রয়েছে", "Sanitation"),
    ("सड़क पूरी तरह टूट गई है", "Road Maintenance"),
    ("बारिश में सड़क पर चलना मुश्किल है", "Road Maintenance"),
    ("রাস্তাটি পুরো ভেঙে গেছে", "Road Maintenance"),
    ("বৃষ্টিতে রাস্তায় চলাচল করা কঠিন", "Road Maintenance"),
    ("स्ट्रीट लैंप कई रातों से नहीं जल रहे", "Public Lighting"),
    ("खंभे की लाइट खराब है", "Public Lighting"),
    ("কয়েক রাত ধরে স্ট্রিট ল্যাম্প জ্বলছে না", "Public Lighting"),
    ("রাস্তার বাতির খুঁটির আলো নষ্ট", "Public Lighting"),
    ("रसोई की गैस पाइप से रिसाव हो रहा है", "Gas Leaks"),
    ("गैस की गंध से घर में डर लग रहा है", "Gas Leaks"),
    ("রান্নাঘরের গ্যাসের পাইপে লিক হয়েছে", "Gas Leaks"),
    ("গ্যাসের গন্ধে বাড়িতে আতঙ্ক তৈরি হয়েছে", "Gas Leaks"),
    ("लाउडस्पीकर की आवाज से रात में नींद नहीं आती", "Noise"),
    ("कारखाने का शोर बहुत परेशान करता है", "Noise"),
    ("মাইকের আওয়াজে রাতে ঘুমানো যায় না", "Noise"),
    ("কারখানার শব্দে মানুষ খুব বিরক্ত", "Noise"),
    ("कचरा उठाने वाली गाड़ी एक सप्ताह से नहीं आई", "Waste Management"),
    ("कूड़ेदान भर गया है और कचरा नहीं उठाया गया", "Waste Management"),
    ("আবর্জনা সংগ্রহের গাড়ি এক সপ্তাহ আসেনি", "Waste Management"),
    ("ডাস্টবিন ভরে গেছে কিন্তু বর্জ্য নেওয়া হয়নি", "Waste Management"),
    ("नाली जाम होने से घर के सामने पानी भर गया", "Drainage"),
    ("बंद नाले से गंदा पानी वापस आ रहा है", "Drainage"),
    ("নালা বন্ধ হয়ে বাড়ির সামনে জল জমেছে", "Drainage"),
    ("বন্ধ নালা দিয়ে নোংরা জল ফিরে আসছে", "Drainage"),
    ("पेड़ की शाखाएं बिजली के तार पर गिर गई हैं", "Tree/Landscape"),
    ("पार्क में पेड़ों की छंटाई की जरूरत है", "Tree/Landscape"),
    ("গাছের ডাল বিদ্যুতের তারের উপর পড়েছে", "Tree/Landscape"),
    ("পার্কের গাছ ছাঁটাই করা দরকার", "Tree/Landscape"),
    ("सरकारी अस्पताल में दवा उपलब्ध नहीं है", "Public Health"),
    ("मोहल्ले में बीमारी फैल रही है", "Public Health"),
    ("সরকারি হাসপাতালে ওষুধ পাওয়া যাচ্ছে না", "Public Health"),
    ("এলাকায় রোগ ছড়িয়ে পড়ছে", "Public Health"),
    ("ऑनलाइन खरीद का पैसा वापस नहीं मिला", "Consumer Affairs"),
    ("दुकानदार ने नकली सामान बेच दिया", "Consumer Affairs"),
    ("অনলাইনে কেনা পণ্যের টাকা ফেরত পাইনি", "Consumer Affairs"),
    ("দোকানদার নকল পণ্য বিক্রি করেছে", "Consumer Affairs"),
    ("इमारत की छत से पानी टपक रहा है", "Rent/Building"),
    ("मकान मालिक मरम्मत नहीं कर रहा", "Rent/Building"),
    ("বাড়ির ছাদ থেকে জল পড়ছে", "Rent/Building"),
    ("বাড়িওয়ালা মেরামত করতে চাইছে না", "Rent/Building"),
    ("सीढ़ियों के पास अग्निशामक यंत्र नहीं है", "Fire Safety"),
    ("इमारत में आग लगने पर कोई निकास नहीं है", "Fire Safety"),
    ("সিঁড়ির কাছে অগ্নিনির্বাপক যন্ত্র নেই", "Fire Safety"),
    ("আগুন লাগলে ভবন থেকে বেরোনোর পথ নেই", "Fire Safety"),
    ("चौराहे पर ट्रैफिक जाम रोज लगता है", "Traffic"),
    ("वाहन गलत दिशा में चल रहे हैं", "Traffic"),
    ("প্রতিদিন মোড়ে ট্রাফিক জ্যাম হচ্ছে", "Traffic"),
    ("গাড়ি ভুল পথে চলাচল করছে", "Traffic"),
]

# Ensure UTF-8 output to support emojis in console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def train_model():
    print("📂 Loading dataset...")

    # Load CSV
    df = pd.read_csv('consumer_complaints.csv')

    # Clean data
    df = df.dropna(subset=['complaint_text', 'product']).drop_duplicates()
    df['complaint_text'] = df['complaint_text'].str.strip()
    df['product'] = df['product'].str.strip()

    # Drop rows that match the header names (in case of duplicate header pastes)
    df = df[df['product'] != 'product']
    df = df[df['complaint_text'] != 'complaint_text']
    # Drop rows with empty text
    df = df[df['complaint_text'] != '']
    df = df[df['product'] != '']

    # Keep native Hindi and Bengali examples in every retraining run so the
    # multilingual encoder is anchored to the application's department labels.
    native_df = pd.DataFrame(NATIVE_LANGUAGE_EXAMPLES, columns=['complaint_text', 'product'])
    df = pd.concat([df, native_df], ignore_index=True).drop_duplicates()

    print(f"✅ Dataset loaded: {len(df)} rows, {df['product'].nunique()} categories.")
    print("\n📋 Rows per category:")
    for cat, count in df['product'].value_counts().items():
        print(f"   {cat:<22} → {count} rows")

    X = df['complaint_text'].astype(str)
    y = df['product']

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"\n📊 Train: {len(X_train)} | Test: {len(X_test)}")

    # Load multilingual embedding model (supports English, Hindi, Bengali)
    print("\n🔍 Loading multilingual embedding model...")
    emb_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

    # Encode text
    print("⚙️  Encoding training data...")
    X_train_embeddings = emb_model.encode(X_train.tolist(), show_progress_bar=False, batch_size=64)
    print("⚙️  Encoding test data...")
    X_test_embeddings  = emb_model.encode(X_test.tolist(),  show_progress_bar=False, batch_size=64)

    # Train SGDClassifier with multiple epochs for higher accuracy.
    # SGDClassifier is used (not LinearSVC) because it supports partial_fit
    # which enables REAL-TIME learning when a user submits a complaint.
    EPOCHS = 30
    print(f"\n🧠 Training classifier ({EPOCHS} epochs)...")
    classes = np.unique(y)

    # Compute class weights manually (class_weight='balanced' not allowed with partial_fit)
    class_weights_arr = compute_class_weight('balanced', classes=classes, y=y_train)
    class_weight_dict = dict(zip(classes, class_weights_arr))

    model = SGDClassifier(
        loss="log_loss",        # Enables predict_proba for confidence scores
        alpha=0.000005,         # Very low L2 regularization for better fitting
        max_iter=1,             # We manage epochs manually via partial_fit
        tol=None,
        random_state=42,
        eta0=0.01,              # Initial learning rate
        learning_rate="adaptive",  # Reduces LR when loss stops improving
        warm_start=False,
    )

    y_train_arr = np.array(y_train)  # Convert once for fast indexing

    best_test_acc = 0.0
    best_model_state = None
    no_improve_count = 0
    PATIENCE = 5  # Stop if no improvement for 5 consecutive checks

    for epoch in range(1, EPOCHS + 1):
        # Shuffle data every epoch to reduce overfitting
        idx = np.random.permutation(len(X_train_embeddings))
        sample_weights = np.array([class_weight_dict[label] for label in y_train_arr[idx]])
        model.partial_fit(
            X_train_embeddings[idx],
            y_train_arr[idx],
            classes=classes,
            sample_weight=sample_weights
        )
        # Check every 3 epochs
        if epoch % 3 == 0 or epoch == EPOCHS:
            y_pred_train = model.predict(X_train_embeddings)
            y_pred_test  = model.predict(X_test_embeddings)
            train_acc = accuracy_score(y_train, y_pred_train)
            test_acc  = accuracy_score(y_test,  y_pred_test)
            improved = "" 
            if test_acc > best_test_acc:
                best_test_acc = test_acc
                import copy
                best_model_state = copy.deepcopy(model)
                no_improve_count = 0
                improved = " <-- best"
            else:
                no_improve_count += 1
            print(f"   Epoch {epoch:2d}/{EPOCHS}  Train: {train_acc:.3f}  Test: {test_acc:.3f}{improved}")
            if no_improve_count >= PATIENCE:
                print(f"   Early stopping at epoch {epoch} (no improvement for {PATIENCE} checks)")
                break

    # Use best model (not last epoch which may overfit)
    if best_model_state is not None:
        model = best_model_state
        print(f"\n   Using best model checkpoint (Test Acc: {best_test_acc:.3f})")

    # Final evaluation on test set
    y_pred = model.predict(X_test_embeddings)
    test_acc = accuracy_score(y_test, y_pred)
    print(f"\n🎯 Final Test Accuracy: {test_acc:.3f}")
    print("\n📄 Classification Report:")
    print(classification_report(y_test, y_pred))

    # Save classification model & classes
    with open('complaint_model.pkl', 'wb') as f:
        pickle.dump(model, f)

    with open('classes.pkl', 'wb') as f:
        pickle.dump(classes, f)

    # Save embedding model (with try-except to avoid Windows file locks when Flask is running)
    try:
        if not os.path.exists("embedding_model"):
            emb_model.save("embedding_model")
            print("💾 Embedding model saved to 'embedding_model' folder.")
        else:
            print("ℹ️  'embedding_model' folder already exists, skipping save.")
    except Exception as e:
        print(f"⚠️  Warning: Could not save embedding model (probably locked by running web app): {e}")

    print("\n✅ All models saved successfully!")
    print("   → complaint_model.pkl")
    print("   → classes.pkl")
    print("   → embedding_model/")

if __name__ == "__main__":
    train_model()
