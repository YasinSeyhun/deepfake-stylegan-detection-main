# 🧠 Deepfake Eğitim Veri Setleri Kaynağı

Projemizi eğitmek için "Fake" ve "Real" etiketli yüzlerce/binlerce fotoğrafa ihtiyacımız var.
İşte en iyi ve ücretsiz kaynaklar:

## 1. En Kolayı: Kaggle (Önerilen) 🏆
Kaggle'da veriler zaten "Real" ve "Fake" diye klasörlenmiş olarak gelir. İndirip klasörlerimize kopyalaman yeterli.

*   **140k Real and Fake Faces:**
    *   **Link:** [Kaggle - 140k Real and Fake Faces](https://www.kaggle.com/datasets/xhlulu/140k-real-and-fake-faces)
    *   **Boyut:** Yaklaşık 3-4 GB
    *   **İçerik:** Flickr (Real) ve StyleGAN (Fake) görüntüleri. Bizim projemiz için mükemmel başlangıç.
    
*   **Deepfake and Real Images:**
    *   **Link:** [Kaggle - Deepfake and Real Images](https://www.kaggle.com/datasets/manjilkarki/deepfake-and-real-images)
    *   **İçerik:** Çeşitli kaynaklardan toplanmış karma veri seti.

## 2. Profesyonel: Celeb-DF (v2)
Akademik kalitede veri setidir. Videolar halindedir, içinden kare (frame) çıkarman gerekebilir ama kalitesi çok yüksektir.
*   **Link:** [Celeb-DF Download](https://github.com/yuezunli/celeb-deepfakeforensics)

## 3. Manuel Toplama (Zor Yöntem)
Eğer hazır indirmek istemezsen:

### FAKE (Sahte) Kaynakları:
*   **ThisPersonDoesNotExist.com:** Bu site her yenilendiğinde yapay zeka ile **olmayan** bir insan yüzü üretir. Buradan 100-200 tane indirebilirsin.

### REAL (Gerçek) Kaynakları:
*   **CelebA Dataset:** [Mala Dataset](http://mmlab.ie.cuhk.edu.hk/projects/CelebA.html)
*   **Kendi Fotoğrafların:** Kendi galerinden veya arkadaşlarından insan yüzü fotoğrafları.
*   **Unsplash / Pexels:** "Portrait" veya "Human Face" araması yapıp indirebilirsin.

---

## 🚀 Nasıl Kuracaksın?

1.  Yukarıdaki Kaggle linklerinden (özellikle 140k olanı) indir.
2.  Zip dosyasını aç.
3.  İçindeki `real` klasöründeki fotoları -> `dataset/train/real` içine at.
4.  İçindeki `fake` klasöründeki fotoları -> `dataset/train/fake` içine at.
