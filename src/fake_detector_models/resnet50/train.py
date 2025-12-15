import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, ConcatDataset
from torchvision import datasets, transforms
from torch.utils.tensorboard import SummaryWriter
from tqdm import tqdm
import numpy as np
from detector import get_resnet50_detector
import argparse

# Klasör yolları
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'processed')
REAL_DIR = os.path.join(DATA_DIR, 'real')
FAKE_DIR = os.path.join(DATA_DIR, 'fake')
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'runs', 'detector_train')
CHECKPOINT_PATH = os.path.join(os.path.dirname(__file__), 'detector_best.pth')

# Transformlar
train_transforms = transforms.Compose([
    transforms.RandomResizedCrop(224),
    transforms.RandomHorizontalFlip(),
    transforms.RandomVerticalFlip(),
    transforms.ColorJitter(brightness=0.4, contrast=0.4, saturation=0.4, hue=0.2),
    transforms.RandomRotation(degrees=20),
    transforms.RandomAffine(degrees=0, translate=(0.1, 0.1), scale=(0.9, 1.1), shear=10),
    transforms.ToTensor(),
    transforms.RandomErasing(p=0.3, scale=(0.02, 0.2), ratio=(0.3, 3.3)),
    transforms.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5])
])
val_test_transforms = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5])
])

def get_datasets():
    datasets_dict = {}
    for split, tfm in zip(['train', 'val', 'test'], [train_transforms, val_test_transforms, val_test_transforms]):
        split_dir = os.path.join(DATA_DIR, split)
        datasets_dict[split] = datasets.ImageFolder(split_dir, transform=tfm)
    return datasets_dict

def train(resume=False):
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    datasets_dict = get_datasets()
    train_loader = DataLoader(datasets_dict['train'], batch_size=32, shuffle=True, num_workers=2)
    val_loader = DataLoader(datasets_dict['val'], batch_size=32, shuffle=False, num_workers=2)
    test_loader = DataLoader(datasets_dict['test'], batch_size=32, shuffle=False, num_workers=2)

    model = get_resnet50_detector(pretrained=True).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=1e-4)
    writer = SummaryWriter(LOG_DIR)

    best_val_acc = 0
    patience = 5
    patience_counter = 0
    num_epochs = 30
    start_epoch = 0

    # Resume from checkpoint
    if resume and os.path.exists(CHECKPOINT_PATH):
        checkpoint = torch.load(CHECKPOINT_PATH)
        model.load_state_dict(checkpoint['model_state_dict']) if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint else model.load_state_dict(checkpoint)
        if isinstance(checkpoint, dict) and 'optimizer_state_dict' in checkpoint:
            optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
            start_epoch = checkpoint.get('epoch', 0)
            best_val_acc = checkpoint.get('best_val_acc', 0)
        print(f"[Resume] Eğitim {start_epoch}. epoch ve Val Acc={best_val_acc:.4f} ({best_val_acc*100:.2f}%) ile devam ediyor.")

    for epoch in range(start_epoch, num_epochs):
        model.train()
        train_loss, train_correct, train_total = 0, 0, 0
        for imgs, labels in tqdm(train_loader, desc=f"Epoch {epoch+1}/{num_epochs} [Train]"):
            imgs, labels = imgs.to(device), labels.to(device)
            optimizer.zero_grad()
            outputs = model(imgs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            train_loss += loss.item() * imgs.size(0)
            preds = outputs.argmax(dim=1)
            train_correct += (preds == labels).sum().item()
            train_total += imgs.size(0)
        train_acc = train_correct / train_total
        train_loss /= train_total
        writer.add_scalar('Loss/train', train_loss, epoch)
        writer.add_scalar('Accuracy/train', train_acc, epoch)

        # Validation
        model.eval()
        val_loss, val_correct, val_total = 0, 0, 0
        with torch.no_grad():
            for imgs, labels in tqdm(val_loader, desc=f"Epoch {epoch+1}/{num_epochs} [Val]"):
                imgs, labels = imgs.to(device), labels.to(device)
                outputs = model(imgs)
                loss = criterion(outputs, labels)
                val_loss += loss.item() * imgs.size(0)
                preds = outputs.argmax(dim=1)
                val_correct += (preds == labels).sum().item()
                val_total += imgs.size(0)
        val_acc = val_correct / val_total
        val_loss /= val_total
        writer.add_scalar('Loss/val', val_loss, epoch)
        writer.add_scalar('Accuracy/val', val_acc, epoch)

        print(f"Epoch {epoch+1}: Train Loss={train_loss:.4f}, Train Acc={train_acc:.4f} ({train_acc*100:.2f}%), Val Loss={val_loss:.4f}, Val Acc={val_acc:.4f} ({val_acc*100:.2f}%)")
        print(f"[INFO] Epoch {epoch+1} - Başarı Oranı: Train={train_acc*100:.2f}%, Val={val_acc*100:.2f}%")

        # Early stopping & checkpoint
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            patience_counter = 0
            torch.save({
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'epoch': epoch+1,
                'best_val_acc': best_val_acc
            }, CHECKPOINT_PATH)
            print(f"[Checkpoint] Yeni en iyi model kaydedildi! Val Acc={val_acc:.4f} ({val_acc*100:.2f}%)")
        else:
            patience_counter += 1
            if patience_counter >= patience:
                print("[Early Stopping] Val accuracy iyileşmedi, eğitim durduruluyor.")
                break

    writer.close()
    print("Eğitim tamamlandı. En iyi model kaydedildi.")

    # Test
    checkpoint = torch.load(CHECKPOINT_PATH)
    model.load_state_dict(checkpoint['model_state_dict']) if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint else model.load_state_dict(checkpoint)
    model.eval()
    test_correct, test_total = 0, 0
    all_preds, all_labels = [], []
    with torch.no_grad():
        for imgs, labels in tqdm(test_loader, desc="[Test]"):
            imgs, labels = imgs.to(device), labels.to(device)
            outputs = model(imgs)
            preds = outputs.argmax(dim=1)
            test_correct += (preds == labels).sum().item()
            test_total += imgs.size(0)
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())
    test_acc = test_correct / test_total
    print(f"Test Accuracy: {test_acc:.4f} ({test_acc*100:.2f}%)")

    # Ekstra: Precision, Recall, F1-score, Confusion Matrix
    try:
        from sklearn.metrics import classification_report, confusion_matrix
        print(classification_report(all_labels, all_preds, target_names=['real', 'fake'], labels=[0,1]))
        print("Confusion Matrix:\n", confusion_matrix(all_labels, all_preds))
    except ImportError:
        print("scikit-learn yüklü değil, ek metrikler gösterilemiyor.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--resume', action='store_true', help='Kaldığı yerden devam et')
    args = parser.parse_args()
    train(resume=args.resume) 