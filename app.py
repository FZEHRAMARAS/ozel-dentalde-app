
import base64
from datetime import date, datetime, timedelta, time

import pandas as pd
import streamlit as st
from supabase import create_client

st.set_page_config(page_title="Dentalde Clinic", page_icon="🦷", layout="wide", initial_sidebar_state="expanded")

# ---------------- STYLE ----------------
st.markdown("""
<style>
.stApp { background: #fafcf5; }
.block-container { padding-top: 1rem; padding-bottom: 5rem; max-width: 1000px; }
.clinic-title {
    background: #ffffff;
    color: #111111;
    padding: 12px 12px 16px 12px;
    border-radius: 18px;
    border: 2px solid #111111;
    text-align: center;
    font-weight: 900;
    letter-spacing: .2px;
    line-height: 1.25;
    font-size: clamp(18px, 3vw, 25px);
    margin-top: 10px;
    margin-bottom: 20px;
}
.logo-wrap {
    background: #ffffff;
    border-radius: 18px;
    padding: 12px;
    margin-top: 8px;
    margin-bottom: 10px;
    text-align: center;
}
.logo-wrap img { max-width: 280px; width: 70%; height: auto; }
.mobile-card {
    background: white;
    border-left: 6px solid #9ACD32;
    border-radius: 18px;
    padding: 14px;
    margin: 10px 0;
    box-shadow: 0 3px 10px rgba(0,0,0,.06);
}
.stButton > button, .stFormSubmitButton > button {
    background: #111111;
    color: #ffffff;
    border-radius: 16px;
    min-height: 46px;
    border: 0;
    font-weight: 700;
    width: 100%;
}
</style>
""", unsafe_allow_html=True)

# ---------------- SUPABASE ----------------
@st.cache_resource
def get_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

sb = get_supabase()

def fetch(table, order=None):
    query = sb.table(table).select("*")
    if order:
        query = query.order(order, desc=False)
    res = query.execute()
    return pd.DataFrame(res.data or [])

def insert(table, payload):
    return sb.table(table).insert(payload).execute()

def update(table, row_id, payload):
    return sb.table(table).update(payload).eq("id", row_id).execute()

def delete(table, row_id):
    return sb.table(table).delete().eq("id", row_id).execute()

def get_options(grup):
    res = sb.table("ayarlar").select("*").eq("grup", grup).order("deger").execute()
    return [r["deger"] for r in (res.data or [])]


# ---------------- DEFAULT SETTINGS ----------------
DEFAULT_AYARLAR = [
    {"grup": "hekim", "deger": "Dr.Dt. M. Enes MARAŞ", "renk": "#9ACD32"},
    {"grup": "hekim", "deger": "Dt. S. Deniz MARAŞ", "renk": "#111111"},

    {"grup": "oda", "deger": "Clinic 1", "renk": "#9ACD32"},
    {"grup": "oda", "deger": "Clinic 2", "renk": "#111111"},

    {"grup": "durum", "deger": "Planlandı", "renk": None},
    {"grup": "durum", "deger": "Geldi", "renk": None},
    {"grup": "durum", "deger": "Tamamlandı", "renk": None},
    {"grup": "durum", "deger": "İptal", "renk": None},
    {"grup": "durum", "deger": "Ertelendi", "renk": None},
    {"grup": "durum", "deger": "Ödeme Alındı", "renk": None},
    {"grup": "durum", "deger": "Ödeme Bekliyor", "renk": None},

    {"grup": "odeme", "deger": "Nakit", "renk": None},
    {"grup": "odeme", "deger": "Kredi Kartı", "renk": None},
    {"grup": "odeme", "deger": "Havale/EFT", "renk": None},
    {"grup": "odeme", "deger": "Parçalı Ödeme", "renk": None},

    {"grup": "gider", "deger": "Laboratuvar", "renk": None},
    {"grup": "gider", "deger": "Malzeme", "renk": None},
    {"grup": "gider", "deger": "Kira", "renk": None},
    {"grup": "gider", "deger": "Personel", "renk": None},
    {"grup": "gider", "deger": "Fatura", "renk": None},
    {"grup": "gider", "deger": "Diğer", "renk": None},

    {"grup": "lab", "deger": "Laboratuvar 1", "renk": None},

    {"grup": "lab_durum", "deger": "Gönderilecek", "renk": None},
    {"grup": "lab_durum", "deger": "Gönderildi", "renk": None},
    {"grup": "lab_durum", "deger": "Teslim Alındı", "renk": None},
    {"grup": "lab_durum", "deger": "Hastaya Takıldı", "renk": None},
    {"grup": "lab_durum", "deger": "İptal", "renk": None},
]

def ensure_default_ayarlar():
    """Ana ayarlar silinse bile app açılırken varsayılanları geri yükler."""
    try:
        mevcut = sb.table("ayarlar").select("grup,deger").execute().data or []
        mevcut_set = {(x.get("grup"), x.get("deger")) for x in mevcut}

        eksikler = [
            item for item in DEFAULT_AYARLAR
            if (item["grup"], item["deger"]) not in mevcut_set
        ]

        if eksikler:
            sb.table("ayarlar").insert(eksikler).execute()
    except Exception as e:
        st.warning("Varsayılan ayarlar kontrol edilemedi. Supabase ayarlar policy/kolonlarını kontrol et.")
        st.caption(str(e))


def make_slots():
    start = datetime.combine(date.today(), time(9, 0))
    return [(start + timedelta(minutes=30*i)).strftime("%H:%M") for i in range(24)]

def monday_of(d):
    return d - timedelta(days=d.weekday())

def safe(v):
    if v is None:
        return ""
    try:
        if pd.isna(v):
            return ""
    except Exception:
        pass
    return str(v)

def money(v):
    try:
        return f"{float(v or 0):,.2f} TL"
    except Exception:
        return "0.00 TL"

