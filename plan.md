Rencana Visualisasi Data (Berdasarkan Dataset)

1. Performa Unit & Utilisasi (Pendapatan vs. Hari Terpakai)

Visualisasi: Dual-Axis Chart (Kombinasi Grafik Batang dan Garis).

Metrik Data: Menjumlahkan pemasukan bersih (kolom Total) dalam bentuk batang, dan menjumlahkan durasi sewa (kolom Durasi (Day)) dalam bentuk garis, dikelompokkan berdasarkan Unit (misal: Zenix G, Reborn) selama 6 bulan terakhir.

Insight CRM: Mengidentifikasi armada mana yang memiliki tingkat ROI (Return on Investment) tertinggi dan utilisasi paling padat untuk strategi penambahan/pengurangan aset.

2. Loyalitas Pelanggan (Top Renters)

Visualisasi: Tabel Leaderboard interaktif.

Metrik Data: Menghitung frekuensi kemunculan nama di kolom Penyewa (seberapa sering menyewa) disandingkan dengan total nominal belanja mereka.

Insight CRM: Mengunci daftar VIP (seperti Amin, Jawa Dwipa, dll.) untuk dimasukkan ke dalam program retensi khusus atau prioritas ketersediaan unit.

3. Distribusi Tujuan Perjalanan

Visualisasi: Donut Chart atau Treemap.

Metrik Data: Menghitung total transaksi (Count) untuk setiap kategori di kolom Tujuan.

Insight CRM: Memetakan rute atau destinasi favorit pelanggan. Insight ini bisa diubah menjadi strategi cross-selling dengan menawarkan paket "Include All" khusus untuk rute-rute yang mendominasi grafik.

4. Analisis Retensi & Akuisisi (Time-Series Chart)

Visualisasi: Line Chart (Grafik Garis).

Metrik Data: Membandingkan tren jumlah pelanggan baru (New Customers) dengan pelanggan lama yang bertransaksi kembali (Returning Customers) setiap bulannya. Pelanggan diklasifikasikan sebagai "New" pada bulan transaksi pertamanya, dan "Returning" pada transaksi bulan-bulan berikutnya.

Insight CRM: Mengukur tingkat kesehatan retensi bisnis secara berkelanjutan dan efisiensi biaya pemasaran (CAC).

---

## 🚀 Status Implementasi: SELESAI

Rencana di atas telah diimplementasikan dalam bentuk aplikasi dashboard interaktif menggunakan **Streamlit** dan **Plotly**.

### File Kode:
- **`app.py`**: Berisi pipeline pembersihan data (normalisasi mata uang Rupiah, pengelompokan VIP pelanggan, pembersihan unit) dan visualisasi visual.
- **`.streamlit/config.toml`**: Konfigurasi tema gelap (dark mode) premium bertema *Slate-Dark*.
- **`requirements.txt`**: Daftar dependensi Python.

### Cara Menjalankan Aplikasi:
1. Pastikan Anda berada di direktori project.
2. Jalankan perintah berikut di terminal:
   ```bash
   streamlit run app.py
   ```
3. Dashboard akan terbuka otomatis di browser Anda di `http://localhost:8501`.