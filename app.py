
import sqlite3
import re
from datetime import date, datetime, timedelta, time
from pathlib import Path

import pandas as pd
import streamlit as st

DB_PATH = Path("klinik.db")

# ---------------- DB HELPERS ----------------
def conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def execute(sql, params=()):
    c = conn()
    cur = c.cursor()
    cur.execute(sql, params)
    c.commit()
    c.close()

def q(sql, params=()):
    c = conn()
    df = pd.read_sql_query(sql, c, params=params)
    c.close()
    return df

def column_exists(table, column):
    c = conn()
    cur = c.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in cur.fetchall()]
    c.close()
    return column in cols

def add_column_if_missing(table, column, definition):
    if not column_exists(table, column):
        execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

def safe_text(v):
    if v is None:
        return ""
    try:
        if pd.isna(v):
            return ""
    except Exception:
        pass
    return str(v)

def safe_hex_color(value, default="#9ACD32"):
    try:
        s = str(value).strip()
        if s.lower() in ["", "none", "nan", "nat"]:
            return default
        if re.match(r"^#[0-9A-Fa-f]{3}$|^#[0-9A-Fa-f]{6}$", s):
            return s
        return default
    except Exception:
        return default

def get_list(grup):
    df = q("SELECT deger FROM ayarlar WHERE grup=? ORDER BY deger", (grup,))
    return df["deger"].tolist()

def make_slots():
    start = datetime.combine(date.today(), time(9, 0))
    return [(start + timedelta(minutes=30*i)).strftime("%H:%M") for i in range(24)]

def monday_of(d):
    return d - timedelta(days=d.weekday())

def clean_money_value(x):
    if pd.isna(x):
        return 0.0
    s = str(x).replace("₺", "").replace("TL", "").replace(" ", "").strip()
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except Exception:
        return 0.0

def clean_int_value(x, default=30):
    try:
        return int(float(str(x).strip()))
    except Exception:
        return default

