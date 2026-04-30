
# Özel Dentalde Mobil Uyumlu Klinik Sistemi

## Kurulum

```bash
cd ~/Downloads/ozel_dental_mobil
python3 -m pip install -r requirements.txt
python3 -m streamlit run app.py
```

## Mobil Kullanım
Tarayıcıdan:
http://localhost:8501

Aynı ağda telefon:
http://BILGISAYAR-IP:8501


## Streamlit Cloud Secrets

App settings > Secrets içine şunu ekle:

```toml
APP_USERNAME = "admin"
APP_PASSWORD = "BURAYA_GUCLU_SIFRE_YAZ"
```

Not: Hasta verisi için bir sonraki adım Supabase PostgreSQL'e geçiştir.
