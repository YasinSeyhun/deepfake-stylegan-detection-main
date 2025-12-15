import warnings
warnings.filterwarnings("ignore")
import os
import sys
sys.path.append(os.path.dirname(__file__))  # src/data içindeki modüller için
import numpy as np
import torch
from PIL import Image
from tqdm import tqdm
import time

from torch.utils.tensorboard import SummaryWriter


# StyleGAN2 ağırlık dosyası yolu
MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'models', 'stylegan2-ffhq-config-f.pkl')

# Çıktı klasörleri
FAKE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'processed', 'fake')
TRAIN_DIR = os.path.join(FAKE_DIR, 'train')
VAL_DIR = os.path.join(FAKE_DIR, 'val')
TEST_DIR = os.path.join(FAKE_DIR, 'test')

os.makedirs(TRAIN_DIR, exist_ok=True)
os.makedirs(VAL_DIR, exist_ok=True)
os.makedirs(TEST_DIR, exist_ok=True)

# Her split için üretilecek görsel sayısı
NUM_IMAGES = {
    'train': 1000,
    'val': 100,
    'test': 100
}

# TensorBoard log klasörü
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'runs', 'fake_generation')

# StyleGAN2 ağırlığını yüklemek için yardımcı fonksiyon
def load_stylegan2_generator(model_path):
    import pickle
    import dnnlib
    import legacy
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    with open(model_path, 'rb') as f:
        G = legacy.load_network_pkl(f)['G_ema'].to(device)
    G.eval()
    return G

# Görsel üretme fonksiyonu
def generate_and_save_images(G, num_images, out_dir, writer, split_name, seed_start=0):
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    G = G.to(device)
    success_count = 0
    error_count = 0
    total_time = 0
    example_images = []
    for i in tqdm(range(num_images), desc=f'Generating in {out_dir}'):
        start_time = time.time()
        try:
            z = torch.from_numpy(np.random.randn(1, G.z_dim)).to(device)
            img = G(z, None)
            img = (img.clamp(-1, 1) + 1) / 2.0  # [-1,1] -> [0,1]
            img = img.mul(255).add_(0.5).clamp_(0, 255).to(torch.uint8)
            img_np = img[0].permute(1, 2, 0).cpu().numpy()
            im = Image.fromarray(img_np)
            save_path = os.path.join(out_dir, f'fake_{i+seed_start:05d}.png')
            im.save(save_path)
            success_count += 1
            # İlk 5 görseli TensorBoard'a ekle
            if i < 5:
                img_tb = torch.from_numpy(img_np).permute(2, 0, 1).unsqueeze(0).float() / 255.0
                example_images.append(img_tb)
        except Exception as e:
            print(f"Error at {i}: {e}")
            error_count += 1
        total_time += (time.time() - start_time)
    avg_time = total_time / max(success_count, 1)
    # TensorBoard'a metrikleri logla
    writer.add_scalar(f'{split_name}/success_count', success_count)
    writer.add_scalar(f'{split_name}/error_count', error_count)
    writer.add_scalar(f'{split_name}/total_time_sec', total_time)
    writer.add_scalar(f'{split_name}/avg_time_per_image_sec', avg_time)
    if example_images:
        example_images = torch.cat(example_images, dim=0)
        writer.add_images(f'{split_name}/examples', example_images, global_step=0)
    print(f"{split_name}: Success={success_count}, Error={error_count}, AvgTime={avg_time:.3f}s")

if __name__ == '__main__':
    writer = SummaryWriter(LOG_DIR)
    G = load_stylegan2_generator(MODEL_PATH)
    generate_and_save_images(G, NUM_IMAGES['train'], TRAIN_DIR, writer, 'train', seed_start=0)
    generate_and_save_images(G, NUM_IMAGES['val'], VAL_DIR, writer, 'val', seed_start=NUM_IMAGES['train'])
    generate_and_save_images(G, NUM_IMAGES['test'], TEST_DIR, writer, 'test', seed_start=NUM_IMAGES['train']+NUM_IMAGES['val'])
    writer.close()
    print('Fake face generation completed and logged to TensorBoard!') 