def init_db():
    c = conn()
    cur = c.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS hastalar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hasta_adi TEXT NOT NULL UNIQUE,
        tc TEXT,
        telefon TEXT,
        dogum_tarihi TEXT,
        kronik_hastalik TEXT,
        kullanilan_ilaclar TEXT,
        alerji TEXT,
        kanser_gecmisi TEXT,
        operasyon_gecmisi TEXT,
        hamilelik_durumu TEXT,
        kanama_pihtilasma TEXT,
        sistemik_notlar TEXT,
        notlar TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS islemler (
        id TEXT PRIMARY KEY,
        kategori TEXT,
        islem_adi TEXT NOT NULL,
        kdv_dahil_ucret REAL NOT NULL DEFAULT 0,
        sure_dk INTEGER NOT NULL DEFAULT 30,
        dis_no_gerekli INTEGER NOT NULL DEFAULT 0,
        durum TEXT DEFAULT 'Aktif'
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS ayarlar (
        grup TEXT NOT NULL,
        deger TEXT NOT NULL,
        renk TEXT,
        UNIQUE(grup, deger)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS randevular (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tarih TEXT NOT NULL,
        saat TEXT NOT NULL,
        hasta_adi TEXT NOT NULL,
        hekim TEXT NOT NULL,
        oda TEXT NOT NULL,
        islem_id TEXT,
        islem_adi TEXT NOT NULL,
        dis_no TEXT,
        ucret REAL NOT NULL DEFAULT 0,
        sure_dk INTEGER NOT NULL DEFAULT 30,
        durum TEXT,
        notlar TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS hasta_islemleri (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tarih TEXT NOT NULL,
        saat TEXT,
        hasta_adi TEXT NOT NULL,
        islem_id TEXT,
        islem_adi TEXT NOT NULL,
        kategori TEXT,
        dis_no TEXT,
        hekim TEXT,
        ucret REAL NOT NULL DEFAULT 0,
        sure_dk INTEGER NOT NULL DEFAULT 30,
        durum TEXT DEFAULT 'Planlandı',
        randevu_id INTEGER,
        lab_gidecek INTEGER DEFAULT 0,
        notlar TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS odemeler (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tarih TEXT NOT NULL,
        hasta_adi TEXT NOT NULL,
        tutar REAL NOT NULL,
        odeme_tipi TEXT NOT NULL,
        aciklama TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS giderler (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tarih TEXT NOT NULL,
        gider_tipi TEXT NOT NULL,
        tutar REAL NOT NULL,
        odeme_tipi TEXT,
        hasta_adi TEXT,
        islem_id INTEGER,
        aciklama TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS laboratuvar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tarih TEXT NOT NULL,
        hasta_adi TEXT NOT NULL,
        islem_id INTEGER,
        islem_adi TEXT,
        lab_adi TEXT,
        gonderim_tarihi TEXT,
        teslim_tarihi TEXT,
        lab_ucreti REAL DEFAULT 0,
        durum TEXT DEFAULT 'Gönderilecek',
        aciklama TEXT
    )
    """)

    defaults = [
        ("hekim", "Dr.Dt. M. Enes MARAŞ", "#9ACD32"),
        ("hekim", "Dt. S. Deniz MARAŞ", "#111111"),
        ("oda", "Clinic 1", "#9ACD32"),
        ("oda", "Clinic 2", "#111111"),
        ("durum", "Planlandı", None),
        ("durum", "Geldi", None),
        ("durum", "Tamamlandı", None),
        ("durum", "İptal", None),
        ("durum", "Ertelendi", None),
        ("odeme", "Nakit", None),
        ("odeme", "Kredi Kartı", None),
        ("odeme", "Havale/EFT", None),
        ("gider", "Laboratuvar", None),
        ("gider", "Malzeme", None),
        ("gider", "Kira", None),
        ("gider", "Personel", None),
        ("gider", "Fatura", None),
        ("gider", "Diğer", None),
        ("lab", "Laboratuvar 1", None),
        ("lab_durum", "Gönderilecek", None),
        ("lab_durum", "Gönderildi", None),
        ("lab_durum", "Teslim Alındı", None),
        ("lab_durum", "Hastaya Takıldı", None),
        ("lab_durum", "İptal", None),
    ]
    cur.executemany("INSERT OR IGNORE INTO ayarlar(grup, deger, renk) VALUES (?, ?, ?)", defaults)

    # Eski kurulumdan kalan oda adlarını yeni isimlere çevir.
    cur.execute("UPDATE ayarlar SET deger='Clinic 1' WHERE grup='oda' AND deger IN ('Oda 1', 'Oda1')")
    cur.execute("UPDATE ayarlar SET deger='Clinic 2' WHERE grup='oda' AND deger IN ('Oda 2', 'Oda2')")
    cur.execute("UPDATE randevular SET oda='Clinic 1' WHERE oda IN ('Oda 1', 'Oda1')")
    cur.execute("UPDATE randevular SET oda='Clinic 2' WHERE oda IN ('Oda 2', 'Oda2')")

    sample_islemler = [
        ("1-1", "Teşhis ve Tedavi Planlaması", "Dişhekimi Muayenesi", 1650, 20, 0, "Aktif"),
        ("2-4", "Tedavi ve Endodonti", "Kompozit Dolgu (Bir Yüzlü)", 3375, 45, 1, "Aktif"),
        ("2-27", "Tedavi ve Endodonti", "Kanal Tedavisi - Tek Kanal", 4610, 60, 1, "Aktif"),
        ("4-51", "Protez", "Zirkonyum Kron", 13750, 60, 1, "Aktif"),
        ("5-1", "Ağız-Diş ve Çene Cerrahisi", "Diş Çekimi", 2475, 30, 1, "Aktif"),
        ("6-1", "Periodontoloji", "Detartraj (Diş Taşı Temizliği - Tek Çene)", 3300, 45, 0, "Aktif"),
    ]
    cur.executemany("""
        INSERT OR IGNORE INTO islemler(id, kategori, islem_adi, kdv_dahil_ucret, sure_dk, dis_no_gerekli, durum)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, sample_islemler)

    c.commit()
    c.close()

    migrations = [
        ("hastalar", "dogum_tarihi", "TEXT"),
        ("hastalar", "kronik_hastalik", "TEXT"),
        ("hastalar", "kullanilan_ilaclar", "TEXT"),
        ("hastalar", "alerji", "TEXT"),
        ("hastalar", "kanser_gecmisi", "TEXT"),
        ("hastalar", "operasyon_gecmisi", "TEXT"),
        ("hastalar", "hamilelik_durumu", "TEXT"),
        ("hastalar", "kanama_pihtilasma", "TEXT"),
        ("hastalar", "sistemik_notlar", "TEXT"),
        ("randevular", "islem_id", "TEXT"),
        ("randevular", "dis_no", "TEXT"),
        ("hasta_islemleri", "lab_gidecek", "INTEGER DEFAULT 0"),
        ("hasta_islemleri", "randevu_id", "INTEGER"),
        ("hasta_islemleri", "dis_no", "TEXT"),
        ("hasta_islemleri", "saat", "TEXT"),
    ]
    for table, col, definition in migrations:
        try:
            add_column_if_missing(table, col, definition)
        except Exception:
            pass

def import_islem_df(df):
    cols = {str(c).lower().strip(): c for c in df.columns}
    def col(*names):
        for n in names:
            if n.lower().strip() in cols:
                return cols[n.lower().strip()]
        return None

    id_col = col("id", "kod")
    kat_col = col("kategori")
    name_col = col("islem_adi", "işlem adı", "islem adı")
    price_col = col("kdv_dahil_ucret", "kdv dahil")
    sure_col = col("sure_dk", "tahmini süre (dk)", "süre", "sure")
    dis_col = col("dis_no_gerekli", "diş no gerekli mi?", "dis no gerekli mi?")
    durum_col = col("durum")

    if not id_col or not name_col or not price_col:
        return 0, "Zorunlu kolonlar bulunamadı: Kod/id, İşlem Adı/islem_adi, KDV Dahil/kdv_dahil_ucret."

    imported = 0
    for _, r in df.iterrows():
        id_ = str(r[id_col]).strip()
        if not id_ or id_.lower() == "nan":
            continue
        name = str(r[name_col]).strip()
        kategori = str(r[kat_col]).strip() if kat_col else ""
        price = clean_money_value(r[price_col])
        sure = clean_int_value(r[sure_col], 30) if sure_col else 30
        dis_val = str(r[dis_col]).strip().lower() if dis_col else ""
        dis = 1 if dis_val in ["evet", "true", "1", "yes"] else 0
        durum = str(r[durum_col]).strip() if durum_col else "Aktif"

        execute("""
            INSERT OR REPLACE INTO islemler
            (id, kategori, islem_adi, kdv_dahil_ucret, sure_dk, dis_no_gerekli, durum)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (id_, kategori, name, price, sure, dis, durum))
        imported += 1
    return imported, None

def get_islem_info(islem_id):
    df = q("SELECT * FROM islemler WHERE id=?", (islem_id,))
    if df.empty:
        return None
    return df.iloc[0].to_dict()

def add_hasta_islemi_from_randevu(randevu_id):
    r = q("SELECT * FROM randevular WHERE id=?", (randevu_id,))
    if r.empty:
        return
    row = r.iloc[0]
    exists = q("SELECT id FROM hasta_islemleri WHERE randevu_id=?", (int(randevu_id),))
    if not exists.empty:
        return
    info = get_islem_info(row.get("islem_id"))
    kategori = info["kategori"] if info else ""
    lab_default = 1 if kategori == "Protez" or "Kuron" in str(row["islem_adi"]) or "Protez" in str(row["islem_adi"]) else 0

    execute("""
        INSERT INTO hasta_islemleri
        (tarih, saat, hasta_adi, islem_id, islem_adi, kategori, dis_no, hekim, ucret, sure_dk, durum, randevu_id, lab_gidecek, notlar)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        row["tarih"], row["saat"], row["hasta_adi"], row.get("islem_id"), row["islem_adi"], kategori,
        row.get("dis_no"), row["hekim"], float(row["ucret"]), int(row["sure_dk"]),
        row["durum"], int(randevu_id), lab_default, row.get("notlar")
    ))

def delete_randevu_and_linked(randevu_id):
    execute("DELETE FROM hasta_islemleri WHERE randevu_id=?", (int(randevu_id),))
    execute("DELETE FROM randevular WHERE id=?", (int(randevu_id),))

def delete_hasta_islemi_and_linked(islem_row_id):
    execute("DELETE FROM laboratuvar WHERE islem_id=?", (int(islem_row_id),))
    execute("DELETE FROM giderler WHERE islem_id=?", (int(islem_row_id),))
    execute("DELETE FROM hasta_islemleri WHERE id=?", (int(islem_row_id),))

def create_lab_from_hasta_islemi(hasta_islem_id, lab_adi, lab_ucreti, aciklama):
    hi = q("SELECT * FROM hasta_islemleri WHERE id=?", (hasta_islem_id,))
    if hi.empty:
        return False
    row = hi.iloc[0]
    exists = q("SELECT id FROM laboratuvar WHERE islem_id=?", (int(hasta_islem_id),))
    if not exists.empty:
        execute("""
            UPDATE laboratuvar SET lab_adi=?, lab_ucreti=?, aciklama=? WHERE islem_id=?
        """, (lab_adi, float(lab_ucreti), aciklama, int(hasta_islem_id)))
        return True
    execute("""
        INSERT INTO laboratuvar
        (tarih, hasta_adi, islem_id, islem_adi, lab_adi, gonderim_tarihi, teslim_tarihi, lab_ucreti, durum, aciklama)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        str(date.today()), row["hasta_adi"], int(hasta_islem_id), row["islem_adi"],
        lab_adi, str(date.today()), "", float(lab_ucreti), "Gönderilecek", aciklama
    ))
    return True

# ---------------- STYLE ----------------
st.set_page_config(page_title="Özel Dentalde", page_icon="🦷", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
:root {
    --green: #9ACD32;
    --black: #111111;
}
.stApp {
    background: #f7faef;
}
.block-container {
    padding-top: 0.75rem;
    padding-bottom: 6rem;
    max-width: 980px;
}
h1, h2, h3 {
    color: #111111;
}
div[data-testid="stMetric"] {
    background: white;
    border: 1px solid #dce8c7;
    padding: 12px;
    border-radius: 18px;
    box-shadow: 0 2px 8px rgba(0,0,0,.05);
}
.stButton > button, .stFormSubmitButton > button {
    background: #111111;
    color: #9ACD32;
    border-radius: 18px;
    border: 0;
    min-height: 48px;
    font-weight: 700;
    width: 100%;
}
.stButton > button:hover, .stFormSubmitButton > button:hover {
    background: #9ACD32;
    color: #111111;
}
div[data-baseweb="select"] > div {
    border-radius: 14px;
}
input, textarea {
    border-radius: 14px !important;
}
.mobile-card {
    background: white;
    border-left: 6px solid #9ACD32;
    border-radius: 18px;
    padding: 14px;
    margin: 10px 0;
    box-shadow: 0 3px 10px rgba(0,0,0,.06);
}
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
    white-space: normal;
    word-break: keep-all;
    overflow-wrap: normal;
    margin-top: 14px;
    margin-bottom: 20px;
    box-shadow: 0 3px 10px rgba(0,0,0,.06);
}
.logo-wrap {
    background: #ffffff;
    border-radius: 18px;
    padding: 14px;
    margin-top: 12px;
    margin-bottom: 10px;
    text-align: center;
}
.logo-wrap img {
    max-width: 280px;
    width: 70%;
    height: auto;
}
.clinic-title .line1,
.clinic-title .line2 {
    display: block;
}
@media (max-width: 640px) {
    .clinic-title {
        font-size: 17px;
        padding: 14px 10px;
        border-radius: 16px;
        margin-top: 12px;
        margin-bottom: 16px;
    }
    .block-container {
        padding-left: 0.75rem;
        padding-right: 0.75rem;
        padding-top: 1.25rem;
    }
}
.small-muted {
    color: #555;
    font-size: 0.9rem;
}
</style>
""", unsafe_allow_html=True)

init_db()

st.markdown('<div class="logo-wrap"><img src="data:image/png;base64,{}"></div>'.format(__import__("base64").b64encode(open("dentalde_logo.png", "rb").read()).decode()), unsafe_allow_html=True)
st.markdown('<div class="clinic-title"><span class="line1">ÖZEL DENTALDE ÇAYYOLU</span><span class="line2">AĞIZ VE DİŞ SAĞLIĞI POLİKLİNİĞİ</span></div>', unsafe_allow_html=True)


# ---------------- AUTH ----------------
def check_login():
    # Streamlit Cloud'da bu bilgiler App settings > Secrets içine girilecek.
    try:
        allowed_username = st.secrets["APP_USERNAME"]
        allowed_password = st.secrets["APP_PASSWORD"]
    except Exception:
        st.error("Giriş bilgileri tanımlı değil. Streamlit Cloud > App settings > Secrets içine APP_USERNAME ve APP_PASSWORD ekle.")
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
    <div style="
        max-width: 420px;
        margin: 40px auto;
        background: white;
        border: 2px solid #111;
        border-radius: 18px;
        padding: 22px;
        box-shadow: 0 3px 12px rgba(0,0,0,.08);
    ">
        <h2 style="text-align:center; color:#111;">Özel Dentalde Çayyolu</h2>
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
            st.success("Giriş başarılı.")
            st.rerun()
        else:
            st.error("Kullanıcı adı veya şifre hatalı.")

    st.stop()

check_login()


MENU = [
    "1 Hasta Kayıt",
    "2 Haftalık Program",
    "3 Randevu Ekle",
    "4 Hasta İşlemleri",
    "5 Cari / Ödeme",
    "6 Laboratuvar",
    "7 Gelir-Gider",
    "8 TDB İşlemleri",
    "9 Ayarlar",
]

with st.sidebar:
    st.markdown("### Menü")
    sayfa = st.radio("Menü", MENU, horizontal=False, label_visibility="collapsed")

# ---------------- 1 HASTA KAYIT ----------------
if sayfa == "1 Hasta Kayıt":
    st.header("Hasta Kayıt ve Anamnez")

    with st.form("hasta_kayit"):
        hasta_adi = st.text_input("Hasta Adı Soyadı *")
        c1, c2 = st.columns(2)
        tc = c1.text_input("T.C.")
        telefon = c2.text_input("Telefon")
        dogum_tarihi = st.date_input("Doğum Tarihi", value=date(1990,1,1))

        st.subheader("Anamnez")
        kronik = st.text_area("Kronik Hastalık", placeholder="Diyabet, hipertansiyon, kalp hastalığı vb.")
        ilac = st.text_area("Kullanılan İlaçlar", placeholder="Kan sulandırıcı, tansiyon ilacı, insülin vb.")
        alerji = st.text_area("Alerji", placeholder="İlaç, lateks, anestezik, gıda vb.")
        kanser = st.text_area("Kanser Geçmişi / RT-KT")
        operasyon = st.text_area("Operasyon / Hastane Yatış Geçmişi")
        c3, c4 = st.columns(2)
        hamilelik = c3.selectbox("Hamilelik Durumu", ["Yok", "Var", "Bilinmiyor", "Uygun değil"])
        kanama = c4.selectbox("Kanama / Pıhtılaşma Problemi", ["Yok", "Var", "Bilinmiyor"])
        sistemik = st.text_area("Diğer Sistemik Notlar")
        notlar = st.text_area("Genel Notlar")
        kaydet = st.form_submit_button("Hasta Kaydet / Güncelle")

    if kaydet:
        if not hasta_adi.strip():
            st.error("Hasta adı zorunlu.")
        else:
            execute("""
            INSERT OR REPLACE INTO hastalar
            (hasta_adi, tc, telefon, dogum_tarihi, kronik_hastalik, kullanilan_ilaclar, alerji,
             kanser_gecmisi, operasyon_gecmisi, hamilelik_durumu, kanama_pihtilasma, sistemik_notlar, notlar)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (hasta_adi.strip(), tc, telefon, str(dogum_tarihi), kronik, ilac, alerji, kanser, operasyon, hamilelik, kanama, sistemik, notlar))
            st.success("Hasta kaydedildi/güncellendi.")

    st.subheader("Hasta Listesi")
    hastalar = q("SELECT * FROM hastalar ORDER BY hasta_adi")
    if hastalar.empty:
        st.info("Henüz hasta yok.")
    else:
        search = st.text_input("Hasta ara")
        shown = hastalar[hastalar["hasta_adi"].str.contains(search, case=False, na=False)] if search else hastalar
        for _, r in shown.iterrows():
            st.markdown(f"""
            <div class="mobile-card">
            <b>{r['hasta_adi']}</b><br>
            <span class="small-muted">Tel: {safe_text(r['telefon'])} | TC: {safe_text(r['tc'])}</span><br>
            <span class="small-muted">Alerji: {safe_text(r['alerji']) or '-'}</span><br>
            <span class="small-muted">Kronik: {safe_text(r['kronik_hastalik']) or '-'}</span>
            </div>
            """, unsafe_allow_html=True)

        st.subheader("Hasta Düzenle / Sil")
        hastalar["secim"] = hastalar["id"].astype(str) + " | " + hastalar["hasta_adi"].astype(str)
        secili = st.selectbox("Hasta seç", hastalar["secim"].tolist())
        hid = int(secili.split(" | ")[0])
        row = hastalar[hastalar["id"] == hid].iloc[0]

        with st.form("hasta_duzenle"):
            yeni_ad = st.text_input("Hasta Adı Soyadı", value=safe_text(row["hasta_adi"]))
            c1, c2 = st.columns(2)
            yeni_tc = c1.text_input("T.C.", value=safe_text(row["tc"]))
            yeni_tel = c2.text_input("Telefon", value=safe_text(row["telefon"]))
            yeni_kronik = st.text_area("Kronik Hastalık", value=safe_text(row["kronik_hastalik"]))
            yeni_ilac = st.text_area("Kullanılan İlaçlar", value=safe_text(row["kullanilan_ilaclar"]))
            yeni_alerji = st.text_area("Alerji", value=safe_text(row["alerji"]))
            yeni_kanser = st.text_area("Kanser Geçmişi / RT-KT", value=safe_text(row["kanser_gecmisi"]))
            yeni_operasyon = st.text_area("Operasyon Geçmişi", value=safe_text(row["operasyon_gecmisi"]))
            yeni_sistemik = st.text_area("Sistemik Notlar", value=safe_text(row["sistemik_notlar"]))
            yeni_not = st.text_area("Genel Notlar", value=safe_text(row["notlar"]))
            c3, c4 = st.columns(2)
            guncelle = c3.form_submit_button("Hasta Güncelle")
            sil = c4.form_submit_button("Hastayı Sil")

        if guncelle:
            eski_ad = safe_text(row["hasta_adi"])
            execute("""
                UPDATE hastalar
                SET hasta_adi=?, tc=?, telefon=?, kronik_hastalik=?, kullanilan_ilaclar=?, alerji=?,
                    kanser_gecmisi=?, operasyon_gecmisi=?, sistemik_notlar=?, notlar=?
                WHERE id=?
            """, (yeni_ad, yeni_tc, yeni_tel, yeni_kronik, yeni_ilac, yeni_alerji, yeni_kanser, yeni_operasyon, yeni_sistemik, yeni_not, hid))
            if eski_ad != yeni_ad:
                for table in ["randevular", "hasta_islemleri", "odemeler", "giderler", "laboratuvar"]:
                    try:
                        execute(f"UPDATE {table} SET hasta_adi=? WHERE hasta_adi=?", (yeni_ad, eski_ad))
                    except Exception:
                        pass
            st.success("Hasta güncellendi.")
            st.rerun()

        if sil:
            hasta_ad = safe_text(row["hasta_adi"])
            for table in ["laboratuvar", "giderler", "odemeler", "hasta_islemleri", "randevular"]:
                try:
                    execute(f"DELETE FROM {table} WHERE hasta_adi=?", (hasta_ad,))
                except Exception:
                    pass
            execute("DELETE FROM hastalar WHERE id=?", (hid,))
            st.warning("Hasta ve bağlı kayıtlar silindi.")
            st.rerun()

# ---------------- 2 HAFTALIK PROGRAM ----------------
elif sayfa == "2 Haftalık Program":
    st.header("Haftalık Program")
    secilen = st.date_input("Hafta seç", value=date.today())
    bas = monday_of(secilen)
    son = bas + timedelta(days=6)
    st.caption(f"{bas.strftime('%d.%m.%Y')} - {son.strftime('%d.%m.%Y')}")

    r = q("""
        SELECT 
            id,
            tarih,
            saat,
            hasta_adi,
            hekim,
            oda,
            islem_adi,
            dis_no,
            durum,
            'Randevu' AS kaynak
        FROM randevular
        WHERE tarih BETWEEN ? AND ?

        UNION ALL

        SELECT
            id,
            tarih,
            saat,
            hasta_adi,
            hekim,
            '' AS oda,
            islem_adi,
            dis_no,
            durum,
            'Hasta İşlemi' AS kaynak
        FROM hasta_islemleri
        WHERE tarih BETWEEN ? AND ?
          AND saat IS NOT NULL
          AND saat != ''
          AND randevu_id IS NULL

        ORDER BY tarih, saat
    """, (str(bas), str(son), str(bas), str(son)))

    if r.empty:
        st.info("Bu haftada randevu yok.")
    else:
        for g in [bas + timedelta(days=i) for i in range(7)]:
            gd = str(g)
            gun_df = r[r["tarih"] == gd]
            st.subheader(g.strftime("%d.%m %A"))
            if gun_df.empty:
                st.caption("Boş")
            else:
                for _, row in gun_df.iterrows():
                    hekim_color = "#9ACD32" if "Enes" in row["hekim"] else "#111111"
                    txt_color = "#111111" if hekim_color == "#9ACD32" else "#9ACD32"
                    st.markdown(f"""
                    <div class="mobile-card" style="border-left-color:{hekim_color};">
                    <b>{row['saat']} - {row['hasta_adi']}</b><br>
                    <span class="small-muted">{row['hekim']} {('| ' + row['oda']) if safe_text(row.get('oda')) else ''}</span><br>
                    <b>{row['islem_adi']}</b><br>
                    <span class="small-muted">Kaynak: {safe_text(row.get('kaynak'))} | Diş: {safe_text(row.get('dis_no')) or '-'} | Durum: {safe_text(row.get('durum'))}</span>
                    </div>
                    """, unsafe_allow_html=True)

# ---------------- 3 RANDEVU EKLE ----------------
elif sayfa == "3 Randevu Ekle":
    st.header("Randevu Ekle / Düzenle")
    hastalar = q("SELECT hasta_adi FROM hastalar ORDER BY hasta_adi")["hasta_adi"].tolist()
    islemler = q("SELECT * FROM islemler WHERE durum='Aktif' ORDER BY kategori, islem_adi")
    hekimler = get_list("hekim")
    odalar = get_list("oda")
    durumlar = get_list("durum")

    if not hastalar:
        st.warning("Önce hasta kaydı oluştur.")
    elif islemler.empty:
        st.warning("Önce TDB işlem listesi yükle.")
    else:
        with st.form("randevu_form"):
            c1, c2 = st.columns(2)
            tarih = c1.date_input("Tarih", value=date.today())
            saat = c2.selectbox("Saat", make_slots())
            hasta = st.selectbox("Hasta", hastalar)
            c3, c4 = st.columns(2)
            hekim = c3.selectbox("Hekim", hekimler)
            oda = c4.selectbox("Oda", odalar)

            secenekler = (islemler["id"] + " | " + islemler["islem_adi"]).tolist()
            secili = st.selectbox("İşlem", secenekler)
            islem_id = secili.split(" | ")[0]
            info = get_islem_info(islem_id)
            dis_gerekli = bool(info["dis_no_gerekli"])

            c5, c6, c7 = st.columns(3)
            dis_no = c5.text_input("Diş No" + (" *" if dis_gerekli else ""))
            ucret = c6.number_input("Ücret", value=float(info["kdv_dahil_ucret"]), step=100.0)
            sure = c7.number_input("Süre", value=int(info["sure_dk"]), step=5)
            durum = st.selectbox("Durum", durumlar)
            otomatik = st.checkbox("Hasta işlemine de ekle", value=True)
            notlar = st.text_area("Not")
            kaydet = st.form_submit_button("Randevu Kaydet")

        if kaydet:
            if dis_gerekli and not dis_no.strip():
                st.error("Bu işlem için diş no zorunlu.")
            else:
                conflict = q("SELECT id FROM randevular WHERE tarih=? AND saat=? AND oda=?", (str(tarih), saat, oda))
                if not conflict.empty:
                    st.error("Çakışma: Aynı tarih/saat/odada randevu var.")
                else:
                    execute("""
                    INSERT INTO randevular
                    (tarih, saat, hasta_adi, hekim, oda, islem_id, islem_adi, dis_no, ucret, sure_dk, durum, notlar)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (str(tarih), saat, hasta, hekim, oda, islem_id, info["islem_adi"], dis_no, ucret, sure, durum, notlar))
                    rid = q("SELECT MAX(id) AS id FROM randevular").iloc[0]["id"]
                    if otomatik:
                        add_hasta_islemi_from_randevu(int(rid))
                    st.success("Randevu kaydedildi.")

    randevular = q("SELECT * FROM randevular ORDER BY tarih DESC, saat DESC")
    st.subheader("Randevu Düzenle / Sil")
    if randevular.empty:
        st.info("Henüz randevu yok.")
    else:
        randevular["secim"] = randevular["id"].astype(str) + " | " + randevular["tarih"].astype(str) + " " + randevular["saat"].astype(str) + " | " + randevular["hasta_adi"].astype(str)
        sec = st.selectbox("Randevu seç", randevular["secim"].tolist())
        rid = int(sec.split(" | ")[0])
        row = randevular[randevular["id"] == rid].iloc[0]
        with st.form("r_edit"):
            durum = st.selectbox("Durum", durumlar, index=durumlar.index(row["durum"]) if row["durum"] in durumlar else 0)
            notu = st.text_area("Not", value=safe_text(row["notlar"]))
            c1, c2 = st.columns(2)
            g = c1.form_submit_button("Güncelle")
            s = c2.form_submit_button("Sil")
        if g:
            execute("UPDATE randevular SET durum=?, notlar=? WHERE id=?", (durum, notu, rid))
            execute("UPDATE hasta_islemleri SET durum=?, notlar=? WHERE randevu_id=?", (durum, notu, rid))
            st.success("Randevu güncellendi.")
            st.rerun()
        if s:
            delete_randevu_and_linked(rid)
            st.warning("Randevu silindi.")
            st.rerun()

# ---------------- 4 HASTA İŞLEMLERİ ----------------
elif sayfa == "4 Hasta İşlemleri":
    st.header("Hasta İşlemleri")
    hastalar = q("SELECT hasta_adi FROM hastalar ORDER BY hasta_adi")["hasta_adi"].tolist()
    islemler = q("SELECT * FROM islemler WHERE durum='Aktif' ORDER BY kategori, islem_adi")
    hekimler = get_list("hekim")

    if not hastalar:
        st.warning("Önce hasta ekle.")
    else:
        with st.form("islem_ekle"):
            hasta = st.selectbox("Hasta", hastalar)
            hekim = st.selectbox("Hekim", hekimler)
            secenekler = (islemler["id"] + " | " + islemler["islem_adi"]).tolist()
            secili = st.selectbox("İşlem", secenekler)
            islem_id = secili.split(" | ")[0]
            info = get_islem_info(islem_id)
            c1, c2, c3 = st.columns(3)
            tarih = c1.date_input("Tarih", value=date.today())
            saat = c2.selectbox("Saat", [""] + make_slots(), help="Boş bırakırsan haftalık programa düşmez.")
            dis_no = c3.text_input("Diş No")
            ucret = st.number_input("Ücret", value=float(info["kdv_dahil_ucret"]), step=100.0)
            durum = st.selectbox("Durum", ["Planlandı", "Başlandı", "Tamamlandı", "İptal"])
            lab = st.checkbox("Laboratuvara gidecek", value=info["kategori"] == "Protez")
            notlar = st.text_area("Not")
            kaydet = st.form_submit_button("İşlem Kaydet")

        if kaydet:
            execute("""
                INSERT INTO hasta_islemleri
                (tarih, saat, hasta_adi, islem_id, islem_adi, kategori, dis_no, hekim, ucret, sure_dk, durum, lab_gidecek, notlar)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (str(tarih), saat, hasta, islem_id, info["islem_adi"], info["kategori"], dis_no, hekim, ucret, int(info["sure_dk"]), durum, 1 if lab else 0, notlar))
            st.success("İşlem kaydedildi.")

    hi = q("SELECT * FROM hasta_islemleri ORDER BY tarih DESC, id DESC")
    for _, row in hi.head(30).iterrows():
        st.markdown(f"""
        <div class="mobile-card">
        <b>{row['hasta_adi']}</b><br>
        {row['tarih']} {safe_text(row.get('saat'))} | {row['islem_adi']}<br>
        <span class="small-muted">Ücret: {float(row['ucret']):,.2f} TL | Durum: {row['durum']} | Lab: {'Evet' if row['lab_gidecek'] else 'Hayır'}</span>
        </div>
        """, unsafe_allow_html=True)

    st.subheader("İşlem Düzenle / Sil")
    if not hi.empty:
        hi["secim"] = hi["id"].astype(str) + " | " + hi["hasta_adi"].astype(str) + " | " + hi["islem_adi"].astype(str)
        sec = st.selectbox("İşlem seç", hi["secim"].tolist())
        iid = int(sec.split(" | ")[0])
        row = hi[hi["id"] == iid].iloc[0]
        with st.form("hi_edit"):
            yeni_saat = st.selectbox("Saat", [""] + make_slots(), index=([""] + make_slots()).index(safe_text(row.get("saat"))) if safe_text(row.get("saat")) in ([""] + make_slots()) else 0)
            yeni_durum = st.selectbox("Durum", ["Planlandı", "Başlandı", "Tamamlandı", "İptal"], index=["Planlandı", "Başlandı", "Tamamlandı", "İptal"].index(row["durum"]) if row["durum"] in ["Planlandı", "Başlandı", "Tamamlandı", "İptal"] else 0)
            yeni_ucret = st.number_input("Ücret", value=float(row["ucret"]), step=100.0)
            yeni_lab = st.checkbox("Laboratuvara gidecek", value=bool(row["lab_gidecek"]))
            c1, c2 = st.columns(2)
            g = c1.form_submit_button("Güncelle")
            s = c2.form_submit_button("Sil")
        if g:
            execute("UPDATE hasta_islemleri SET saat=?, durum=?, ucret=?, lab_gidecek=? WHERE id=?", (yeni_saat, yeni_durum, yeni_ucret, 1 if yeni_lab else 0, iid))
            st.success("İşlem güncellendi.")
            st.rerun()
        if s:
            delete_hasta_islemi_and_linked(iid)
            st.warning("İşlem silindi.")
            st.rerun()

# ---------------- 5 CARI ----------------
elif sayfa == "5 Cari / Ödeme":
    st.header("Cari / Ödeme")
    hastalar = q("SELECT hasta_adi FROM hastalar ORDER BY hasta_adi")["hasta_adi"].tolist()
    if not hastalar:
        st.warning("Önce hasta ekle.")
    else:
        hasta = st.selectbox("Hasta", hastalar)
        borc = q("SELECT IFNULL(SUM(ucret),0) AS s FROM hasta_islemleri WHERE hasta_adi=? AND IFNULL(durum,'')!='İptal'", (hasta,)).iloc[0]["s"]
        tahsilat = q("SELECT IFNULL(SUM(tutar),0) AS s FROM odemeler WHERE hasta_adi=?", (hasta,)).iloc[0]["s"]
        gider = q("SELECT IFNULL(SUM(tutar),0) AS s FROM giderler WHERE hasta_adi=?", (hasta,)).iloc[0]["s"]
        c1, c2, c3 = st.columns(3)
        c1.metric("Borç", f"{float(borc):,.2f} TL")
        c2.metric("Tahsilat", f"{float(tahsilat):,.2f} TL")
        c3.metric("Bakiye", f"{float(borc)-float(tahsilat):,.2f} TL")

        with st.form("odeme"):
            tutar = st.number_input("Ödeme Tutarı", min_value=0.0, step=100.0)
            odeme_tipi = st.selectbox("Ödeme Tipi", get_list("odeme"))
            aciklama = st.text_input("Açıklama")
            kaydet = st.form_submit_button("Ödeme Kaydet")
        if kaydet and tutar > 0:
            execute("INSERT INTO odemeler(tarih,hasta_adi,tutar,odeme_tipi,aciklama) VALUES (?,?,?,?,?)", (str(date.today()), hasta, tutar, odeme_tipi, aciklama))
            st.success("Ödeme kaydedildi.")

        st.subheader("Ödemeler")
        od = q("SELECT * FROM odemeler WHERE hasta_adi=? ORDER BY tarih DESC, id DESC", (hasta,))
        st.dataframe(od, width="stretch", hide_index=True)

# ---------------- 6 LAB ----------------
elif sayfa == "6 Laboratuvar":
    st.header("Laboratuvar")
    labs = get_list("lab")
    lab_durumlar = get_list("lab_durum")

    cand = q("""
        SELECT hi.id, hi.tarih, hi.hasta_adi, hi.islem_adi, hi.dis_no, hi.ucret, hi.durum
        FROM hasta_islemleri hi
        LEFT JOIN laboratuvar l ON l.islem_id = hi.id
        WHERE hi.lab_gidecek=1 AND l.id IS NULL AND IFNULL(hi.durum,'')!='İptal'
        ORDER BY hi.tarih DESC
    """)
    st.subheader("Gönderilecekler")
    if cand.empty:
        st.info("Bekleyen lab işlemi yok.")
    else:
        with st.form("lab_ac"):
            ids = cand["id"].tolist()
            sec = st.selectbox("İşlem seç", ids)
            lab_adi = st.selectbox("Laboratuvar", labs)
            lab_ucret = st.number_input("Lab Ücreti", min_value=0.0, step=100.0)
            aciklama = st.text_input("Açıklama")
            kaydet = st.form_submit_button("Lab Kaydı Aç")
        if kaydet:
            create_lab_from_hasta_islemi(int(sec), lab_adi, lab_ucret, aciklama)
            st.success("Lab kaydı açıldı.")
            st.rerun()

    labdf = q("SELECT * FROM laboratuvar ORDER BY tarih DESC, id DESC")
    for _, row in labdf.iterrows():
        st.markdown(f"""
        <div class="mobile-card">
        <b>{row['hasta_adi']}</b><br>
        {row['islem_adi']}<br>
        <span class="small-muted">{row['lab_adi']} | {row['durum']} | {float(row['lab_ucreti'] or 0):,.2f} TL</span>
        </div>
        """, unsafe_allow_html=True)

    st.subheader("Lab Güncelle / Sil")
    if not labdf.empty:
        sec = st.selectbox("Lab kaydı seç", labdf["id"].tolist())
        row = labdf[labdf["id"] == sec].iloc[0]
        with st.form("lab_edit"):
            durum = st.selectbox("Durum", lab_durumlar, index=lab_durumlar.index(row["durum"]) if row["durum"] in lab_durumlar else 0)
            ucret = st.number_input("Lab Ücreti", value=float(row["lab_ucreti"] or 0), step=100.0)
            c1, c2 = st.columns(2)
            g = c1.form_submit_button("Güncelle")
            s = c2.form_submit_button("Sil")
        if g:
            execute("UPDATE laboratuvar SET durum=?, lab_ucreti=? WHERE id=?", (durum, ucret, int(sec)))
            if durum in ["Teslim Alındı", "Hastaya Takıldı"]:
                already = q("SELECT id FROM giderler WHERE gider_tipi='Laboratuvar' AND islem_id=?", (int(row["islem_id"]),))
                if already.empty and ucret > 0:
                    execute("INSERT INTO giderler(tarih,gider_tipi,tutar,odeme_tipi,hasta_adi,islem_id,aciklama) VALUES (?,?,?,?,?,?,?)",
                            (str(date.today()), "Laboratuvar", ucret, "Havale/EFT", row["hasta_adi"], int(row["islem_id"]), f"Lab: {row['islem_adi']}"))
            st.success("Lab güncellendi.")
            st.rerun()
        if s:
            execute("DELETE FROM giderler WHERE gider_tipi='Laboratuvar' AND islem_id=?", (int(row["islem_id"]),))
            execute("DELETE FROM laboratuvar WHERE id=?", (int(sec),))
            st.warning("Lab kaydı silindi.")
            st.rerun()

# ---------------- 7 GELIR GIDER ----------------
elif sayfa == "7 Gelir-Gider":
    st.header("Gelir-Gider")
    gelir = q("SELECT IFNULL(SUM(tutar),0) AS s FROM odemeler").iloc[0]["s"]
    gider = q("SELECT IFNULL(SUM(tutar),0) AS s FROM giderler").iloc[0]["s"]
    c1, c2, c3 = st.columns(3)
    c1.metric("Gelir", f"{float(gelir):,.2f} TL")
    c2.metric("Gider", f"{float(gider):,.2f} TL")
    c3.metric("Net", f"{float(gelir)-float(gider):,.2f} TL")

    with st.form("gider_ekle"):
        tip = st.selectbox("Gider Tipi", get_list("gider"))
        tutar = st.number_input("Tutar", min_value=0.0, step=100.0)
        aciklama = st.text_input("Açıklama")
        kaydet = st.form_submit_button("Gider Kaydet")
    if kaydet and tutar > 0:
        execute("INSERT INTO giderler(tarih,gider_tipi,tutar,odeme_tipi,aciklama) VALUES (?,?,?,?,?)", (str(date.today()), tip, tutar, "Nakit", aciklama))
        st.success("Gider kaydedildi.")

    gid = q("SELECT * FROM giderler ORDER BY tarih DESC, id DESC")
    st.dataframe(gid, width="stretch", hide_index=True)
    if not gid.empty:
        st.subheader("Gider Düzenle / Sil")
        sec = st.selectbox("Gider seç", gid["id"].tolist())
        row = gid[gid["id"] == sec].iloc[0]
        with st.form("gider_edit"):
            tutar2 = st.number_input("Tutar", value=float(row["tutar"]), step=100.0)
            aciklama2 = st.text_input("Açıklama", value=safe_text(row["aciklama"]))
            c1, c2 = st.columns(2)
            g = c1.form_submit_button("Güncelle")
            s = c2.form_submit_button("Sil")
        if g:
            execute("UPDATE giderler SET tutar=?, aciklama=? WHERE id=?", (tutar2, aciklama2, int(sec)))
            st.success("Gider güncellendi.")
            st.rerun()
        if s:
            execute("DELETE FROM giderler WHERE id=?", (int(sec),))
            st.warning("Gider silindi.")
            st.rerun()

# ---------------- 8 TDB ----------------
elif sayfa == "8 TDB İşlemleri":
    st.header("TDB İşlemleri")
    uploaded = st.file_uploader("TDB Excel/CSV yükle", type=["csv", "xlsx", "xls"])
    if uploaded:
        df = pd.read_csv(uploaded) if uploaded.name.endswith(".csv") else pd.read_excel(uploaded)
        n, err = import_islem_df(df)
        if err:
            st.error(err)
        else:
            st.success(f"{n} işlem yüklendi.")
            st.rerun()

    isdf = q("SELECT * FROM islemler ORDER BY id")
    st.dataframe(isdf, width="stretch", hide_index=True)

    st.subheader("İşlem Ekle / Güncelle")
    with st.form("islem_manual"):
        id_ = st.text_input("Kod / ID")
        kategori = st.text_input("Kategori")
        ad = st.text_input("İşlem Adı")
        c1, c2 = st.columns(2)
        ucret = c1.number_input("KDV Dahil Ücret", min_value=0.0, step=100.0)
        sure = c2.number_input("Süre", min_value=5, step=5, value=30)
        dis = st.checkbox("Diş no gerekli")
        durum = st.selectbox("Durum", ["Aktif", "Pasif"])
        kaydet = st.form_submit_button("Kaydet")
    if kaydet and id_ and ad:
        execute("INSERT OR REPLACE INTO islemler(id,kategori,islem_adi,kdv_dahil_ucret,sure_dk,dis_no_gerekli,durum) VALUES (?,?,?,?,?,?,?)",
                (id_, kategori, ad, ucret, sure, 1 if dis else 0, durum))
        st.success("İşlem kaydedildi.")
        st.rerun()

# ---------------- 9 AYARLAR ----------------
elif sayfa == "9 Ayarlar":
    st.header("Ayarlar")
    ayar = q("SELECT rowid AS kayit_id, grup, deger, renk FROM ayarlar ORDER BY grup, deger")
    st.dataframe(ayar, width="stretch", hide_index=True)

    st.subheader("Yeni Ayar Ekle")
    gruplar = ["hekim", "oda", "durum", "odeme", "gider", "lab", "lab_durum"]
    with st.form("ayar_ekle"):
        grup = st.selectbox("Grup", gruplar)
        deger = st.text_input("Değer")
        renk = st.color_picker("Renk", "#9ACD32") if grup in ["hekim", "oda"] else None
        kaydet = st.form_submit_button("Ekle")
    if kaydet and deger:
        execute("INSERT OR REPLACE INTO ayarlar(grup,deger,renk) VALUES (?,?,?)", (grup, deger.strip(), renk))
        st.success("Ayar eklendi.")
        st.rerun()

    st.subheader("Ayar Düzenle / Sil")
    if not ayar.empty:
        ayar["secim"] = ayar["kayit_id"].astype(str) + " | " + ayar["grup"] + " | " + ayar["deger"]
        sec = st.selectbox("Ayar seç", ayar["secim"].tolist())
        aid = int(sec.split(" | ")[0])
        row = ayar[ayar["kayit_id"] == aid].iloc[0]
        with st.form("ayar_edit"):
            grup2 = st.selectbox("Grup", gruplar, index=gruplar.index(row["grup"]) if row["grup"] in gruplar else 0)
            deger2 = st.text_input("Değer", value=row["deger"])
            renk2 = st.color_picker("Renk", safe_hex_color(row["renk"])) if grup2 in ["hekim", "oda"] else None
            c1, c2 = st.columns(2)
            g = c1.form_submit_button("Güncelle")
            s = c2.form_submit_button("Sil")
        if g:
            execute("DELETE FROM ayarlar WHERE rowid=?", (aid,))
            execute("INSERT OR REPLACE INTO ayarlar(grup,deger,renk) VALUES (?,?,?)", (grup2, deger2.strip(), renk2))
            st.success("Ayar güncellendi.")
            st.rerun()
        if s:
            execute("DELETE FROM ayarlar WHERE rowid=?", (aid,))
            st.warning("Ayar silindi.")
            st.rerun()
