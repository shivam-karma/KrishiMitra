"""
train_soil_model.py
────────────────────────────────────────────────────────────────
Trains a pure-Python KNN / lookup-based crop recommendation model.
NO sklearn required — works despite numpy version conflicts.

Uses:  soil_dataset.csv  →  N, P, K, ph, moisture, label
Saves: soil_model.pkl (pickled dict with data + class info)
       soil_classes.json

The saved model is used by app.py at runtime for real-time prediction.
"""
import os, json, csv, pickle, math, random

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, 'soil_dataset.csv')
MODEL_OUT = os.path.join(BASE_DIR, 'soil_model.pkl')
CLASS_OUT = os.path.join(BASE_DIR, 'soil_classes.json')

# ── Load Data ─────────────────────────────────────────────────────────────────
print("Loading dataset...")
rows = []
with open(DATA_PATH, newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for r in reader:
        rows.append({
            'x': [float(r['N']), float(r['P']), float(r['K']),
                  float(r['ph']), float(r['moisture'])],
            'y': r['label'].strip()
        })

classes  = sorted(set(r['y'] for r in rows))
n_feat   = 5
n_rows   = len(rows)
print(f"  Rows: {n_rows}  |  Crops ({len(classes)}): {classes}\n")

# ── Compute per-feature Mean & Std for normalization ─────────────────────────
means = [0.0] * n_feat
for r in rows:
    for i in range(n_feat):
        means[i] += r['x'][i]
means = [m / n_rows for m in means]

stds = [0.0] * n_feat
for r in rows:
    for i in range(n_feat):
        stds[i] += (r['x'][i] - means[i]) ** 2
stds = [math.sqrt(s / n_rows) if s > 0 else 1.0 for s in stds]

print(f"  Feature means: {[round(m,2) for m in means]}")
print(f"  Feature stds:  {[round(s,2) for s in stds]}")

def normalize(x):
    return [(x[i] - means[i]) / stds[i] for i in range(n_feat)]

# Normalize all rows
for r in rows:
    r['xn'] = normalize(r['x'])

# ── Train / Test Split (80/20, stratified simple) ─────────────────────────────
random.seed(42)
by_class = {c: [] for c in classes}
for r in rows:
    by_class[r['y']].append(r)

train_data, test_data = [], []
for c, rlist in by_class.items():
    random.shuffle(rlist)
    split = int(len(rlist) * 0.8)
    train_data.extend(rlist[:split])
    test_data.extend(rlist[split:])

print(f"\n  Train: {len(train_data)}  |  Test: {len(test_data)}\n")

# ── KNN Prediction ─────────────────────────────────────────────────────────────
def euclidean(a, b):
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(n_feat)))

def knn_predict(xn, k=7):
    dists = [(euclidean(xn, r['xn']), r['y']) for r in train_data]
    dists.sort(key=lambda x: x[0])
    top_k = dists[:k]
    votes = {}
    for _, label in top_k:
        votes[label] = votes.get(label, 0) + 1
    return max(votes, key=votes.get)

def knn_predict_with_confidence(xn, k=7):
    dists = [(euclidean(xn, r['xn']), r['y']) for r in train_data]
    dists.sort(key=lambda x: x[0])
    top_k = dists[:k]
    votes = {}
    for _, label in top_k:
        votes[label] = votes.get(label, 0) + 1
    best   = max(votes, key=votes.get)
    conf   = votes[best] / k
    # Top 3 alternatives
    ranked = sorted(votes.items(), key=lambda x: -x[1])
    return best, conf, ranked

# ── Evaluate on Test Set ──────────────────────────────────────────────────────
print("Evaluating K=7 KNN on test set...")
correct = 0
class_correct = {c: 0 for c in classes}
class_total   = {c: 0 for c in classes}
for r in test_data:
    pred = knn_predict(r['xn'])
    class_total[r['y']] += 1
    if pred == r['y']:
        correct += 1
        class_correct[r['y']] += 1

acc = correct / len(test_data)
print(f"\n  Test Accuracy: {acc * 100:.1f}%\n")
print(f"  {'Crop':<15} {'Correct':>8} {'Total':>8} {'Acc':>8}")
print(f"  {'-'*45}")
for c in classes:
    tot = class_total[c]
    cor = class_correct[c]
    a   = cor / tot if tot else 0
    print(f"  {c:<15} {cor:>8} {tot:>8} {a*100:>7.0f}%")

# ── Save Model ────────────────────────────────────────────────────────────────
model_bundle = {
    'train_data': train_data,   # list of {x, xn, y} dicts
    'means':      means,
    'stds':       stds,
    'classes':    classes,
    'k':          7,
    'n_feat':     n_feat,
    'accuracy':   round(acc * 100, 1),
}

with open(MODEL_OUT, 'wb') as f:
    pickle.dump(model_bundle, f)

with open(CLASS_OUT, 'w') as f:
    json.dump(classes, f)

print(f"\n✅ Model saved:   {MODEL_OUT}")
print(f"✅ Classes saved: {CLASS_OUT}")
print(f"✅ Accuracy:      {acc * 100:.1f}%")
print("\nDone! Soil crop recommendation model is ready.")
