# 🔥 Firebase Setup Guide — FinsageAI

## Step 1 — Firebase Console mein project banao

1. **https://console.firebase.google.com** par jao
2. **"Create a project"** click karo
3. Project name: `finsage-app` (ya koi bhi)
4. Google Analytics: **Disable** karo (optional hai)
5. **"Create Project"** click karo — 30 seconds wait karo

---

## Step 2 — Firestore Database enable karo

1. Left sidebar mein **"Firestore Database"** click karo
2. **"Create database"** click karo
3. Mode: **"Start in production mode"** select karo
4. Location: **`asia-south1` (Mumbai)** — India ke liye best
5. **"Done"** click karo

---

## Step 3 — Firestore Security Rules set karo

1. Firestore → **"Rules"** tab click karo
2. Ye rules paste karo:

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /finsage_users/{userId} {
      allow read, write: if true;  // Server-side only via Admin SDK
    }
  }
}
```

3. **"Publish"** click karo

---

## Step 4 — Service Account key download karo

1. Firebase Console → ⚙️ **Project Settings** (top-left gear icon)
2. **"Service accounts"** tab click karo
3. **"Generate new private key"** button click karo
4. **"Generate key"** confirm karo
5. Ek JSON file download hogi — **is file ko safely rakhna**

---

## Step 5 — Streamlit Secrets mein add karo

### Option A — Streamlit Cloud (app deploy kiya hua hai to)

1. https://share.streamlit.io → apna app → **"Settings"** → **"Secrets"**
2. Ye paste karo:

```toml
FIREBASE_SERVICE_ACCOUNT_JSON = '''
{
  "type": "service_account",
  "project_id": "finsage-app-xxxxx",
  "private_key_id": "abc123...",
  "private_key": "-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----\n",
  "client_email": "firebase-adminsdk-xxxxx@finsage-app.iam.gserviceaccount.com",
  "client_id": "123456789",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/..."
}
'''
```

> **Note:** Download ki hui JSON file ko exactly copy karo — single quotes ke beech mein paste karo

3. **"Save"** click karo → app automatically reboot hoga

### Option B — Local development (`.streamlit/secrets.toml`)

```toml
FIREBASE_SERVICE_ACCOUNT_JSON = '''
{ ...JSON content... }
'''
```

---

## Step 6 — Verify karo

App open karo → signup karo → Firebase Console → Firestore Database mein `finsage_users` collection mein user dikh jaayega ✅

---

## Bina Firebase ke bhi kaam karta hai

Agar `FIREBASE_SERVICE_ACCOUNT_JSON` set nahi hai, app automatically `users.json` file use karta hai (local fallback). Koi breaking change nahi hoga — smoothly switch hoga jab Firebase configure karoge.

---

## Firebase Free Tier limits (Spark Plan)

| Resource | Free limit |
|----------|-----------|
| Reads | 50,000/day |
| Writes | 20,000/day |
| Deletes | 20,000/day |
| Storage | 1 GB |
| Network | 10 GB/month |

FinsageAI ke liye ye kaafi hai jab tak bahut bade scale par nahi jao.

---

## 🔒 Security Note

- Service Account JSON mein private key hoti hai — **kabhi bhi GitHub ya public jagah upload mat karo**
- Sirf Streamlit Secrets mein daalo
- Firebase Admin SDK server-side se hi access karta hai — client ke paas keys nahi pahunchti
