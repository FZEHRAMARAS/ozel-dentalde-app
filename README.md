# Dentalde Clinic Supabase App

## Streamlit Secrets

```toml
APP_USERNAME = "admin"
APP_PASSWORD = "SIFREN"
SUPABASE_URL = "https://PROJECT_ID.supabase.co"
SUPABASE_KEY = "sb_publishable_xxxxx"
```

## Supabase

Supabase SQL Editor > New query içine `supabase_schema.sql` içeriğini yapıştırıp Run bas.


## Varsayılan Ana Ayarlar

Bu sürümde aşağıdaki ana ayarlar koda sabitlenmiştir ve `ayarlar` tablosundan silinse bile app açılışında otomatik geri eklenir:

- Dr.Dt. M. Enes MARAŞ
- Dt. S. Deniz MARAŞ
- Clinic 1
- Clinic 2
- Planlandı, Geldi, Tamamlandı, İptal, Ertelendi, Ödeme Alındı, Ödeme Bekliyor
- Nakit, Kredi Kartı, Havale/EFT, Parçalı Ödeme
- Laboratuvar, Malzeme, Kira, Personel, Fatura, Diğer
- Laboratuvar 1
- Gönderilecek, Gönderildi, Teslim Alındı, Hastaya Takıldı, İptal
