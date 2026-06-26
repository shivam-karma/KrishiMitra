"""
FIXED: Transfer Learning with ResNet50 for KrishiMitra.
Avoids the MobileNetV2 'Size must be positive' loading bug.
"""
import os
import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras import layers, Model, Input
from tensorflow.keras.applications import ResNet50
from tensorflow.keras.callbacks import ModelCheckpoint, EarlyStopping, ReduceLROnPlateau

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DATA_DIR  = os.path.join(BASE_DIR, "dataset", "train")
MODEL_OUT = os.path.join(BASE_DIR, "saved_model")

# NOTE: IMG_SIZE must be 128 to match the existing saved_model.
# The saved model was trained with 128x128 input (NOT ResNet50's standard 224).
# If you retrain and change this, change IMG_SIZE in model.py to match.
IMG_SIZE    = 128
BATCH_SIZE  = 16
EPOCHS      = 30
NUM_CLASSES = 3

# ── Data Augmentation ────────────────────────────────────────────────────────
train_datagen = ImageDataGenerator(
    rescale=1./255,
    validation_split=0.2,
    rotation_range=20,
    width_shift_range=0.2,
    height_shift_range=0.2,
    horizontal_flip=True,
    zoom_range=0.2,
)

train_gen = train_datagen.flow_from_directory(
    DATA_DIR,
    target_size=(IMG_SIZE, IMG_SIZE),
    batch_size=BATCH_SIZE,
    class_mode='categorical',
    subset='training',
    shuffle=True,
)

val_gen = train_datagen.flow_from_directory(
    DATA_DIR,
    target_size=(IMG_SIZE, IMG_SIZE),
    batch_size=BATCH_SIZE,
    class_mode='categorical',
    subset='validation',
    shuffle=False,
)

def build_resnet_model(img_size, num_classes):
    base_model = ResNet50(
        input_shape=(img_size, img_size, 3),
        include_top=False,
        weights='imagenet'
    )
    base_model.trainable = False
    
    inputs = Input(shape=(img_size, img_size, 3))
    x = base_model(inputs, training=False)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dense(256, activation='relu')(x)
    x = layers.Dropout(0.3)(x)
    outputs = layers.Dense(num_classes, activation='softmax')(x)
    
    return Model(inputs, outputs)

model = build_resnet_model(IMG_SIZE, NUM_CLASSES)
model.compile(
    optimizer=tf.keras.optimizers.Adam(1e-3),
    loss='categorical_crossentropy',
    metrics=['accuracy'],
)

callbacks = [
    ModelCheckpoint(MODEL_OUT, save_best_only=True, monitor='val_accuracy', verbose=1, save_format='tf'),
    EarlyStopping(patience=8, restore_best_weights=True, monitor='val_accuracy', verbose=1),
    ReduceLROnPlateau(factor=0.2, patience=3, monitor='val_accuracy', verbose=1, min_lr=1e-6),
]

print("\nStarting Training with ResNet50...")
model.fit(
    train_gen,
    validation_data=val_gen,
    epochs=EPOCHS,
    callbacks=callbacks,
)

print(f"\nModel saved: {MODEL_OUT}")
print("Class order:", list(train_gen.class_indices.keys()))
