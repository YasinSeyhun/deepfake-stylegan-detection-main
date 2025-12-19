import os

def create_structure():
    root = "dataset"
    paths = [
        "dataset/train/real",
        "dataset/train/fake",
        "dataset/val/real",
        "dataset/val/fake"
    ]
    
    print(f"📁 Creating dataset structure in '{os.getcwd()}'...\n")
    
    for p in paths:
        try:
            os.makedirs(p, exist_ok=True)
            print(f"✅ Created: {p}")
        except Exception as e:
            print(f"❌ Error creating {p}: {e}")
            
    print("\n" + "="*50)
    print("SENDING INSTRUCTIONS:")
    print("1. Download a dataset (see DATA_SOURCES.md).")
    print("2. Unzip/Extract it.")
    print("3. Copy 'Real' face images into -> dataset/train/real/")
    print("4. Copy 'Fake/Deepfake' images into -> dataset/train/fake/")
    print("5. (Optional) Put some test images into -> dataset/val/...")
    print("="*50)

if __name__ == "__main__":
    create_structure()