def show_islem_risk_warnings(islem_adi, kategori="", hasta_row=None):
    """Seçilen işleme ve hasta anamnezine göre klinik risk hatırlatıcıları gösterir."""
    islem = safe(islem_adi).lower()
    kat = safe(kategori).lower()

    kronik = safe(hasta_row.get("kronik_hastalik") if hasta_row is not None else "").lower()
    ilac = safe(hasta_row.get("kullanilan_ilaclar") if hasta_row is not None else "").lower()
    alerji = safe(hasta_row.get("alerji") if hasta_row is not None else "").lower()
    anamnez = " ".join([kronik, ilac, alerji])

    cerrahi_keywords = ["çekim", "implant", "cerrahi", "greft", "sinüs", "sinus", "kist", "rezeksiyon", "gömülü"]
    protez_keywords = ["protez", "zirkonyum", "kron", "köprü", "implant üstü"]
    endo_keywords = ["kanal", "endodonti"]
    perio_keywords = ["detartraj", "küretaj", "periodontal", "diş taşı"]

    is_cerrahi = any(k in islem for k in cerrahi_keywords) or "cerrahi" in kat
    is_protez = any(k in islem for k in protez_keywords) or "protez" in kat
    is_endo = any(k in islem for k in endo_keywords) or "endodonti" in kat
    is_perio = any(k in islem for k in perio_keywords) or "periodontoloji" in kat

    if is_cerrahi:
        st.warning("🦷 Cerrahi işlem hatırlatması: kanama riski, sistemik hastalıklar, ilaç kullanımı ve iyileşme durumu işlem öncesi kontrol edilmeli.")
        if any(k in anamnez for k in ["kan sulandırıcı", "antikoagülan", "aspirin", "antiagregan", "kanama"]):
            st.error("🚨 Cerrahi + kanama riski: kan sulandırıcı/kanama öyküsü var. Hekim değerlendirmesi ve gerekirse konsültasyon gerekir.")
        if any(k in anamnez for k in ["diyabet", "diabetes"]):
            st.warning("⚠ Cerrahi + diyabet: enfeksiyon ve yara iyileşmesi açısından dikkat.")
        if any(k in anamnez for k in ["bisfosfonat", "osteoporoz"]):
            st.error("🚨 Cerrahi + bisfosfonat/osteoporoz ilacı: osteonekroz riski açısından dikkat.")
        if any(k in anamnez for k in ["radyoterapi", "kemoterapi", "kanser"]):
            st.error("🚨 Cerrahi + onkolojik öykü: RT/KT ve immünsüpresyon açısından ayrıntılı değerlendirme gerekir.")

    if is_protez:
        st.info("🧪 Protez/lab işlemi: laboratuvar takibi, prova/teslim tarihi ve lab maliyeti kontrol edilmeli.")
        if any(k in anamnez for k in ["bruksizm", "sıkma", "gıcırdatma"]):
            st.warning("⚠ Protez + bruksizm: materyal seçimi ve gece plağı ihtiyacı değerlendirilmeli.")

    if is_endo:
        st.info("🦷 Kanal tedavisi hatırlatması: ağrı, perküsyon hassasiyeti, radyografik bulgu ve seans takibi kontrol edilmeli.")
        if any(k in anamnez for k in ["kalp kapağı", "endokardit"]):
            st.warning("⚠ Endodonti + endokardit riski: profilaksi gerekliliği hekim tarafından değerlendirilmeli.")

    if is_perio:
        st.info("🪥 Periodontal işlem hatırlatması: kanama, plak kontrolü, periodontal bakım randevusu ve sistemik riskler değerlendirilmeli.")
        if any(k in anamnez for k in ["kan sulandırıcı", "antikoagülan", "aspirin", "antiagregan", "kanama"]):
            st.warning("⚠ Periodontal işlem + kanama riski: işlem sırasında kanama kontrolü planlanmalı.")

    if any(k in anamnez for k in ["lokal anestezik"]):
        st.error("🚨 Lokal anestezik alerjisi kayıtlı: anestezi planı işlemden önce mutlaka kontrol edilmeli.")
    if any(k in anamnez for k in ["penisilin", "antibiyotik alerjisi"]):
        st.warning("⚠ Antibiyotik alerjisi kayıtlı: reçete yazmadan önce kontrol et.")


def hasta_risk_ozeti(row):
    """Hasta kartında gösterilecek kısa risk özeti üretir."""
    kronik = safe(row.get("kronik_hastalik")).lower()
    ilac = safe(row.get("kullanilan_ilaclar")).lower()
    alerji = safe(row.get("alerji")).lower()
    metin = " ".join([kronik, ilac, alerji])

    riskler = []

    if "diyabet" in metin:
        riskler.append("⚠ Diyabet")
    if "hipertansiyon" in metin:
        riskler.append("⚠ Hipertansiyon")
    if any(k in metin for k in ["kan sulandırıcı", "antikoagülan", "aspirin", "antiagregan", "kanama"]):
        riskler.append("🚨 Kanama riski")
    if any(k in metin for k in ["bisfosfonat", "osteoporoz"]):
        riskler.append("🚨 Bisfosfonat/osteonekroz riski")
    if any(k in metin for k in ["radyoterapi", "kemoterapi", "kanser"]):
        riskler.append("🚨 Onkolojik öykü")
    if "lokal anestezik" in metin:
        riskler.append("🚨 Lokal anestezik alerjisi")
    if any(k in metin for k in ["penisilin", "antibiyotik alerjisi"]):
        riskler.append("⚠ Antibiyotik alerjisi")
    if "lateks" in metin:
        riskler.append("⚠ Lateks alerjisi")

    try:
        dogum = row.get("dogum_tarihi")
        if dogum:
            dt = datetime.strptime(str(dogum), "%Y-%m-%d").date()
            yas = date.today().year - dt.year - ((date.today().month, date.today().day) < (dt.month, dt.day))
            if yas < 12:
                riskler.append("🧒 Pediatrik")
            elif yas >= 65:
                riskler.append("👴 Geriatrik")
    except Exception:
        pass

    return " | ".join(riskler) if riskler else "Belirgin risk işaretlenmemiş"

