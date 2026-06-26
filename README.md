<h1 align="center">🌾 KrishiMitra</h1>

<p align="center">
  <strong>An Advanced AI-Powered Agricultural Assistant & P2P Marketplace</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Flutter-Frontend-blue?style=for-the-badge&logo=flutter" alt="Flutter">
  <img src="https://img.shields.io/badge/Flask-Backend-green?style=for-the-badge&logo=flask" alt="Flask">
  <img src="https://img.shields.io/badge/Python-3.10+-yellow?style=for-the-badge&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/TensorFlow-AI%20Models-orange?style=for-the-badge&logo=tensorflow" alt="TensorFlow">
</p>

---

## 📖 About The Project

**KrishiMitra** is a comprehensive mobile/web application designed to empower farmers with modern technology. It bridges the gap between traditional farming and artificial intelligence by providing real-time data, AI-driven disease detection, and a direct peer-to-peer (P2P) marketplace to sell crops without middlemen.


krishimitra-shivam.surge.sh

## ✨ Key Features

- **🔍 AI Crop Disease Detection:** Upload a photo of a diseased plant leaf. The built-in CNN model identifies the disease, generates a Grad-CAM heatmap to show exactly where the infection is, and provides actionable treatment steps.
- **🛒 P2P Crop Marketplace:** Farmers can list their harvested crops directly. Buyers can browse, negotiate via an in-app chat, and purchase crops without intermediary commissions.
- **🌱 Soil Analysis & Recommendations:** Input soil parameters (N, P, K, pH, Moisture) and receive scientifically backed crop recommendations using an integrated K-Nearest Neighbors (KNN) model.
- **🤖 Krishi AI Assistant:** A specialized agricultural chatbot (powered by Groq & LLaMA-3) to answer questions about fertilizers, pesticides, and farming best practices.
- **🌦️ Real-Time Weather & Market Trends:** Fetches localized weather forecasts, extreme weather alerts, and real-time Mandi (market) prices using OpenWeather and Data.gov APIs.

## 🛠️ Technology Stack

### Frontend (`krishimitra_app`)
- **Framework:** Flutter & Dart
- **State Management:** Provider / setState
- **Network:** Dio
- **Authentication:** Firebase Phone Auth

### Backend (`krishimitra_backend`)
- **Framework:** Flask (Python)
- **Database:** SQLite & SQLAlchemy
- **Machine Learning:** TensorFlow / Keras (CNN for image classification), Scikit-Learn (KNN for soil analysis), OpenCV (Grad-CAM heatmaps)
- **APIs:** Groq (LLM), OpenWeather, Data.gov.in (Market Prices)

## 🚀 Deployment & Installation

### Running the Backend Locally
```bash
cd krishimitra_backend
pip install -r requirements.txt
python app.py
```
*(The backend runs on `http://localhost:5000` or your local IPv4 address by default)*

### Running the Frontend Locally
```bash
cd krishimitra_app
flutter pub get
flutter run
```
*(Ensure you update the `baseUrl` in `lib/services/api_service.dart` to point to your backend IP or deployment URL)*

## ☁️ Production Deployment (Free Tier)
- **Frontend (Web):** Compiled via `flutter build web` and hosted on Surge / Vercel.
- **Backend:** Configured via `pythonanywhere_wsgi.py` to be hosted on PythonAnywhere. *(Note: Due to PythonAnywhere's 512MB disk limit, TensorFlow is conditionally disabled in the cloud version to prevent quota crashes, returning mock results instead).*

---
*Built as a Major Academic Project.*
