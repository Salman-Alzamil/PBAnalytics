import os
import shutil
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter
import random
import math


# Config

SOURCE_DIR = 'raw_images/'
OUTPUT_DIR = 'dataset/'
IMAGE_SIZE = (224, 224)
SPLIT      = (0.70, 0.20, 0.10)  # Train, Val, Test percentages
AUGMENT_MULTIPLIER = 3
SEED       = 42

CLASSES = ['saudi_formal', 'casual', 'not_human']

random.seed(SEED)


# Preprocessing

def preprocess(img: Image.Image) -> Image.Image:
    """
    Standarize every image before anything else:
    - Convert to RGB (handles PNG with alpha, grayscale, etc.)
    - Resize to 224x224 using LANCZOS for quality
    """
    img = img.convert('RGB')
    img = img.resize(IMAGE_SIZE, Image.LANCZOS)
    return img

# Augmentation

def augment(img: Image.Image) -> Image.Image:
    """
    Randomly applies a combination of transformations.
    Each call produces a different result, genuine variety per epoch.
    """
    # horizontal flip
    if random.random() > 0.5:
        img = img.transpose(Image.FLIP_LEFT_RIGHT)

    # Random rotation
    angle = random.uniform(-15, 15)
    img = img.rotate(angle, expand=False, fillcolor=(128, 128, 128))

    # Random brightness
    brightness_factor = random.uniform(0.7, 1.3)
    img = ImageEnhance.Brightness(img).enhance(brightness_factor)

    # Random contrast
    contrast_factor = random.uniform(0.8, 1.2)
    img = ImageEnhance.Contrast(img).enhance(contrast_factor)

    # Random blur
    if random.random() > 0.7:
        img = img.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.5, 1.5)))

    # Random crop
    if random.random() > 0.5:
        w, h = img.size
        left = random.randint(0, int(w * 0.2))
        top = random.randint(0, int(h * 0.2))
        right = w - random.randint(0, int(w * 0.2))
        bottom = h - random.randint(0, int(h * 0.2))
        img = img.crop((left, top, right, bottom))
        img = img.resize(IMAGE_SIZE, Image.LANCZOS)
    return img

# Split & Save

def build_dataset():
    for split in ['train', 'valid', 'test']:
        for cls in CLASSES:
            Path(f'{OUTPUT_DIR}/{split}/{cls}').mkdir(parents=True, exist_ok=True)

    for cls in CLASSES:
        source_path = Path(f'{SOURCE_DIR}/{cls}')
        images = [f for f in source_path.iterdir()
                  if f.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp'}
                  and f.is_file()]

        random.shuffle(images)

        total      = len(images)
        train_end  = math.floor(total * SPLIT[0])
        valid_end  = train_end + math.floor(total * SPLIT[1])

        splits = {
            'train': images[:train_end],
            'valid': images[train_end:valid_end],
            'test':  images[valid_end:]
        }
        print(f"\n{cls}:")
        for split_name, split_images in splits.items():
            print(f"  {split_name}: {len(split_images)} images to process")
            for idx, img_path in enumerate(split_images):
                try:
                    img = Image.open(img_path)
                    img = preprocess(img)
                    save_path = Path(f'{OUTPUT_DIR}/{split_name}/{cls}/{idx:04d}_orig.jpg')
                    img.save(str(save_path), quality=95)

                    if split_name == 'train':
                        for aug_idx in range(AUGMENT_MULTIPLIER):
                            aug_img  = augment(img)
                            aug_path = Path(f'{OUTPUT_DIR}/{split_name}/{cls}/{idx:04d}_aug{aug_idx}.jpg')
                            aug_img.save(str(aug_path), quality=95)

                except Exception as e:
                    print(f"  ERROR on {img_path.name}: {e}")
                    continue

            saved = len(list(Path(f'{OUTPUT_DIR}/{split_name}/{cls}').glob('*.jpg')))
            print(f"  {split_name} saved: {saved}")

    total_train = sum(len(list(Path(f'{OUTPUT_DIR}/train/{cls}').glob('*.jpg'))) for cls in CLASSES)
    total_valid = sum(len(list(Path(f'{OUTPUT_DIR}/valid/{cls}').glob('*.jpg'))) for cls in CLASSES)
    total_test  = sum(len(list(Path(f'{OUTPUT_DIR}/test/{cls}').glob('*.jpg'))) for cls in CLASSES)
    print(f"\nTotal — train: {total_train}, valid: {total_valid}, test: {total_test}")


# Run
if __name__ == "__main__":
    print("Starting preprocessing and augmentation...")
    build_dataset()
    print(f"\nDone. Dataset ready at: {OUTPUT_DIR}")