# ---------------- AUTH ----------------
def check_login():
    try:
        allowed_username = st.secrets["APP_USERNAME"]
        allowed_password = st.secrets["APP_PASSWORD"]
    except Exception:
        st.error("APP_USERNAME / APP_PASSWORD Secrets eksik.")
        st.stop()

    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if st.session_state["authenticated"]:
        with st.sidebar:
            if st.button("Çıkış Yap"):
                st.session_state["authenticated"] = False
                st.rerun()
        return

    st.markdown("""
    <div style="max-width:420px;margin:40px auto;background:white;border:2px solid #111;border-radius:18px;padding:22px;">
        <h2 style="text-align:center;color:#111;">Özel Dentalde Çayyolu</h2>
        <p style="text-align:center;">Yetkili kullanıcı girişi</p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("login_form"):
        username = st.text_input("Kullanıcı Adı")
        password = st.text_input("Şifre", type="password")
        login = st.form_submit_button("Giriş Yap")
    if login:
        if username == allowed_username and password == allowed_password:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Kullanıcı adı veya şifre hatalı.")
    st.stop()

# ---------------- HEADER ----------------
try:
    with open("dentalde_logo.png", "rb") as f:
        logo_b64 = base64.b64encode(f.read()).decode()
    st.markdown(f'<div class="logo-wrap"><img src="data:image/png;base64,{logo_b64}"></div>', unsafe_allow_html=True)
except Exception:
    pass

st.markdown('<div class="clinic-title"><span>ÖZEL DENTALDE ÇAYYOLU</span><br><span>AĞIZ VE DİŞ SAĞLIĞI POLİKLİNİĞİ</span></div>', unsafe_allow_html=True)

check_login()
ensure_default_ayarlar()

MENU = [
    "1 Hasta Kayıt",
    "2 Hasta Listesi",
    "3 Haftalık Program",
    "4 Randevu Ekle",
    "5 Hasta İşlemleri",
    "6 Cari / Ödeme",
    "7 Laboratuvar",
    "8 Gelir-Gider",
    "9 TDB İşlemleri",
    "10 Ayarlar",
]

with st.sidebar:
    st.markdown("### Menü")
    sayfa = st.radio("Menü", MENU, label_visibility="collapsed")

# ---------------- 1 HASTA ----------------
if sayfa == "1 Hasta Kayıt":
    st.header("Hasta Kayıt ve Anamnez")

    with st.form("hasta_form"):
        hasta_adi = st.text_input("Hasta Adı Soyadı *")
        c1, c2 = st.columns(2)
        tc = c1.text_input("T.C.")
        telefon = c2.text_input("Telefon")
        dogum_tarihi = st.date_input(
            "Doğum Tarihi",
            value=date(2000, 1, 1),
            min_value=date(1900, 1, 1),
            max_value=date.today()
        )

        yas = date.today().year - dogum_tarihi.year - (
            (date.today().month, date.today().day) < (dogum_tarihi.month, dogum_tarihi.day)
        )
        st.caption(f"Yaş: {yas}")

        if yas < 12:
            st.warning("🧒 Pediyatrik hasta: doz ayarlamaları ve davranış yönetimi önemli.")
        elif yas >= 65:
            st.warning("👴 Geriatrik hasta: sistemik hastalıklar ve ilaç kullanımı dikkatle değerlendirilmeli.")

        st.markdown("### Anamnez / Risk Bilgileri")

        kronik_secimler = st.multiselect(
            "Kronik hastalık hatırlatıcıları",
            [
                "Diyabet",
                "Hipertansiyon",
                "Kalp hastalığı",
                "Ritim bozukluğu",
                "Kalp kapağı / endokardit riski",
                "Tiroid hastalığı",
                "Astım",
                "KOAH",
                "Epilepsi",
                "Böbrek hastalığı",
                "Karaciğer hastalığı",
                "Kanama / pıhtılaşma bozukluğu",
                "Osteoporoz",
                "Romatizmal hastalık",
                "İmmünsüpresyon",
                "Gebelik",
                "Emzirme",
                "Kanser öyküsü",
                "Radyoterapi / kemoterapi öyküsü"
            ]
        )
        kronik_not = st.text_area("Kronik hastalık ek notu")
        kronik = (", ".join(kronik_secimler) + (" | Not: " + kronik_not if kronik_not else "")).strip(" |")

        ilac_secimler = st.multiselect(
            "Kullanılan ilaç hatırlatıcıları",
            [
                "Kan sulandırıcı / antikoagülan",
                "Aspirin / antiagregan",
                "Tansiyon ilacı",
                "Diyabet ilacı / insülin",
                "Kortizon",
                "Bisfosfonat / osteoporoz ilacı",
                "Kemoterapi / immünsüpresif ilaç",
                "Antidepresan / psikiyatrik ilaç",
                "Tiroid ilacı",
                "Astım ilacı",
                "Düzenli ağrı kesici / NSAİİ",
                "Doğum kontrol hapı",
                "Diğer"
            ]
        )
        ilac_not = st.text_area("Kullanılan ilaç ek notu")
        ilac = (", ".join(ilac_secimler) + (" | Not: " + ilac_not if ilac_not else "")).strip(" |")

        alerji_secimler = st.multiselect(
            "Alerji hatırlatıcıları",
            [
                "Penisilin",
                "Antibiyotik alerjisi",
                "Lokal anestezik alerjisi",
                "Ağrı kesici / NSAİİ alerjisi",
                "Lateks alerjisi",
                "İyot / antiseptik alerjisi",
                "Gıda alerjisi",
                "Bilinmeyen ilaç alerjisi",
                "Alerji yok",
                "Diğer"
            ]
        )
        alerji_not = st.text_area("Alerji ek notu")
        alerji = (", ".join(alerji_secimler) + (" | Not: " + alerji_not if alerji_not else "")).strip(" |")

        if "Diyabet" in kronik_secimler:
            st.warning("⚠ Diyabet: enfeksiyon riski, yara iyileşmesi ve randevu öncesi beslenme/ilaç düzeni sorgulanmalı.")
        if "Hipertansiyon" in kronik_secimler:
            st.warning("⚠ Hipertansiyon: tansiyon ölçümü ve adrenalinli lokal anestezik kullanımı dikkatle değerlendirilmeli.")
        if "Kanama / pıhtılaşma bozukluğu" in kronik_secimler or "Kan sulandırıcı / antikoagülan" in ilac_secimler or "Aspirin / antiagregan" in ilac_secimler:
            st.error("🚨 Kanama riski: cerrahi/çekim öncesi hekim değerlendirmesi ve gerekirse konsültasyon önerilir.")
        if "Kalp kapağı / endokardit riski" in kronik_secimler:
            st.warning("⚠ Endokardit riski: işlem öncesi profilaksi gerekliliği hekim tarafından değerlendirilmeli.")
        if "Bisfosfonat / osteoporoz ilacı" in ilac_secimler:
            st.error("🚨 Bisfosfonat/osteoporoz ilacı: çekim, implant ve cerrahi işlemlerde osteonekroz riski açısından dikkat.")
        if "Radyoterapi / kemoterapi öyküsü" in kronik_secimler or "Kemoterapi / immünsüpresif ilaç" in ilac_secimler:
            st.error("🚨 Onkolojik tedavi/immünsüpresyon: cerrahi ve enfeksiyon riski açısından detaylı değerlendirme gerekir.")
        if "Lokal anestezik alerjisi" in alerji_secimler:
            st.error("🚨 Lokal anestezik alerjisi: işlem öncesi alternatif plan ve hekim değerlendirmesi şart.")
        if "Penisilin" in alerji_secimler or "Antibiyotik alerjisi" in alerji_secimler:
            st.warning("⚠ Antibiyotik alerjisi: reçete öncesi mutlaka kontrol edilmeli.")
        if "Lateks alerjisi" in alerji_secimler:
            st.warning("⚠ Lateks alerjisi: latekssiz eldiven ve malzeme kullanılmalı.")

        kanser = st.text_area("Kanser Geçmişi / RT-KT")
        operasyon = st.text_area("Operasyon / Hastane Yatış Geçmişi")
        c3, c4 = st.columns(2)
        hamilelik = c3.selectbox("Hamilelik Durumu", ["Yok", "Var", "Bilinmiyor", "Uygun değil"])
        kanama = c4.selectbox("Kanama / Pıhtılaşma Problemi", ["Yok", "Var", "Bilinmiyor"])
        sistemik = st.text_area("Diğer Sistemik Notlar")
        notlar = st.text_area("Genel Notlar")
        kaydet = st.form_submit_button("Hasta Kaydet")

    if kaydet:
        if not hasta_adi.strip():
            st.error("Hasta adı zorunlu.")
        else:
            insert("hastalar", {
                "hasta_adi": hasta_adi.strip(), "tc": tc, "telefon": telefon,
                "dogum_tarihi": str(dogum_tarihi), "kronik_hastalik": kronik,
                "kullanilan_ilaclar": ilac, "alerji": alerji, "kanser_gecmisi": kanser,
                "operasyon_gecmisi": operasyon, "hamilelik_durumu": hamilelik,
                "kanama_pihtilasma": kanama, "sistemik_notlar": sistemik, "notlar": notlar
            })
            st.success("Hasta Supabase'e kaydedildi.")
            st.rerun()

    st.subheader("Hasta Listesi")
    hastalar = fetch("hastalar", "hasta_adi")
    if hastalar.empty:
        st.info("Henüz hasta yok.")
    else:
        ara = st.text_input("Hasta ara")
        shown = hastalar[hastalar["hasta_adi"].str.contains(ara, case=False, na=False)] if ara else hastalar
        for _, r in shown.iterrows():
            st.markdown(f"""
            <div class="mobile-card">
            <b>{safe(r.get('hasta_adi'))}</b><br>
            Tel: {safe(r.get('telefon'))} | TC: {safe(r.get('tc'))}<br>
            Alerji: {safe(r.get('alerji')) or '-'}<br>
            Kronik: {safe(r.get('kronik_hastalik')) or '-'}<br>
            İlaç: {safe(r.get('kullanilan_ilaclar')) or '-'}
            </div>
            """, unsafe_allow_html=True)

        st.subheader("Hasta Düzenle / Sil")
        hastalar["secim"] = hastalar["id"].astype(str) + " | " + hastalar["hasta_adi"].astype(str)
        sec = st.selectbox("Hasta seç", hastalar["secim"].tolist())
        hid = int(sec.split(" | ")[0])
        row = hastalar[hastalar["id"] == hid].iloc[0]

        with st.form("hasta_edit"):
            ad2 = st.text_input("Hasta Adı", value=safe(row.get("hasta_adi")))
            tel2 = st.text_input("Telefon", value=safe(row.get("telefon")))
            alerji2 = st.text_area("Alerji", value=safe(row.get("alerji")))
            kronik2 = st.text_area("Kronik Hastalık", value=safe(row.get("kronik_hastalik")))
            ilac2 = st.text_area("Kullanılan İlaçlar", value=safe(row.get("kullanilan_ilaclar")))
            c1, c2 = st.columns(2)
            guncelle = c1.form_submit_button("Güncelle")
            sil = c2.form_submit_button("Sil")

        if guncelle:
            old_name = safe(row.get("hasta_adi"))
            update("hastalar", hid, {"hasta_adi": ad2, "telefon": tel2, "alerji": alerji2, "kronik_hastalik": kronik2, "kullanilan_ilaclar": ilac2})
            if old_name != ad2:
                for table in ["randevular", "hasta_islemleri", "odemeler", "giderler", "laboratuvar"]:
                    rows = sb.table(table).select("*").eq("hasta_adi", old_name).execute().data or []
                    for rr in rows:
                        update(table, rr["id"], {"hasta_adi": ad2})
            st.success("Hasta güncellendi.")
            st.rerun()

        if sil:
            hasta_ad = safe(row.get("hasta_adi"))
            for table in ["laboratuvar", "giderler", "odemeler", "hasta_islemleri", "randevular"]:
                rows = sb.table(table).select("*").eq("hasta_adi", hasta_ad).execute().data or []
                for rr in rows:
                    delete(table, rr["id"])
            delete("hastalar", hid)
            st.warning("Hasta ve bağlı kayıtlar silindi.")
            st.rerun()

# ---------------- 2 HASTA LISTESI ----------------
elif sayfa == "2 Hasta Listesi":
    st.header("Detaylı Hasta Listesi")

    hastalar = fetch("hastalar", "hasta_adi")
    if hastalar.empty:
        st.info("Henüz hasta kaydı yok.")
    else:
        c1, c2 = st.columns(2)
        ara = c1.text_input("Hasta adı / telefon / TC ara")
        risk_filtresi = c2.selectbox(
            "Risk filtresi",
            ["Tümü", "Riskli hastalar", "Diyabet", "Hipertansiyon", "Kanama riski", "Alerji", "Onkolojik öykü", "Pediatrik", "Geriatrik"]
        )

        shown = hastalar.copy()

        if ara:
            mask = (
                shown["hasta_adi"].fillna("").str.contains(ara, case=False, na=False) |
                shown["telefon"].fillna("").str.contains(ara, case=False, na=False) |
                shown["tc"].fillna("").str.contains(ara, case=False, na=False)
            )
            shown = shown[mask]

        def risk_match(row, filtre):
            ozet = hasta_risk_ozeti(row).lower()
            metin = " ".join([
                safe(row.get("kronik_hastalik")),
                safe(row.get("kullanilan_ilaclar")),
                safe(row.get("alerji")),
                safe(row.get("kanser_gecmisi")),
            ]).lower()

            if filtre == "Tümü":
                return True
            if filtre == "Riskli hastalar":
                return "belirgin risk işaretlenmemiş" not in ozet
            if filtre == "Diyabet":
                return "diyabet" in metin
            if filtre == "Hipertansiyon":
                return "hipertansiyon" in metin
            if filtre == "Kanama riski":
                return any(k in metin for k in ["kan sulandırıcı", "antikoagülan", "aspirin", "antiagregan", "kanama"])
            if filtre == "Alerji":
                return bool(safe(row.get("alerji")).strip())
            if filtre == "Onkolojik öykü":
                return any(k in metin for k in ["kanser", "radyoterapi", "kemoterapi"])
            if filtre == "Pediatrik":
                return "pediatrik" in ozet
            if filtre == "Geriatrik":
                return "geriatrik" in ozet
            return True

        shown = shown[shown.apply(lambda r: risk_match(r, risk_filtresi), axis=1)]

        st.caption(f"Görünen hasta sayısı: {len(shown)} / Toplam: {len(hastalar)}")

        export_df = shown.copy()
        if not export_df.empty:
            export_df["risk_ozeti"] = export_df.apply(hasta_risk_ozeti, axis=1)
            kolonlar = [
                "hasta_adi", "telefon", "tc", "dogum_tarihi", "risk_ozeti",
                "kronik_hastalik", "kullanilan_ilaclar", "alerji",
                "kanser_gecmisi", "operasyon_gecmisi", "hamilelik_durumu",
                "kanama_pihtilasma", "sistemik_notlar", "notlar"
            ]
            kolonlar = [k for k in kolonlar if k in export_df.columns]
            st.dataframe(export_df[kolonlar], width="stretch", hide_index=True)

        st.subheader("Detaylı Kartlar")
        for _, r in shown.iterrows():
            risk = hasta_risk_ozeti(r)
            st.markdown(f"""
            <div class="mobile-card">
            <b>{safe(r.get('hasta_adi'))}</b><br>
            Tel: {safe(r.get('telefon')) or '-'} | TC: {safe(r.get('tc')) or '-'} | Doğum: {safe(r.get('dogum_tarihi')) or '-'}<br>
            <b>Risk Özeti:</b> {risk}<br>
            <b>Kronik:</b> {safe(r.get('kronik_hastalik')) or '-'}<br>
            <b>İlaç:</b> {safe(r.get('kullanilan_ilaclar')) or '-'}<br>
            <b>Alerji:</b> {safe(r.get('alerji')) or '-'}<br>
            <b>Kanser / RT-KT:</b> {safe(r.get('kanser_gecmisi')) or '-'}<br>
            <b>Operasyon:</b> {safe(r.get('operasyon_gecmisi')) or '-'}<br>
            <b>Diğer not:</b> {safe(r.get('notlar')) or '-'}
            </div>
            """, unsafe_allow_html=True)

# ---------------- 3 TAKVIM ----------------
elif sayfa == "3 Haftalık Program":
    st.header("Haftalık Program")
    st.caption("Bu ekran sadece randevuları gösterir. Hasta işlemleri cari ve laboratuvar takibi için ayrı tutulur; takvimde ikinci kez gösterilmez.")

    secilen = st.date_input("Hafta seç", value=date.today())
    bas = monday_of(secilen)
    son = bas + timedelta(days=6)

    randevular = sb.table("randevular").select("*").gte("tarih", str(bas)).lte("tarih", str(son)).execute().data or []

    if not randevular:
        st.info("Bu haftada randevu yok.")
    else:
        df = pd.DataFrame(randevular).sort_values(["tarih","saat"])
        for g in [bas + timedelta(days=i) for i in range(7)]:
            st.subheader(g.strftime("%d.%m %A"))
            gd = str(g)
            rows = df[df["tarih"] == gd]
            if rows.empty:
                st.caption("Boş")
            for _, row in rows.iterrows():
                st.markdown(f"""
                <div class="mobile-card">
                <b>{safe(row.get('saat'))} - {safe(row.get('hasta_adi'))}</b><br>
                {safe(row.get('hekim'))} {('| ' + safe(row.get('oda'))) if safe(row.get('oda')) else ''}<br>
                <b>{safe(row.get('islem_adi'))}</b><br>
                Durum: {safe(row.get('durum'))}
                </div>
                """, unsafe_allow_html=True)

# ---------------- 3 RANDEVU ----------------
elif sayfa == "4 Randevu Ekle":
    st.header("Randevu Ekle / Düzenle")
    st.caption("Hasta seçildiğinde yalnızca o hastaya 'Hasta İşlemleri' ekranında atanmış işlemler listelenir.")

    hastalar = fetch("hastalar", "hasta_adi")
    tum_islemler = fetch("islemler", "islem_adi")
    hasta_islemleri_all = fetch("hasta_islemleri", "tarih")
    hekimler = get_options("hekim")
    odalar = get_options("oda")
    durumlar = get_options("durum")

    if hastalar.empty:
        st.warning("Önce hasta kaydı oluştur.")
    elif tum_islemler.empty:
        st.warning("Önce TDB işlemi ekle.")
    else:
        with st.form("randevu_form"):
            c1, c2 = st.columns(2)
            tarih = c1.date_input("Tarih", value=date.today())
            saat = c2.selectbox("Saat", make_slots())
            hasta = st.selectbox("Hasta", hastalar["hasta_adi"].tolist())
            c3, c4 = st.columns(2)
            hekim = c3.selectbox("Hekim", hekimler)
            oda = c4.selectbox("Clinic", odalar)

            hasta_atanmis = pd.DataFrame()
            if not hasta_islemleri_all.empty and "hasta_adi" in hasta_islemleri_all.columns:
                hasta_atanmis = hasta_islemleri_all[
                    (hasta_islemleri_all["hasta_adi"] == hasta) &
                    (hasta_islemleri_all["durum"].fillna("") != "İptal")
                ].copy()

            if hasta_atanmis.empty:
                st.warning("Bu hastaya atanmış işlem yok. Önce 'Hasta İşlemleri' sekmesinden işlem ekle.")
                secenekler = ["İşlem seç"]
            else:
                hasta_atanmis["secim"] = (
                    hasta_atanmis["id"].astype(str) + " | " +
                    hasta_atanmis["islem_adi"].astype(str) + " | " +
                    hasta_atanmis["tarih"].astype(str)
                )
                secenekler = ["İşlem seç"] + hasta_atanmis["secim"].tolist()

            sec = st.selectbox("İşlem", secenekler)

            info = None
            selected_hasta_islem = None

            if sec != "İşlem seç":
                hasta_islem_id = int(sec.split(" | ")[0])
                selected_hasta_islem = hasta_atanmis[hasta_atanmis["id"] == hasta_islem_id].iloc[0]

                islem_id_raw = safe(selected_hasta_islem.get("islem_id"))
                matched = pd.DataFrame()

                if islem_id_raw and not tum_islemler.empty:
                    if "kod" in tum_islemler.columns:
                        matched = tum_islemler[
                            (tum_islemler["kod"].astype(str) == islem_id_raw) |
                            (tum_islemler["id"].astype(str) == islem_id_raw)
                        ]
                    else:
                        matched = tum_islemler[tum_islemler["id"].astype(str) == islem_id_raw]

                if not matched.empty:
                    info = matched.iloc[0]
                else:
                    info = selected_hasta_islem

                hasta_row = hastalar[hastalar["hasta_adi"] == hasta].iloc[0] if not hastalar.empty else None
                show_islem_risk_warnings(info.get("islem_adi"), info.get("kategori"), hasta_row)

            dis_no = st.text_input(
                "Diş No",
                value=safe(selected_hasta_islem.get("dis_no")) if selected_hasta_islem is not None else ""
            )

            ucret = st.number_input(
                "Ücret",
                value=float(selected_hasta_islem.get("ucret") or info.get("kdv_dahil_ucret") or 0) if info is not None else 0.0,
                step=100.0
            )

            durum = st.selectbox("Durum", durumlar)
            notlar = st.text_area("Not")
            kaydet = st.form_submit_button("Randevu Kaydet")

        if kaydet:
            if info is None:
                st.error("Lütfen işlem seç.")
                st.stop()

            conflict = sb.table("randevular").select("*").eq("tarih", str(tarih)).eq("saat", saat).eq("oda", oda).execute().data or []
            if conflict:
                st.error("Çakışma: Aynı tarih/saat/clinic için randevu var.")
            else:
                insert("randevular", {
                    "tarih": str(tarih),
                    "saat": saat,
                    "hasta_adi": hasta,
                    "hekim": hekim,
                    "oda": oda,
                    "islem_id": str(info.get("kod") or info.get("islem_id") or info.get("id")),
                    "islem_adi": info["islem_adi"],
                    "dis_no": dis_no,
                    "ucret": ucret,
                    "sure_dk": int(info.get("sure_dk") or 30),
                    "durum": durum,
                    "notlar": notlar
                })

                if selected_hasta_islem is not None:
                    update("hasta_islemleri", int(selected_hasta_islem["id"]), {
                        "tarih": str(tarih),
                        "saat": saat,
                        "dis_no": dis_no,
                        "hekim": hekim,
                        "ucret": ucret,
                        "durum": durum,
                        "notlar": notlar
                    })

                st.success("Randevu kaydedildi ve atanmış hasta işlemi güncellendi.")
                st.rerun()

    r = fetch("randevular", "tarih")
    if not r.empty:
        st.subheader("Randevu Düzenle / Sil")
        r["secim"] = r["id"].astype(str) + " | " + r["tarih"].astype(str) + " " + r["saat"].astype(str) + " | " + r["hasta_adi"].astype(str)
        sec = st.selectbox("Randevu seç", r["secim"].tolist())
        rid = int(sec.split(" | ")[0])
        row = r[r["id"] == rid].iloc[0]
        with st.form("r_edit"):
            durum = st.selectbox("Durum", durumlar, index=durumlar.index(row["durum"]) if row["durum"] in durumlar else 0)
            notu = st.text_area("Not", value=safe(row.get("notlar")))
            c1, c2 = st.columns(2)
            g = c1.form_submit_button("Güncelle")
            s = c2.form_submit_button("Sil")
        if g:
            update("randevular", rid, {"durum": durum, "notlar": notu})
            st.success("Randevu güncellendi.")
            st.rerun()
        if s:
            delete("randevular", rid)
            st.warning("Randevu silindi.")
            st.rerun()

# ---------------- 4 ISLEMLER ----------------
 elif sayfa == "5 Hasta İşlemleri":
    st.header("Hasta İşlemleri")
    hastalar = fetch("hastalar", "hasta_adi")
    islemler = fetch("islemler", "islem_adi")
    if not islemler.empty and "kod" in islemler.columns:
        islemler = islemler.assign(
            _sort_key=islemler["kod"].astype(str).str.extract(r"(\d+)")[0].fillna(999999).astype(int)
        ).sort_values("_sort_key").drop(columns=["_sort_key"])
    hekimler = get_options("hekim")

    if hastalar.empty:
        st.warning("Önce hasta ekle.")
    elif islemler.empty:
        st.warning("Önce işlem ekle.")
    else:
        with st.form("hi_add"):
            hasta = st.selectbox("Hasta", ["Hasta seç"] + hastalar["hasta_adi"].tolist())

            islemler["secim"] = (
                islemler["kod"].fillna(islemler["id"].astype(str)).astype(str)
                + " | " +
                islemler["islem_adi"].astype(str)
            )

            sec = st.selectbox("İşlem", ["İşlem seç"] + islemler["secim"].tolist())
            hekim = st.selectbox("Hekim", ["Hekim seç"] + hekimler)
            tarih = st.date_input("Tarih seç", value=date.today(), format="DD/MM/YYYY")

            info = None
            if sec != "İşlem seç":
                sec_kod = sec.split(" | ")[0]
                matched = islemler[
                    (islemler["kod"].astype(str) == sec_kod) |
                    (islemler["id"].astype(str) == sec_kod)
                ]
                if not matched.empty:
                    info = matched.iloc[0]

            hasta_row = None
            if hasta != "Hasta seç":
                hasta_row = hastalar[hastalar["hasta_adi"] == hasta].iloc[0]
                st.info(f"Seçilen hasta risk özeti: {hasta_risk_ozeti(hasta_row)}")

            if info is not None and hasta_row is not None:
                show_islem_risk_warnings(info.get("islem_adi"), info.get("kategori"), hasta_row)

            saat = st.selectbox("Saat", [""] + make_slots())
            dis_no = st.text_input("Diş No")
            ucret = st.number_input(
                "Ücret",
                value=float(info.get("kdv_dahil_ucret") or 0) if info is not None else 0.0,
                step=100.0
            )
            durum = st.selectbox("Durum", ["Planlandı", "Başlandı", "Tamamlandı", "İptal"])
            lab = st.checkbox("Laboratuvara gidecek")
            notlar = st.text_area("Not")
            kaydet = st.form_submit_button("İşlem Kaydet")

        if kaydet:
            if hasta == "Hasta seç":
                st.error("Lütfen hasta seç.")
                st.stop()
            if sec == "İşlem seç" or info is None:
                st.error("Lütfen işlem seç.")
                st.stop()
            if hekim == "Hekim seç":
                st.error("Lütfen hekim seç.")
                st.stop()

            insert("hasta_islemleri", {
                "tarih": str(tarih),
                "saat": saat,
                "hasta_adi": hasta,
                "islem_id": str(info.get("kod") or info.get("id")),
                "islem_adi": info["islem_adi"],
                "kategori": safe(info.get("kategori")),
                "dis_no": dis_no,
                "hekim": hekim,
                "ucret": ucret,
                "sure_dk": int(info.get("sure_dk") or 30),
                "durum": durum,
                "lab_gidecek": lab,
                "notlar": notlar
            })
            st.success("İşlem kaydedildi.")
            st.rerun()

    hi = fetch("hasta_islemleri", "tarih")
    if not hi.empty:
        for _, row in hi.sort_values("id", ascending=False).head(30).iterrows():
            tarih_goster = pd.to_datetime(row.get("tarih")).strftime("%d/%m/%Y") if safe(row.get("tarih")) else ""
            st.markdown(f"""
            <div class="mobile-card">
            <b>{safe(row.get('hasta_adi'))}</b><br>
            {tarih_goster} {safe(row.get('saat'))} | {safe(row.get('islem_adi'))}<br>
            Ücret: {money(row.get('ucret'))} | Durum: {safe(row.get('durum'))}
            </div>
            """, unsafe_allow_html=True)

        st.subheader("İşlem Düzenle / Sil")
        hi["secim"] = hi["id"].astype(str) + " | " + hi["hasta_adi"].astype(str) + " | " + hi["islem_adi"].astype(str)
        sec = st.selectbox("İşlem seç", hi["secim"].tolist())
        iid = int(sec.split(" | ")[0])
        row = hi[hi["id"] == iid].iloc[0]

        with st.form("hi_edit"):
            saat2 = st.selectbox(
                "Saat",
                [""] + make_slots(),
                index=([""] + make_slots()).index(safe(row.get("saat"))) if safe(row.get("saat")) in ([""] + make_slots()) else 0
            )
            durum2 = st.selectbox(
                "Durum",
                ["Planlandı", "Başlandı", "Tamamlandı", "İptal"],
                index=["Planlandı", "Başlandı", "Tamamlandı", "İptal"].index(row["durum"]) if row["durum"] in ["Planlandı", "Başlandı", "Tamamlandı", "İptal"] else 0
            )
            ucret2 = st.number_input("Ücret", value=float(row.get("ucret") or 0), step=100.0)
            lab2 = st.checkbox("Laboratuvara gidecek", value=bool(row.get("lab_gidecek")))
            c1, c2 = st.columns(2)
            g = c1.form_submit_button("Güncelle")
            s = c2.form_submit_button("Sil")

        if g:
            update("hasta_islemleri", iid, {
                "saat": saat2,
                "durum": durum2,
                "ucret": ucret2,
                "lab_gidecek": lab2
            })
            st.success("İşlem güncellendi.")
            st.rerun()

        if s:
            delete("hasta_islemleri", iid)
            st.warning("İşlem silindi.")
            st.rerun()

# ---------------- 5 CARI ----------------
elif sayfa == "6 Cari / Ödeme":
    st.header("Cari / Ödeme")
    hastalar = fetch("hastalar", "hasta_adi")
    if hastalar.empty:
        st.warning("Önce hasta ekle.")
    else:
        hasta = st.selectbox("Hasta", hastalar["hasta_adi"].tolist())
        hi = pd.DataFrame(sb.table("hasta_islemleri").select("*").eq("hasta_adi", hasta).execute().data or [])
        od = pd.DataFrame(sb.table("odemeler").select("*").eq("hasta_adi", hasta).execute().data or [])
        borc = hi[hi["durum"]!="İptal"]["ucret"].sum() if not hi.empty and "durum" in hi else 0
        tah = od["tutar"].sum() if not od.empty else 0
        c1, c2, c3 = st.columns(3)
        c1.metric("Borç", money(borc))
        c2.metric("Tahsilat", money(tah))
        c3.metric("Bakiye", money(float(borc)-float(tah)))

        with st.form("odeme"):
            tutar = st.number_input("Ödeme Tutarı", min_value=0.0, step=100.0)
            tip = st.selectbox("Ödeme Tipi", get_options("odeme"))
            aciklama = st.text_input("Açıklama")
            kaydet = st.form_submit_button("Ödeme Kaydet")
        if kaydet and tutar > 0:
            insert("odemeler", {"tarih": str(date.today()), "hasta_adi": hasta, "tutar": tutar, "odeme_tipi": tip, "aciklama": aciklama})
            st.success("Ödeme kaydedildi.")
            st.rerun()

        st.dataframe(od, width="stretch", hide_index=True)

# ---------------- 6 LAB ----------------
elif sayfa == "7 Laboratuvar":
    st.header("Laboratuvar")
    labs = get_options("lab")
    durumlar = get_options("lab_durum")

    hi = pd.DataFrame(sb.table("hasta_islemleri").select("*").eq("lab_gidecek", True).execute().data or [])
    lab = fetch("laboratuvar", "tarih")
    existing_ids = set(lab["islem_row_id"].dropna().astype(int).tolist()) if not lab.empty and "islem_row_id" in lab else set()
    cand = hi[~hi["id"].isin(existing_ids)] if not hi.empty else pd.DataFrame()

    st.subheader("Gönderilecekler")
    if cand.empty:
        st.info("Bekleyen lab işlemi yok.")
    else:
        cand["secim"] = cand["id"].astype(str) + " | " + cand["hasta_adi"] + " | " + cand["islem_adi"]
        with st.form("lab_add"):
            sec = st.selectbox("İşlem seç", cand["secim"].tolist())
            row_id = int(sec.split(" | ")[0])
            row = cand[cand["id"] == row_id].iloc[0]
            lab_adi = st.selectbox("Laboratuvar", labs)
            ucret = st.number_input("Lab Ücreti", min_value=0.0, step=100.0)
            aciklama = st.text_input("Açıklama")
            kaydet = st.form_submit_button("Lab Kaydı Aç")
        if kaydet:
            insert("laboratuvar", {
                "tarih": str(date.today()), "hasta_adi": row["hasta_adi"], "islem_row_id": int(row_id),
                "islem_adi": row["islem_adi"], "lab_adi": lab_adi, "gonderim_tarihi": str(date.today()),
                "lab_ucreti": ucret, "durum": "Gönderilecek", "aciklama": aciklama
            })
            st.success("Lab kaydı açıldı.")
            st.rerun()

    lab = fetch("laboratuvar", "tarih")
    if not lab.empty:
        for _, row in lab.sort_values("id", ascending=False).iterrows():
            st.markdown(f"""
            <div class="mobile-card">
            <b>{safe(row.get('hasta_adi'))}</b><br>
            {safe(row.get('islem_adi'))}<br>
            {safe(row.get('lab_adi'))} | {safe(row.get('durum'))} | {money(row.get('lab_ucreti'))}
            </div>
            """, unsafe_allow_html=True)

        st.subheader("Lab Güncelle / Sil")
        lab["secim"] = lab["id"].astype(str) + " | " + lab["hasta_adi"].astype(str) + " | " + lab["islem_adi"].astype(str)
        sec = st.selectbox("Lab seç", lab["secim"].tolist())
        lid = int(sec.split(" | ")[0])
        row = lab[lab["id"] == lid].iloc[0]
        with st.form("lab_edit"):
            durum = st.selectbox("Durum", durumlar, index=durumlar.index(row["durum"]) if row["durum"] in durumlar else 0)
            ucret = st.number_input("Ücret", value=float(row.get("lab_ucreti") or 0), step=100.0)
            c1, c2 = st.columns(2)
            g = c1.form_submit_button("Güncelle")
            s = c2.form_submit_button("Sil")
        if g:
            update("laboratuvar", lid, {"durum": durum, "lab_ucreti": ucret})
            st.success("Lab güncellendi.")
            st.rerun()
        if s:
            delete("laboratuvar", lid)
            st.warning("Lab silindi.")
            st.rerun()

# ---------------- 7 GELIR GIDER ----------------
elif sayfa == "8 Gelir-Gider":
    st.header("Gelir-Gider")
    od = fetch("odemeler", "tarih")
    gd = fetch("giderler", "tarih")
    gelir = od["tutar"].sum() if not od.empty else 0
    gider = gd["tutar"].sum() if not gd.empty else 0
    c1, c2, c3 = st.columns(3)
    c1.metric("Gelir", money(gelir))
    c2.metric("Gider", money(gider))
    c3.metric("Net", money(float(gelir)-float(gider)))

    with st.form("gider_add"):
        tip = st.selectbox("Gider Tipi", get_options("gider"))
        tutar = st.number_input("Tutar", min_value=0.0, step=100.0)
        aciklama = st.text_input("Açıklama")
        kaydet = st.form_submit_button("Gider Kaydet")
    if kaydet and tutar > 0:
        insert("giderler", {"tarih": str(date.today()), "gider_tipi": tip, "tutar": tutar, "odeme_tipi": "Nakit", "aciklama": aciklama})
        st.success("Gider kaydedildi.")
        st.rerun()

    st.dataframe(gd, width="stretch", hide_index=True)

# ---------------- 8 TDB ----------------
elif sayfa == "9 TDB İşlemleri":
    st.header("TDB İşlemleri")

    st.info("Excel yüklerken 200+ satır için toplu yükleme kullanılır. Aynı listeyi tekrar yüklüyorsan önce eski TDB kayıtlarını temizle.")

    def parse_money(x):
        if x is None or (isinstance(x, float) and pd.isna(x)):
            return 0.0
        s = str(x).replace("₺", "").replace("TL", "").replace(" ", "").strip()
        # 1.650,50 veya 1,650.50 ayrımı
        if "," in s and "." in s:
            if s.rfind(",") > s.rfind("."):
                s = s.replace(".", "").replace(",", ".")
            else:
                s = s.replace(",", "")
        elif "," in s:
            s = s.replace(".", "").replace(",", ".")
        else:
            # 1.650 gibi binlik nokta olabilir
            parts = s.split(".")
            if len(parts) > 1 and all(len(p) == 3 for p in parts[1:]):
                s = s.replace(".", "")
        try:
            return float(s)
        except Exception:
            return 0.0

    def parse_int(x, default=30):
        try:
            if pd.isna(x):
                return default
            return int(float(str(x).strip()))
        except Exception:
            return default

    def parse_bool(x):
        s = safe(x).strip().lower()
        return s in ["evet", "true", "1", "yes", "e"]

    uploaded = st.file_uploader("TDB Excel/CSV yükle", type=["csv","xlsx","xls"])
    temizle = st.checkbox("Yüklemeden önce mevcut TDB işlem listesini temizle", value=False)

    if uploaded:
        df = pd.read_csv(uploaded) if uploaded.name.endswith(".csv") else pd.read_excel(uploaded)
        st.write(f"Okunan satır sayısı: {len(df)}")

        cols = {str(c).lower().strip(): c for c in df.columns}
        def col(*names):
            for n in names:
                if n.lower().strip() in cols:
                    return cols[n.lower().strip()]
            return None

        kod_c = col("kod", "id", "sıra no", "sira no")
        kat_c = col("kategori")
        ad_c = col("işlem adı", "islem_adi", "islem adı", "işlem_adi")
        ucret_c = col("kdv dahil", "kdv_dahil_ucret", "kdv dahil ücret", "kdv_dahil_ücret")
        sure_c = col("tahmini süre (dk)", "sure_dk", "süre", "sure", "süre dk")
        dis_c = col("diş no gerekli mi?", "dis no gerekli mi?", "dis_no_gerekli", "diş_no_gerekli")
        durum_c = col("durum")

        if not kod_c or not ad_c or not ucret_c:
            st.error("Zorunlu kolonlar bulunamadı. Gerekli kolonlar: Kod/id, İşlem Adı, KDV Dahil.")
            st.write("Bulunan kolonlar:", list(df.columns))
        else:
            preview_payload = []
            for _, r in df.iterrows():
                kod = safe(r[kod_c]).strip()
                ad = safe(r[ad_c]).strip()
                if not kod or kod.lower() == "nan" or not ad:
                    continue
                preview_payload.append({
                    "kod": kod,
                    "kategori": safe(r[kat_c]).strip() if kat_c else "",
                    "islem_adi": ad,
                    "kdv_dahil_ucret": parse_money(r[ucret_c]),
                    "sure_dk": parse_int(r[sure_c], 30) if sure_c else 30,
                    "dis_no_gerekli": parse_bool(r[dis_c]) if dis_c else False,
                    "durum": safe(r[durum_c]).strip() if durum_c else "Aktif"
                })

            st.write(f"Yüklenecek geçerli işlem sayısı: {len(preview_payload)}")
            if preview_payload:
                st.dataframe(pd.DataFrame(preview_payload).head(10), width="stretch", hide_index=True)

            if st.button("TDB listesini toplu yükle"):
                try:
                    if temizle:
                        # Supabase REST delete için filtre gerekir; id > 0 tüm kayıtları siler.
                        sb.table("islemler").delete().gt("id", 0).execute()

                    # 500 satırın altında tek batch yeterli.
                    sb.table("islemler").insert(preview_payload).execute()
                    st.success(f"{len(preview_payload)} işlem toplu yüklendi.")
                    st.rerun()
                except Exception as e:
                    st.error("TDB yükleme sırasında hata oluştu.")
                    st.exception(e)

    st.subheader("Manuel İşlem Ekle")
    with st.form("islem_add"):
        kod = st.text_input("Kod")
        kategori = st.text_input("Kategori")
        ad = st.text_input("İşlem Adı")
        ucret = st.number_input("KDV Dahil Ücret", min_value=0.0, step=100.0)
        sure = st.number_input("Süre", min_value=5, step=5, value=30)
        dis = st.checkbox("Diş no gerekli")
        kaydet = st.form_submit_button("Kaydet")
    if kaydet and kod and ad:
        insert("islemler", {"kod": kod, "kategori": kategori, "islem_adi": ad, "kdv_dahil_ucret": ucret, "sure_dk": int(sure), "dis_no_gerekli": dis, "durum": "Aktif"})
        st.success("İşlem kaydedildi.")
        st.rerun()

    st.dataframe(fetch("islemler", "islem_adi"), width="stretch", hide_index=True)

# ---------------- 9 AYARLAR ----------------
elif sayfa == "10 Ayarlar":
    st.header("Ayarlar")
    ay = fetch("ayarlar", "grup")
    st.dataframe(ay, width="stretch", hide_index=True)

    gruplar = ["hekim","oda","durum","odeme","gider","lab","lab_durum"]
    with st.form("ayar_add"):
        grup = st.selectbox("Grup", gruplar)
        deger = st.text_input("Değer")
        renk = st.color_picker("Renk", "#9ACD32") if grup in ["hekim","oda"] else None
        kaydet = st.form_submit_button("Ayar Ekle")
    if kaydet and deger:
        insert("ayarlar", {"grup": grup, "deger": deger, "renk": renk})
        st.success("Ayar eklendi.")
        st.rerun()

    if not ay.empty:
        st.subheader("Ayar Düzenle / Sil")
        ay["secim"] = ay["id"].astype(str) + " | " + ay["grup"] + " | " + ay["deger"]
        sec = st.selectbox("Ayar seç", ay["secim"].tolist())
        aid = int(sec.split(" | ")[0])
        row = ay[ay["id"] == aid].iloc[0]
        with st.form("ayar_edit"):
            deger2 = st.text_input("Değer", value=row["deger"])
            c1, c2 = st.columns(2)
            g = c1.form_submit_button("Güncelle")
            s = c2.form_submit_button("Sil")
        if g:
            update("ayarlar", aid, {"deger": deger2})
            st.success("Ayar güncellendi.")
            st.rerun()
        if s:
            delete("ayarlar", aid)
            st.warning("Ayar silindi.")
            st.rerun()
